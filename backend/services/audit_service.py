"""감사 로그 기록 — 관리자 행동을 admin_history 에 남긴다.

기록 실패가 본 작업(승인 등)을 막지 않도록 예외를 삼킨다(감사는 부가 기능).
호출 측에서 이미 db.commit() 을 했거나 할 예정이므로, 여기서는 add + flush 만 하고
커밋은 호출 측 트랜잭션에 맡기는 것을 기본으로 한다(같은 트랜잭션에 묶기 위해).
"""

from sqlalchemy.orm import Session

from backend.db.models import AdminAction, AdminHistory
from backend.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = AuditRepository(db)

    def record_admin_action(
        self,
        *,
        actor_id: str,
        action_type: AdminAction,
        target_type: str,
        target_id: str | None = None,
        detail: dict | None = None,
        batch_id: str | None = None,
        success: bool = True,
        ip_address: str | None = None,
    ) -> None:
        """관리자 행동 1건을 감사 로그에 기록.

        호출 측이 커밋하는 트랜잭션에 함께 묶인다. 기록 자체 실패는 무시(로깅만).
        """
        try:
            self.repository.add(
                AdminHistory(
                    actor_id=actor_id,
                    action_type=action_type,
                    target_type=target_type,
                    target_id=target_id,
                    detail=detail,
                    batch_id=batch_id,
                    success=success,
                    ip_address=ip_address,
                )
            )
        except Exception:
            # 감사 로그 실패가 본 작업을 막지 않도록 삼킨다.
            pass
