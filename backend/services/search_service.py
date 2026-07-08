from math import ceil

from sqlalchemy.orm import Session

from backend.repositories.search_repository import SearchRepository
from backend.schemas.search_schema import (
    SearchCreate,
    SearchDetail,
    SearchListResponse,
    PagingInfo,
    SearchItem,
)
from backend.services.analysis_service import AnalysisService


class SearchService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = SearchRepository(db)

    def create_search(self, search_data: SearchCreate) -> SearchDetail:
        search = self.repository.save(search_data)
        detail = SearchDetail.model_validate(search)

        # 동기 실행 — 검색 시점엔 이미 인덱싱된 임베딩만 조회하므로 가벼움(1차 결정).
        # 나중에 검색 대상이 많아지면 BackgroundTasks 등 비동기 전환 검토.
        AnalysisService(self.db).run_analysis(detail)

        return detail

    def get_search(self, search_id: int) -> SearchDetail:
        search = self.repository.find_by_id(search_id)

        if search is None:
            raise ValueError("검색 기록을 찾을 수 없습니다.")

        return SearchDetail.model_validate(search)

    def get_search_list(self, page: int, size: int) -> SearchListResponse:
        items, total = self.repository.find_all(page=page, per_page=size)

        page_info = PagingInfo(
            total=total,
            total_pages=ceil(total / size) if total > 0 else 0,
            page=page,
            per_page=size,
            has_prev=page > 1,
            has_next=page * size < total,
        )

        return SearchListResponse(
            items=[SearchItem.model_validate(item) for item in items],
            page_info=page_info,
        )

    def delete_search(self, search_id: int) -> None:
        search = self.repository.find_by_id(search_id)

        if search is None:
            raise ValueError("검색 기록을 찾을 수 없습니다.")

        self.repository.delete(search)
