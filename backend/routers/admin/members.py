"""
[화면] MemberViews.jsx, AdminLayout.jsx
[서비스] audit_service.record_admin_action
[테이블] user, admin_history
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.deps import require_roles
from backend.core.security import utc_now
from backend.db.database import get_db
from backend.db.models import AdminAction, ApprovalStatus, User, UserRole
from backend.schemas.auth import UserResponse
from backend.schemas.user import ApprovalRequest
from backend.services.audit_service import record_admin_action

from .tags import TAG_MEMBERS

router = APIRouter()


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="회원 목록 조회",
    description="가입 신청·승인·반려·정지 상태의 회원 목록을 최신순으로 반환합니다.",
    tags=TAG_MEMBERS,
)
def list_users(
    approval_status: ApprovalStatus | None = Query(
        default=None,
        description="승인 상태 필터: 0=대기, 1=승인, 2=반려, 3=정지",
    ),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[User]:
    stmt = select(User).order_by(User.created_at.desc())
    if approval_status is not None:
        stmt = stmt.where(User.approval_status == approval_status)
    return list(db.scalars(stmt).all())


@router.patch(
    "/users/{user_id}/approval",
    response_model=UserResponse,
    summary="회원 승인·반려·정지",
    description="관리자가 회원 가입을 승인하거나 반려·정지합니다. 승인 시 역할(investigator 등)을 부여합니다.",
    tags=TAG_MEMBERS,
)
def update_approval(
    user_id: str,
    payload: ApprovalRequest,
    request: Request,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    if target.id == admin.id and payload.status != ApprovalStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail="본인 계정은 이 API로 정지하거나 반려할 수 없습니다.",
        )

    before = {
        "role": target.role.value if target.role else None,
        "approval_status": target.approval_status.value,
    }

    if payload.status == ApprovalStatus.APPROVED:
        never_approved = target.role is None and payload.role is None
        if never_approved and before["approval_status"] in ("2", "3"):
            target.approval_status = ApprovalStatus.PENDING
            target.approved_at = None
            target.approved_by_id = None
            target.rejection_reason = None
            action = AdminAction.REACTIVATE
            reason = "승인 이력이 없어 승인 대기 상태로 되돌림"
        else:
            assigned_role = payload.role or target.requested_role
            target.role = assigned_role
            target.approval_status = ApprovalStatus.APPROVED
            target.approved_at = utc_now()
            target.approved_by_id = admin.id
            target.rejection_reason = None
            action = (
                AdminAction.APPROVE
                if before["approval_status"] == "0"
                else AdminAction.REACTIVATE
            )
            reason = None
    elif payload.status == ApprovalStatus.REJECTED:
        target.role = None
        target.approval_status = ApprovalStatus.REJECTED
        target.approved_at = None
        target.approved_by_id = admin.id
        target.rejection_reason = (
            payload.rejection_reason or "관리자 검토 결과 가입 신청이 반려되었습니다."
        )
        action = AdminAction.REJECT
        reason = target.rejection_reason
    elif payload.status == ApprovalStatus.SUSPENDED:
        target.approval_status = ApprovalStatus.SUSPENDED
        target.approved_by_id = admin.id
        target.rejection_reason = (
            payload.rejection_reason or "관리자에 의해 계정 사용이 정지되었습니다."
        )
        action = AdminAction.SUSPEND
        reason = target.rejection_reason
    else:
        raise HTTPException(
            status_code=422, detail="pending 상태로 되돌리는 작업은 지원하지 않습니다."
        )

    db.add(target)
    record_admin_action(
        db,
        actor_id=admin.id,
        action_type=action,
        target_type="user",
        target_id=target.id,
        detail={
            "target_username": target.username,
            "target_name": target.full_name,
            "before": before,
            "after": {
                "role": target.role.value if target.role else None,
                "approval_status": target.approval_status.value,
            },
            "reason": reason,
        },
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(target)
    return target
