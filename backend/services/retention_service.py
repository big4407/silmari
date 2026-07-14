"""보존 정책 조회·만료 집계·드라이런."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.db.models import (
    LoginHistory,
    Message,
    RetentionPolicy,
    Search,
    SearchResult,
    Video,
)
from backend.schemas.retention_schema import RetentionDryRunItem
from backend.utils.timeutils import kst_now

_DRY_RUN_SAMPLE_LIMIT = 50


def _cutoff(retention_days: int) -> datetime:
    return kst_now() - timedelta(days=retention_days)


def _count_files(directory: Path) -> int:
    if not directory.exists():
        return 0
    return sum(1 for p in directory.rglob("*") if p.is_file())


def _expired_files(
    directory: Path, retention_days: int, *, sample_limit: int = _DRY_RUN_SAMPLE_LIMIT
) -> tuple[int, list[str]]:
    if not directory.exists():
        return 0, []
    cutoff_ts = _cutoff(retention_days).timestamp()
    samples: list[str] = []
    count = 0
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        try:
            if path.stat().st_mtime >= cutoff_ts:
                continue
        except OSError:
            continue
        count += 1
        if len(samples) < sample_limit:
            try:
                samples.append(str(path.relative_to(directory)))
            except ValueError:
                samples.append(path.name)
    return count, samples


def _expired_db_count_and_samples(
    db: Session,
    model,
    date_column,
    retention_days: int,
    *,
    sample_limit: int = _DRY_RUN_SAMPLE_LIMIT,
    sample_fmt,
) -> tuple[int, list[str]]:
    cutoff = _cutoff(retention_days)
    count = (
        db.scalar(
            select(func.count()).select_from(model).where(date_column < cutoff)
        )
        or 0
    )
    if count == 0:
        return 0, []
    rows = db.scalars(
        select(model).where(date_column < cutoff).order_by(date_column).limit(sample_limit)
    ).all()
    return count, [sample_fmt(row) for row in rows]


def _storage_count(db: Session, data_type: str) -> int:
    settings = get_settings()
    if data_type == "cctv_video":
        return db.scalar(select(func.count()).select_from(Video)) or 0
    if data_type == "search_result":
        return db.scalar(select(func.count()).select_from(SearchResult)) or 0
    if data_type == "search_request":
        return db.scalar(select(func.count()).select_from(Search)) or 0
    if data_type == "login_history":
        return db.scalar(select(func.count()).select_from(LoginHistory)) or 0
    if data_type == "disaster_message":
        return db.scalar(select(func.count()).select_from(Message)) or 0
    if data_type == "clip_thumbnail":
        clips = _count_files(Path(settings.results_dir) / "clips")
        thumbs = _count_files(Path(settings.results_dir) / "thumbnails")
        return clips + thumbs
    if data_type == "chroma_embedding":
        return _count_files(Path(settings.chroma_dir))
    return 0


def _expired_count_and_samples(
    db: Session, data_type: str, retention_days: int
) -> tuple[int, list[str]]:
    settings = get_settings()
    if data_type == "cctv_video":
        return _expired_db_count_and_samples(
            db,
            Video,
            Video.created_at,
            retention_days,
            sample_fmt=lambda v: f"video#{v.id}:{v.file_path}",
        )
    if data_type == "search_result":
        return _expired_db_count_and_samples(
            db,
            SearchResult,
            SearchResult.created_at,
            retention_days,
            sample_fmt=lambda r: f"result#{r.id}:{r.video_filename or '—'}",
        )
    if data_type == "search_request":
        return _expired_db_count_and_samples(
            db,
            Search,
            Search.searched_at,
            retention_days,
            sample_fmt=lambda s: f"search#{s.id}",
        )
    if data_type == "login_history":
        return _expired_db_count_and_samples(
            db,
            LoginHistory,
            LoginHistory.created_at,
            retention_days,
            sample_fmt=lambda h: f"login#{h.id}:{h.username}",
        )
    if data_type == "disaster_message":
        return _expired_db_count_and_samples(
            db,
            Message,
            Message.crt_dt,
            retention_days,
            sample_fmt=lambda m: f"message#{m.sn}",
        )
    if data_type == "clip_thumbnail":
        results_dir = Path(settings.results_dir)
        clips = _expired_files(results_dir / "clips", retention_days)
        thumbs = _expired_files(results_dir / "thumbnails", retention_days)
        return clips[0] + thumbs[0], [
            *(f"clips/{s}" for s in clips[1]),
            *(f"thumbnails/{s}" for s in thumbs[1]),
        ][: _DRY_RUN_SAMPLE_LIMIT]
    if data_type == "chroma_embedding":
        return _expired_files(Path(settings.chroma_dir), retention_days)
    return 0, []


def list_retention_policies(db: Session) -> list[dict]:
    rows = list(
        db.scalars(select(RetentionPolicy).order_by(RetentionPolicy.id)).all()
    )
    result: list[dict] = []
    for p in rows:
        expired_count, _ = _expired_count_and_samples(
            db, p.data_type, p.retention_days
        )
        result.append(
            {
                "id": p.id,
                "data_type": p.data_type,
                "data_label": p.data_label,
                "storage_target": p.storage_target,
                "retention_days": p.retention_days,
                "expiry_action": p.expiry_action,
                "is_active": p.is_active,
                "notes": p.notes,
                "updated_at": p.updated_at,
                "current_count": _storage_count(db, p.data_type),
                "expired_count": expired_count,
            }
        )
    return result


def _policy_for_preview(
    policy: RetentionPolicy, overrides: dict[int, dict] | None
) -> tuple[int, bool]:
    patch = (overrides or {}).get(policy.id) or {}
    days = patch.get("retention_days", policy.retention_days)
    is_active = patch.get("is_active", policy.is_active)
    return days, is_active


def dry_run_retention(
    db: Session,
    *,
    policy_id: int | None = None,
    overrides: list[dict] | None = None,
) -> list[RetentionDryRunItem]:
    override_map = {o["id"]: o for o in (overrides or []) if "id" in o}
    stmt = select(RetentionPolicy).order_by(RetentionPolicy.id)
    if policy_id is not None:
        stmt = stmt.where(RetentionPolicy.id == policy_id)
    policies = list(db.scalars(stmt).all())
    if policy_id is not None and not policies:
        return []

    items: list[RetentionDryRunItem] = []
    for p in policies:
        days, is_active = _policy_for_preview(p, override_map)
        expired_count, samples = _expired_count_and_samples(db, p.data_type, days)
        items.append(
            RetentionDryRunItem(
                policy_id=p.id,
                data_type=p.data_type,
                data_label=p.data_label,
                expiry_action=override_map.get(p.id, {}).get(
                    "expiry_action", p.expiry_action
                ),
                expired_count=expired_count,
                samples=samples,
                is_active=is_active,
                skipped_reason=(
                    None
                    if is_active
                    else "정책이 중지 상태라 자동 실행 시 적용되지 않습니다."
                ),
            )
        )
    return items
