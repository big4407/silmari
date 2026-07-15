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
        detail, _analysis = self._create_search_and_run_analysis(search_data)
        return detail

    def create_search_with_match_count(
        self, search_data: SearchCreate
    ) -> tuple[SearchDetail, int]:
        """검색 생성 + 분석 실행 후 매칭 건수까지 함께 돌려준다.

        챗봇처럼 "몇 건 찾았는지"를 바로 응답에 써야 하는 호출부를 위한 것.
        AnalysisRepository를 직접 알 필요 없이 이 메서드 하나로 끝나게 한다.
        """
        detail, analysis = self._create_search_and_run_analysis(search_data)
        match_count = len(analysis.details) if analysis is not None else 0
        return detail, match_count

    def _create_search_and_run_analysis(self, search_data: SearchCreate):
        search = self.repository.save(search_data)
        detail = SearchDetail.model_validate(search)

        # 동기 실행 — 검색 시점엔 이미 인덱싱된 임베딩만 조회하므로 가벼움(1차 결정).
        # 나중에 검색 대상이 많아지면 BackgroundTasks 등 비동기 전환 검토.
        analysis = AnalysisService(self.db).run_analysis(detail)

        return detail, analysis

    def get_search(self, search_id: int) -> SearchDetail:
        search = self.repository.find_by_id(search_id)

        if search is None:
            raise ValueError("검색 기록을 찾을 수 없습니다.")

        analysis_results = []

        for analysis in search.analyses:
            for detail in analysis.details:
                analysis_results.append(
                    {
                        "id": detail.id,
                        "video_id": detail.video_id,
                        "video_path": detail.video.file_path if detail.video else None,
                        "video_timestamp": detail.video_timestamp,
                        "crop_id": detail.crop_id,
                        "position": detail.position,
                        "crop_img_path": detail.crop_img_path,
                        "matching_rate": detail.matching_rate,
                    }
                )

        search_detail = SearchDetail.model_validate(search)

        return search_detail.model_copy(
            update={"analysis_results": analysis_results}
        )

    def get_search_list(
        self,
        page: int,
        size: int,
        user_id: str | None,
    ) -> SearchListResponse:
        items, total = self.repository.find_all(
            page=page, per_page=size, user_id=user_id
        )

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
