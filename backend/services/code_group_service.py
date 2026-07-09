"""코드 그룹 조회·참조 수·수정."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.db.models import (
    Analysis,
    Search,
    SysCodeGroup,
    SysCodeItem,
    User,
)
from backend.schemas.region_schema import CodeGroupEntry, CodeGroupItem, CodeGroupListResponse


def _ref_count(db: Session, group_key: str, code: str) -> int:
    if group_key == "user_role":
        return (
            db.scalar(select(func.count()).select_from(User).where(User.role == code))
            or 0
        )
    if group_key == "approval_status":
        return (
            db.scalar(
                select(func.count())
                .select_from(User)
                .where(User.approval_status == code)
            )
            or 0
        )
    if group_key == "search_type":
        return (
            db.scalar(
                select(func.count())
                .select_from(Search)
                .where(Search.search_type == code)
            )
            or 0
        )
    if group_key == "analysis_status":
        return (
            db.scalar(
                select(func.count())
                .select_from(Analysis)
                .where(Analysis.analysis_status == code)
            )
            or 0
        )
    return 0


def build_code_group_list(db: Session) -> CodeGroupListResponse:
    groups = list(
        db.scalars(
            select(SysCodeGroup)
            .options(selectinload(SysCodeGroup.items))
            .order_by(SysCodeGroup.sort_order, SysCodeGroup.group_key)
        ).all()
    )
    result: list[CodeGroupItem] = []
    for g in groups:
        items_sorted = sorted(g.items, key=lambda i: (i.sort_order, i.code))
        result.append(
            CodeGroupItem(
                group=g.group_key,
                group_label=g.group_label,
                description=g.description,
                items=[
                    CodeGroupEntry(
                        id=item.id,
                        code=item.code,
                        label=item.label,
                        description=item.description,
                        is_active=item.is_active,
                        ref_count=_ref_count(db, g.group_key, item.code),
                    )
                    for item in items_sorted
                ],
            )
        )
    return CodeGroupListResponse(groups=result)
