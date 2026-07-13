"""정합성 검사 실행 이력 — admin_history 조회·저장."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import AdminAction, AdminHistory
from backend.repositories.audit_repository import AuditRepository
from backend.schemas.data_integrity_schema import IntegrityCheckResult, IntegrityRunResponse


class IntegrityRepository:
    def __init__(self, db: Session):
        self.db = db
        self._audit = AuditRepository(db)

    def get_previous_total_issues(self) -> int | None:
        detail = self.db.scalar(
            select(AdminHistory.detail)
            .where(AdminHistory.target_type == "integrity_check")
            .order_by(AdminHistory.created_at.desc())
            .limit(1)
        )
        if not isinstance(detail, dict) or detail.get("action") != "run":
            return None
        total = detail.get("total_issues")
        return int(total) if total is not None else None

    def latest_run(self) -> IntegrityRunResponse | None:
        row = self.db.scalar(
            select(AdminHistory)
            .where(AdminHistory.target_type == "integrity_check")
            .order_by(AdminHistory.created_at.desc())
            .limit(1)
        )
        if row is None:
            return None
        return self._run_from_row(row)

    def get_run_by_id(self, run_id: str) -> IntegrityRunResponse | None:
        row = self.db.get(AdminHistory, run_id)
        if row is None or row.target_type != "integrity_check":
            return None
        return self._run_from_row(row)

    def record_run(
        self,
        *,
        actor_id: str,
        checks: list[IntegrityCheckResult],
        total_issues: int,
        delta_issues: int | None,
        ip_address: str | None,
    ) -> str | None:
        try:
            entry = AdminHistory(
                actor_id=actor_id,
                action_type=AdminAction.UPDATE,
                target_type="integrity_check",
                target_id=str(total_issues),
                detail=self._build_detail(checks, total_issues, delta_issues),
                success=True,
                ip_address=ip_address,
            )
            self._audit.add(entry)
            return entry.id
        except Exception:
            return None

    @staticmethod
    def _build_detail(
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

    @staticmethod
    def _run_from_row(row: AdminHistory) -> IntegrityRunResponse | None:
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
