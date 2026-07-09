from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import RetentionPolicy


class RetentionRepository:
    def __init__(self, db: Session):
        self.db = db

    def count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(RetentionPolicy)) or 0

    def list_ordered(self) -> list[RetentionPolicy]:
        return list(
            self.db.scalars(
                select(RetentionPolicy).order_by(RetentionPolicy.id)
            ).all()
        )

    def list_filtered(self, policy_id: int | None = None) -> list[RetentionPolicy]:
        stmt = select(RetentionPolicy).order_by(RetentionPolicy.id)
        if policy_id is not None:
            stmt = stmt.where(RetentionPolicy.id == policy_id)
        return list(self.db.scalars(stmt).all())

    def get(self, policy_id: int) -> RetentionPolicy | None:
        return self.db.get(RetentionPolicy, policy_id)
