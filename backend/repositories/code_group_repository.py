from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.db.models import SysCodeGroup, SysCodeItem


class CodeGroupRepository:
    def __init__(self, db: Session):
        self.db = db

    def group_count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(SysCodeGroup)) or 0

    def list_groups_with_items(self) -> list[SysCodeGroup]:
        return list(
            self.db.scalars(
                select(SysCodeGroup)
                .options(selectinload(SysCodeGroup.items))
                .order_by(SysCodeGroup.sort_order, SysCodeGroup.group_key)
            ).all()
        )

    def get_group(self, group_key: str) -> SysCodeGroup | None:
        return self.db.get(SysCodeGroup, group_key)

    def get_item(self, group_key: str, code: str) -> SysCodeItem | None:
        return self.db.scalar(
            select(SysCodeItem).where(
                SysCodeItem.group_key == group_key,
                SysCodeItem.code == code,
            )
        )
