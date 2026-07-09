from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import Region


class RegionRepository:
    def __init__(self, db: Session):
        self.db = db

    def count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Region)) or 0

    def find_codes_by_keyword(self, keyword: str) -> list[str]:
        """지역명 자유 텍스트로 region_code 를 찾는다(부분 일치).

        full_name/specific_name 둘 중 하나라도 걸리면 후보로 포함한다.
        여러 개 걸리면 전부 반환(호출 측이 $in 필터로 사용).
        """
        rows = (
            self.db.query(Region.region_code)
            .filter(
                (Region.full_name.like(f"%{keyword}%"))
                | (Region.specific_name.like(f"%{keyword}%"))
            )
            .all()
        )
        return [row[0] for row in rows]
