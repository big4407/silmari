from sqlalchemy.orm import Session, selectinload

from backend.db.models import Search, Analysis, AnalysisDetail, SearchType
from backend.schemas.search_schema import SearchCreate
from datetime import datetime, date, time
from sqlalchemy import desc, asc, or_, func


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

    def find_all_admin(
        self,
        page: int,
        per_page: int,
        keyword: str | None = None,
        search_type: str | None = None,
        requester_user_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[Search], int]:
        """관리자용 검색 요청 전체 조회 — 요청자 제한 없이 필터·페이지네이션.

        keyword는 이름·인상착의·실종지역에 부분 일치, requester_user_id는 정확히
        일치(요청자 선택 드롭다운용). start_date/end_date는 searched_at 기준.
        """
        query = self.db.query(Search).options(
            selectinload(Search.user), selectinload(Search.message)
        )

        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    Search.missing_name.like(like),
                    Search.clothing.like(like),
                    Search.missing_location.like(like),
                )
            )
        if search_type:
            query = query.filter(Search.search_type == search_type)
        if requester_user_id:
            query = query.filter(Search.user_id == requester_user_id)
        if start_date is not None:
            query = query.filter(
                Search.searched_at >= datetime.combine(start_date, time.min)
            )
        if end_date is not None:
            query = query.filter(
                Search.searched_at <= datetime.combine(end_date, time.max)
            )

        total = query.count()
        query = query.order_by(desc(Search.searched_at))
        items = query.offset((page - 1) * per_page).limit(per_page).all()

        return items, total

    def count_today_by_type(self) -> dict[str, int]:
        """오늘(로컬 날짜 기준) 검색 요청을 search_type별로 집계한다."""
        today = date.today()
        start = datetime.combine(today, time.min)
        end = datetime.combine(today, time.max)

        rows = (
            self.db.query(Search.search_type, func.count())
            .filter(Search.searched_at >= start, Search.searched_at <= end)
            .group_by(Search.search_type)
            .all()
        )
        counts = {search_type: count for search_type, count in rows}
        return {
            "today_total": sum(counts.values()),
            "today_sms": counts.get(SearchType.SMS.value, 0),
            "today_chatbot": counts.get(SearchType.CHATBOT.value, 0),
            "today_auto": counts.get(SearchType.AUTO.value, 0),
        }

    def delete(self, search: Search) -> None:
        """검색내역 삭제"""
        self.db.delete(search)
        self.db.commit()