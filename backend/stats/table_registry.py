from __future__ import annotations

from sqlalchemy import MetaData, Table
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session


class StatsSourceError(RuntimeError):
    pass


class StatsTableRegistry:
    """
    기존 테이블을 SQLAlchemy reflection으로 읽습니다.
    따라서 기존 ORM model 파일을 import하거나 수정할 필요가 없습니다.
    """

    def __init__(self, db: Session):
        self.bind = db.get_bind()
        self.metadata = MetaData()
        self._tables: dict[str, Table] = {}

    def table(self, name: str) -> Table:
        if name not in self._tables:
            try:
                self._tables[name] = Table(
                    name,
                    self.metadata,
                    autoload_with=self.bind,
                )
            except Exception as exc:
                raise StatsSourceError(
                    f"통계 원본 테이블 '{name}'을 찾거나 반영할 수 없습니다."
                ) from exc

        return self._tables[name]

    @staticmethod
    def column(
        table: Table,
        name: str,
        *,
        required: bool = True,
    ):
        if name and name in table.c:
            return table.c[name]

        if required:
            raise StatsSourceError(
                f"'{table.name}' 테이블에 '{name}' 컬럼이 없습니다."
            )

        return None
