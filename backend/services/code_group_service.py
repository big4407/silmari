"""코드 그룹 조회·참조 수·수정."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import Analysis, Search, User
from backend.repositories.code_group_repository import CodeGroupRepository
from backend.schemas.region_schema import CodeGroupEntry, CodeGroupItem, CodeGroupListResponse


class CodeGroupService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = CodeGroupRepository(db)

    def build_list(self) -> CodeGroupListResponse:
        groups = self.repository.list_groups_with_items()
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
                            ref_count=self._ref_count(g.group_key, item.code),
                        )
                        for item in items_sorted
                    ],
                )
            )
        return CodeGroupListResponse(groups=result)

    def _ref_count(self, group_key: str, code: str) -> int:
        if group_key == "user_role":
            return (
                self.db.scalar(
                    select(func.count()).select_from(User).where(User.role == code)
                )
                or 0
            )
        if group_key == "approval_status":
            return (
                self.db.scalar(
                    select(func.count())
                    .select_from(User)
                    .where(User.approval_status == code)
                )
                or 0
            )
        if group_key == "search_type":
            return (
                self.db.scalar(
                    select(func.count())
                    .select_from(Search)
                    .where(Search.search_type == code)
                )
                or 0
            )
        if group_key == "analysis_status":
            return (
                self.db.scalar(
                    select(func.count())
                    .select_from(Analysis)
                    .where(Analysis.analysis_status == code)
                )
                or 0
            )
        return 0
