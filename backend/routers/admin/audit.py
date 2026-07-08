"""
[화면] AuditViews.jsx, DataViews.jsx
[서비스] — (라우터에서 ORM 쿼리)
[테이블] login_history, admin_history, user
"""
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.deps import require_roles
from backend.db.database import get_db
from backend.db.models import AdminAction, AdminHistory, LoginHistory, User, UserRole
from backend.schemas.admin_history_schema import (
    AdminHistoryItem,
    AdminHistoryListResponse,
)
from backend.schemas.login_history_schema import (
    LoginHistoryItem,
    LoginHistoryListResponse,
)
from backend.utils.timeutils import kst_now

from .tags import TAG_AUDIT

router = APIRouter()


@router.get(
    "/login-history",
    response_model=LoginHistoryListResponse,
    summary="로그인 이력 조회",
    tags=TAG_AUDIT,
)
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

    count_stmt = select(func.count()).select_from(LoginHistory)
    for c in conds:
        count_stmt = count_stmt.where(c)
    total = db.scalar(count_stmt) or 0

    rows = db.execute(
        base.order_by(LoginHistory.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()

    items = []
    for lh, full_name in rows:
        item = LoginHistoryItem.model_validate(lh)
        item.full_name = full_name
        items.append(item)

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


@router.get(
    "/admin-history",
    response_model=AdminHistoryListResponse,
    summary="관리자 작업 이력 조회",
    tags=TAG_AUDIT,
)
def list_admin_history(
    action_type: AdminAction | None = Query(default=None, description="행동 유형 필터"),
    approval_only: bool = Query(default=False, description="승인·권한 변경만(1~4)"),
    actor: str | None = Query(default=None, description="행위자 이름·아이디 부분 검색"),
    target_type: str | None = Query(default=None, description="대상 유형 필터 (user, region 등)"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> AdminHistoryListResponse:
    """관리자 행동 이력(감사 로그) 조회 — 최신순, 필터·페이지네이션."""
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
    if target_type:
        conds.append(AdminHistory.target_type == target_type)
    if start_date is not None:
        conds.append(AdminHistory.created_at >= datetime.combine(start_date, time.min))
    if end_date is not None:
        conds.append(AdminHistory.created_at <= datetime.combine(end_date, time.max))
    for c in conds:
        base = base.where(c)

    count_stmt = select(func.count()).select_from(AdminHistory)
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
