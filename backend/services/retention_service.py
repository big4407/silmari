"""보존 정책 조회·만료 집계·드라이런."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.db.models import (
    Analysis,
    LoginHistory,
    Message,
    RetentionPolicy,
    Search,
    Video,
)
from backend.repositories.retention_repository import RetentionRepository
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


def _delete_expired_files(directory: Path, retention_days: int) -> int:
    """cutoff 이전 파일을 실제로 지운다. 지운 개수를 반환."""
    if not directory.exists():
        return 0
    cutoff_ts = _cutoff(retention_days).timestamp()
    count = 0
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        try:
            if path.stat().st_mtime >= cutoff_ts:
                continue
            path.unlink()
            count += 1
        except OSError:
            continue
    return count


class RetentionService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = RetentionRepository(db)

    def list_policies(self) -> list[dict]:
        result: list[dict] = []
        for p in self.repository.list_ordered():
            expired_count, _ = self._expired_count_and_samples(p.data_type, p.retention_days)
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
                    "current_count": self._storage_count(p.data_type),
                    "expired_count": expired_count,
                }
            )
        return result

    def dry_run(
        self,
        *,
        policy_id: int | None = None,
        overrides: list[dict] | None = None,
    ) -> list[RetentionDryRunItem]:
        override_map = {o["id"]: o for o in (overrides or []) if "id" in o}
        policies = self.repository.list_filtered(policy_id)
        if policy_id is not None and not policies:
            return []

        items: list[RetentionDryRunItem] = []
        for p in policies:
            days, is_active = self._policy_for_preview(p, override_map)
            expired_count, samples = self._expired_count_and_samples(p.data_type, days)
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

    def _policy_for_preview(
        self, policy: RetentionPolicy, overrides: dict[int, dict] | None
    ) -> tuple[int, bool]:
        patch = (overrides or {}).get(policy.id) or {}
        days = patch.get("retention_days", policy.retention_days)
        is_active = patch.get("is_active", policy.is_active)
        return days, is_active

    def _storage_count(self, data_type: str) -> int:
        settings = get_settings()
        if data_type == "cctv_video":
            return self.db.scalar(select(func.count()).select_from(Video)) or 0
        if data_type == "search_result":
            return self.db.scalar(select(func.count()).select_from(Analysis)) or 0
        if data_type == "search_request":
            return self.db.scalar(select(func.count()).select_from(Search)) or 0
        if data_type == "login_history":
            return self.db.scalar(select(func.count()).select_from(LoginHistory)) or 0
        if data_type == "disaster_message":
            return self.db.scalar(select(func.count()).select_from(Message)) or 0
        if data_type == "clip_thumbnail":
            clips = _count_files(Path(settings.results_dir) / "clips")
            thumbs = _count_files(Path(settings.results_dir) / "thumbnails")
            return clips + thumbs
        if data_type == "chroma_embedding":
            return _count_files(Path(settings.chroma_dir))
        return 0

    def _expired_db_count_and_samples(
        self,
        model,
        date_column,
        retention_days: int,
        *,
        sample_limit: int = _DRY_RUN_SAMPLE_LIMIT,
        sample_fmt,
    ) -> tuple[int, list[str]]:
        cutoff = _cutoff(retention_days)
        count = (
            self.db.scalar(
                select(func.count()).select_from(model).where(date_column < cutoff)
            )
            or 0
        )
        if count == 0:
            return 0, []
        rows = self.db.scalars(
            select(model).where(date_column < cutoff).order_by(date_column).limit(sample_limit)
        ).all()
        return count, [sample_fmt(row) for row in rows]

    def _expired_count_and_samples(
        self, data_type: str, retention_days: int
    ) -> tuple[int, list[str]]:
        settings = get_settings()
        if data_type == "cctv_video":
            return self._expired_db_count_and_samples(
                Video,
                Video.created_at,
                retention_days,
                sample_fmt=lambda v: f"video#{v.id}:{v.file_path}",
            )
        if data_type == "search_result":
            return self._expired_db_count_and_samples(
                Analysis,
                Analysis.created_at,
                retention_days,
                sample_fmt=lambda a: f"analysis#{a.id}:search#{a.search_id}",
            )
        if data_type == "search_request":
            return self._expired_db_count_and_samples(
                Search,
                Search.searched_at,
                retention_days,
                sample_fmt=lambda s: f"search#{s.id}",
            )
        if data_type == "login_history":
            return self._expired_db_count_and_samples(
                LoginHistory,
                LoginHistory.created_at,
                retention_days,
                sample_fmt=lambda h: f"login#{h.id}:{h.username}",
            )
        if data_type == "disaster_message":
            return self._expired_db_count_and_samples(
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

    # ── 실제 삭제 실행 ───────────────────────────────────────────────────
    def execute(self, *, policy_id: int | None = None) -> list[dict]:
        """만료된 데이터를 실제로 삭제한다.

        - is_active=False인 정책은 건너뛴다(자동 실행 대상이 아니므로).
        - expiry_action="delete"만 지원한다. "archive"/"anonymize"는 아직
          구현이 없어 건너뛰고 skipped_reason으로 알린다 — 조용히 아무 일도
          안 하는 것보다, 뭘 못 했는지 명시하는 게 삭제 기능에선 더 중요하다.
        - 정책별로 개별 커밋한다 — 하나가 실패해도 그 전까지 처리한 정책은
          남는다(전부 롤백되는 큰 트랜잭션 하나로 묶지 않음).
        """
        policies = self.repository.list_filtered(policy_id)
        results: list[dict] = []

        for p in policies:
            if not p.is_active:
                results.append(
                    {
                        "policy_id": p.id,
                        "data_type": p.data_type,
                        "data_label": p.data_label,
                        "expiry_action": p.expiry_action,
                        "executed_count": 0,
                        "skipped_reason": "정책이 중지 상태라 실행하지 않았습니다.",
                    }
                )
                continue

            if p.expiry_action != "delete":
                results.append(
                    {
                        "policy_id": p.id,
                        "data_type": p.data_type,
                        "data_label": p.data_label,
                        "expiry_action": p.expiry_action,
                        "executed_count": 0,
                        "skipped_reason": (
                            f"'{p.expiry_action}' 처리는 아직 지원하지 않습니다"
                            "(지금은 delete만 실행 가능)."
                        ),
                    }
                )
                continue

            executed_count = self._execute_for_data_type(p.data_type, p.retention_days)
            self.db.commit()
            results.append(
                {
                    "policy_id": p.id,
                    "data_type": p.data_type,
                    "data_label": p.data_label,
                    "expiry_action": p.expiry_action,
                    "executed_count": executed_count,
                    "skipped_reason": None,
                }
            )

        return results

    def _delete_expired_db(self, model, date_column, retention_days: int) -> int:
        """model을 ORM으로 하나씩 불러와서 지운다(bulk delete 대신) —

        Video.details/Search.analyses/Analysis.details가 relationship에
        cascade="all, delete-orphan"으로 걸려있는데, 이건 ORM 레벨 cascade라
        db.execute(delete(...)) 같은 bulk 삭제로는 안 타고, 개별 db.delete(row)
        로 불러와야 자식 row(VideoDetail/Analysis/AnalysisDetail)까지 같이
        지워진다. DB에 ON DELETE CASCADE가 없어서 이 방식이 아니면 FK 제약
        위반이 날 수 있다.
        """
        cutoff = _cutoff(retention_days)
        rows = self.db.scalars(select(model).where(date_column < cutoff)).all()
        for row in rows:
            self.db.delete(row)
        self.db.flush()
        return len(rows)

    def _execute_for_data_type(self, data_type: str, retention_days: int) -> int:
        settings = get_settings()
        if data_type == "cctv_video":
            # Video row만 지우면 실제 영상 파일이 디스크에 그대로 남으므로,
            # 파일도 같이 지운다.
            cutoff = _cutoff(retention_days)
            videos = self.db.scalars(
                select(Video).where(Video.created_at < cutoff)
            ).all()
            for v in videos:
                try:
                    Path(v.file_path).unlink(missing_ok=True)
                except OSError:
                    pass
                self.db.delete(v)
            self.db.flush()
            return len(videos)
        if data_type == "search_result":
            return self._delete_expired_db(Analysis, Analysis.created_at, retention_days)
        if data_type == "search_request":
            return self._delete_expired_db(Search, Search.searched_at, retention_days)
        if data_type == "login_history":
            return self._delete_expired_db(
                LoginHistory, LoginHistory.created_at, retention_days
            )
        if data_type == "disaster_message":
            return self._delete_expired_db(Message, Message.crt_dt, retention_days)
        if data_type == "clip_thumbnail":
            results_dir = Path(settings.results_dir)
            return _delete_expired_files(
                results_dir / "clips", retention_days
            ) + _delete_expired_files(results_dir / "thumbnails", retention_days)
        if data_type == "chroma_embedding":
            return _delete_expired_files(Path(settings.chroma_dir), retention_days)
        return 0