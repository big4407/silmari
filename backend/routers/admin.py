"""
관리자 API — 회원 승인·반려·역할 부여.

[RBAC] require_roles(UserRole.ADMIN) — admin 역할만 접근
[핵심] PATCH /admin/users/{id}/approval — pending → approved/rejected/suspended
"""

from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.deps import require_roles
from backend.core.security import utc_now
from backend.db.database import get_db
from backend.db.models import (
    AdminAction,
    AdminHistory,
    ApprovalStatus,
    LoginHistory,
    User,
    UserRole,
)
from backend.schemas.auth_schema import UserResponse
from backend.schemas.user_schema import ApprovalRequest
from backend.schemas.login_history_schema import (
    LoginHistoryItem,
    LoginHistoryListResponse,
)
from backend.utils.timeutils import kst_now
from backend.services.audit_service import AuditService
from backend.schemas.admin_history_schema import (
    AdminHistoryItem,
    AdminHistoryListResponse,
)

router = APIRouter(prefix="/admin")


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

    # 변경 전 상태 (감사 로그 detail 의 before)
    before = {
        "role": target.role.value if target.role else None,
        "approval_status": target.approval_status.value,
    }
    was_approved = target.approval_status == ApprovalStatus.APPROVED

    if payload.status == ApprovalStatus.APPROVED:
        # [안전장치] 승인된 적 없는 계정(role 없음)을 정지 해제하는 경우,
        # 승인으로 바로 넘기지 않고 '승인 대기'로 되돌린다. 검토 없이 승인되는 것을 방지.
        never_approved = target.role is None and payload.role is None
        if never_approved and before["approval_status"] in ("2", "3"):
            # 정지·반려 상태 + 승인 이력 없음 → 대기로 복귀
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
            # 반려·정지에서 다시 승인이면 재승인(REACTIVATE), 신규 대기 승인이면 APPROVE
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

    # 감사 로그 기록 (같은 트랜잭션에 묶어 커밋)
    AuditService(db).record_admin_action(
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


@router.get("/login-history", response_model=LoginHistoryListResponse)
def list_login_history(
    username: str | None = Query(default=None, description="아이디 부분 검색"),
    success: bool | None = Query(default=None, description="성공/실패 필터"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> LoginHistoryListResponse:
    """로그인 이력(감사 로그) 조회 — 최신순, 필터·페이지네이션."""
    # user 와 LEFT JOIN 해서 full_name 도 함께 (없는 계정 시도면 None)
    base = select(LoginHistory, User.full_name).join(
        User, LoginHistory.user_id == User.id, isouter=True
    )

    conds = []
    if username:
        conds.append(LoginHistory.username.like(f"%{username}%"))
    if success is not None:
        conds.append(LoginHistory.success == success)
    if start_date is not None:
        conds.append(LoginHistory.created_at >= datetime.combine(start_date, time.min))
    if end_date is not None:
        conds.append(LoginHistory.created_at <= datetime.combine(end_date, time.max))
    for c in conds:
        base = base.where(c)

    # 총 건수
    count_stmt = select(func.count()).select_from(LoginHistory)
    for c in conds:
        count_stmt = count_stmt.where(c)
    total = db.scalar(count_stmt) or 0

    # 페이지 데이터
    rows = db.execute(
        base.order_by(LoginHistory.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()

    items = []
    for lh, full_name in rows:
        item = LoginHistoryItem.model_validate(lh)
        item.full_name = full_name  # JOIN 으로 얻은 값 주입 (스키마 기본값 None 이라 검증 통과 후 할당)
        items.append(item)

    # 오늘(KST) 요약
    today_start = datetime.combine(kst_now().date(), time.min)
    today_base = (
        select(func.count())
        .select_from(LoginHistory)
        .where(LoginHistory.created_at >= today_start)
    )
    today_success = db.scalar(today_base.where(LoginHistory.success == True)) or 0  # noqa: E712
    today_failed = db.scalar(today_base.where(LoginHistory.success == False)) or 0  # noqa: E712

    return LoginHistoryListResponse(
        items=items,
        total=total,
        page=page,
        size=per_page,
        today_success=today_success,
        today_failed=today_failed,
    )


@router.get("/admin-history", response_model=AdminHistoryListResponse)
def list_admin_history(
    action_type: AdminAction | None = Query(default=None, description="행동 유형 필터"),
    approval_only: bool = Query(default=False, description="승인·권한 변경만(1~4)"),
    actor: str | None = Query(default=None, description="행위자 이름·아이디 부분 검색"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> AdminHistoryListResponse:
    """관리자 행동 이력(감사 로그) 조회 — 최신순, 필터·페이지네이션.

    approval_only=True 면 승인·권한 변경(APPROVE~REACTIVATE)만 → 승인 이력 뷰용.
    """
    base = select(AdminHistory, User.full_name).join(
        User, AdminHistory.actor_id == User.id, isouter=True
    )

    conds = []
    if action_type is not None:
        conds.append(AdminHistory.action_type == action_type)
    if approval_only:
        conds.append(
            AdminHistory.action_type.in_(
                [
                    AdminAction.APPROVE,
                    AdminAction.REJECT,
                    AdminAction.SUSPEND,
                    AdminAction.REACTIVATE,
                ]
            )
        )
    if actor:
        conds.append(
            or_(
                User.full_name.like(f"%{actor}%"),
                User.username.like(f"%{actor}%"),
            )
        )
    if start_date is not None:
        conds.append(AdminHistory.created_at >= datetime.combine(start_date, time.min))
    if end_date is not None:
        conds.append(AdminHistory.created_at <= datetime.combine(end_date, time.max))
    for c in conds:
        base = base.where(c)

    count_stmt = select(func.count()).select_from(AdminHistory)
    # actor 검색은 User 조인이 필요하므로 count 에도 반영
    if actor:
        count_stmt = count_stmt.join(
            User, AdminHistory.actor_id == User.id, isouter=True
        )
    for c in conds:
        count_stmt = count_stmt.where(c)
    total = db.scalar(count_stmt) or 0

    rows = db.execute(
        base.order_by(AdminHistory.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()

    items = []
    for ah, actor_name in rows:
        item = AdminHistoryItem.model_validate(ah)
        item.actor_name = actor_name
        items.append(item)

    return AdminHistoryListResponse(items=items, total=total, page=page, size=per_page)
