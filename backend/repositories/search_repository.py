from sqlalchemy.orm import Session, selectinload

from backend.db.models import Search, Analysis, AnalysisDetail
from backend.schemas.search_schema import SearchCreate
from datetime import datetime, date
from sqlalchemy import desc, asc


class SearchRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, id: int) -> Search | None:
        return (
            self.db.query(Search)
            .options(
                selectinload(Search.analyses)
                .selectinload(Analysis.details)
                .selectinload(AnalysisDetail.video)
            )
            .filter(Search.id == id)
            .first()
        )

    def save(self, search_data: SearchCreate) -> Search:
        search = Search(**search_data.model_dump())

        self.db.add(search)
        self.db.commit()
        self.db.refresh(search)

        return search

    def find_all(
        self,
        page: int,
        per_page: int,
        # search_word: str|None=None, # 검색 기능은 이후 구현, 어떤 검색이 필요할지 나중에 판단
        user_id: str | None = None,
        order_by: str = "latest",
    ) -> tuple[list[Search], int]:
        query = self.db.query(Search)

        # user_id가 있으면 해당 사용자의 검색 내역만 조회
        if user_id:
            query = query.filter(Search.user_id == user_id)

        # 검색 기능은 이후 구현

        total = query.count()

        if order_by == "oldest":
            query = query.order_by(asc(Search.searched_at))
        else:
            query = query.order_by(desc(Search.searched_at))

        searchs = query.offset((page - 1) * per_page).limit(per_page).all()

        return searchs, total

    def delete(self, search: Search) -> None:
        """검색내역 삭제"""
        self.db.delete(search)
        self.db.commit()
