from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.deps import require_roles
from backend.core.security import utc_now
from backend.db.database import get_db
from backend.db.models import ApprovalStatus, User, UserRole
from backend.schemas.auth import UserResponse
from backend.schemas.user import ApprovalRequest

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=list[UserResponse])
def list_users(
    approval_status: ApprovalStatus | None = Query(default=None),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[User]:
    stmt = select(User).order_by(User.created_at.desc())
    if approval_status is not None:
        stmt = stmt.where(User.approval_status == approval_status)
    return list(db.scalars(stmt).all())


@router.patch("/users/{user_id}/approval", response_model=UserResponse)
def update_approval(
    user_id: str,
    payload: ApprovalRequest,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    if target.id == admin.id and payload.status != ApprovalStatus.APPROVED:
        raise HTTPException(status_code=400, detail="본인 계정은 이 API로 정지하거나 반려할 수 없습니다.")

    if payload.status == ApprovalStatus.APPROVED:
        assigned_role = payload.role or target.requested_role
        target.role = assigned_role
        target.approval_status = ApprovalStatus.APPROVED
        target.approved_at = utc_now()
        target.approved_by_id = admin.id
        target.rejection_reason = None
    elif payload.status == ApprovalStatus.REJECTED:
        target.role = None
        target.approval_status = ApprovalStatus.REJECTED
        target.approved_at = None
        target.approved_by_id = admin.id
        target.rejection_reason = payload.rejection_reason or "관리자 검토 결과 가입 신청이 반려되었습니다."
    elif payload.status == ApprovalStatus.SUSPENDED:
        target.approval_status = ApprovalStatus.SUSPENDED
        target.approved_by_id = admin.id
        target.rejection_reason = payload.rejection_reason or "관리자에 의해 계정 사용이 정지되었습니다."
    else:
        raise HTTPException(status_code=422, detail="pending 상태로 되돌리는 작업은 지원하지 않습니다.")

    db.add(target)
    db.commit()
    db.refresh(target)
    return target
