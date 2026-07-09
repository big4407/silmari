"""정합성 검사 감사 로그 — 실행 이력 저장·복원."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import AdminAction, AdminHistory
from backend.schemas.data_integrity_schema import IntegrityCheckResult, IntegrityRunResponse


def get_previous_integrity_total(db: Session) -> int | None:
    """직전 정합성 검사의 total_issues. 없으면 None."""
    detail = db.scalar(
        select(AdminHistory.detail)
        .where(AdminHistory.target_type == "integrity_check")
        .order_by(AdminHistory.created_at.desc())
        .limit(1)
    )
    if not isinstance(detail, dict) or detail.get("action") != "run":
        return None
    total = detail.get("total_issues")
    return int(total) if total is not None else None


def build_integrity_detail(
    checks: list[IntegrityCheckResult],
    total_issues: int,
    delta_issues: int | None,
) -> dict:
    return {
        "action": "run",
        "total_issues": total_issues,
        "ok_count": sum(1 for c in checks if c.status == "ok"),
        "warn_count": sum(1 for c in checks if c.status == "warn"),
        "error_count": sum(1 for c in checks if c.status == "error"),
        "check_count": len(checks),
        "delta_issues": delta_issues,
        "checks": [c.model_dump(mode="json") for c in checks],
    }


def record_integrity_run(
    db: Session,
    *,
    actor_id: str,
    checks: list[IntegrityCheckResult],
    total_issues: int,
    delta_issues: int | None,
    ip_address: str | None,
) -> str | None:
    """정합성 검사 실행 1건을 admin_history에 기록. 실패 시 None."""
    try:
        entry = AdminHistory(
            actor_id=actor_id,
            action_type=AdminAction.UPDATE,
            target_type="integrity_check",
            target_id=str(total_issues),
            detail=build_integrity_detail(checks, total_issues, delta_issues),
            success=True,
            ip_address=ip_address,
        )
        db.add(entry)
        db.flush()
        return entry.id
    except Exception:
        return None


def _integrity_run_from_row(row: AdminHistory) -> IntegrityRunResponse | None:
    if not isinstance(row.detail, dict):
        return None
    detail = row.detail
    if detail.get("action") != "run":
        return None
    raw_checks = detail.get("checks") or []
    checks = [IntegrityCheckResult.model_validate(c) for c in raw_checks]
    return IntegrityRunResponse(
        ran_at=row.created_at,
        total_issues=int(detail.get("total_issues") or 0),
        checks=checks,
        delta_issues=detail.get("delta_issues"),
        run_id=row.id,
    )


def latest_integrity_run(db: Session) -> IntegrityRunResponse | None:
    """가장 최근 정합성 검사 결과를 감사 로그에서 복원."""
    row = db.scalar(
        select(AdminHistory)
        .where(AdminHistory.target_type == "integrity_check")
        .order_by(AdminHistory.created_at.desc())
        .limit(1)
    )
    if row is None:
        return None
    return _integrity_run_from_row(row)


def get_integrity_run_by_id(db: Session, run_id: str) -> IntegrityRunResponse | None:
    """감사 로그 ID로 정합성 검사 결과 복원."""
    row = db.get(AdminHistory, run_id)
    if row is None or row.target_type != "integrity_check":
        return None
    return _integrity_run_from_row(row)
