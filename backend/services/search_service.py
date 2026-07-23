from math import ceil

from sqlalchemy.orm import Session

from backend.repositories.search_repository import SearchRepository
from backend.schemas.search_schema import (
    AdminSearchItem,
    AdminSearchListResponse,
    AdminSearchSummary,
    SearchCreate,
    SearchDetail,
    SearchListResponse,
    PagingInfo,
    SearchItem,
)
from backend.services.analysis_service import AnalysisService

from backend.repositories.video_repository import VideoRepository
from backend.repositories.region_repository import RegionRepository

from backend.services.video_period_validator import (
    VideoPeriodValidator,
    VideoPeriodValidationStatus,
)
from backend.services.region_resolver import RegionResolver, RegionResolveStatus

from datetime import date


class SearchValidationError(Exception):
    """검색 조건 검증 실패의 기본 예외."""


class RegionNotFoundError(SearchValidationError):
    """입력한 지역을 찾을 수 없음."""


class RegionAmbiguousError(SearchValidationError):
    """입력한 지역에 여러 후보가 존재함."""

    def __init__(self, candidate_names: list[str]):
        self.candidate_names = candidate_names
        super().__init__(", ".join(candidate_names))


class InvalidVideoPeriodError(SearchValidationError):
    """시작일이 종료일보다 늦음."""


class VideoNotFoundError(SearchValidationError):
    """해당 지역과 기간에 CCTV 영상이 없음."""

# 최종 정렬 점수 = matching_rate(FashionCLIP 코사인 유사도) + color_match_rate
# (실제 색상 매칭, core/search/color_matching.py)의 가중합. 원값(matching_rate,
# color_match_rate)은 AnalysisDetail에 그대로 저장해두고, 조합은 조회 시점에만
# 계산한다 — 가중치를 나중에 튜닝해도 DB를 다시 채울 필요가 없게 하기 위함.
# color_match_rate가 없으면(텍스트에 색상 정보 자체가 없던 검색) matching_rate만
# 그대로 쓴다.
MATCHING_RATE_WEIGHT = 0.6
COLOR_MATCH_RATE_WEIGHT = 0.4


def _compute_final_score(matching_rate: float, color_match_rate: float | None) -> float:
    if color_match_rate is None:
        return round(matching_rate, 4)
    return round(
        matching_rate * MATCHING_RATE_WEIGHT
        + color_match_rate * COLOR_MATCH_RATE_WEIGHT,
        4,
    )


class SearchService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = SearchRepository(db)

        self.video_repository = VideoRepository(db)
        self.region_repository = RegionRepository(db)

        self.period_validator = VideoPeriodValidator(
            self.video_repository,
            self.region_repository,
        )
        self.region_resolver = RegionResolver(self.region_repository)

    def create_search(
        self,
        search_data: SearchCreate,
    ) -> SearchDetail:
        region_result = self.region_resolver.resolve(
            search_data.missing_location,
        )

        if region_result.status == RegionResolveStatus.NOT_FOUND:
            raise RegionNotFoundError()

        if region_result.status == RegionResolveStatus.AMBIGUOUS:
            candidate_names = [
                candidate.full_name for candidate in region_result.candidates[:5]
            ]

            raise RegionAmbiguousError(candidate_names)

        start_date = self._to_date(search_data.start_date)
        end_date = self._to_date(search_data.end_date)

        period_result = self.period_validator.validate(
            region_code=region_result.region_code,
            start_date=start_date,
            end_date=end_date,
        )

        if period_result.status == VideoPeriodValidationStatus.INVALID_RANGE:
            raise InvalidVideoPeriodError()

        if period_result.status == VideoPeriodValidationStatus.VIDEO_NOT_FOUND:
            raise VideoNotFoundError()

        # 검증이 모두 통과한 경우에만 검색 및 분석 실행
        detail, _analysis = self._create_search_and_run_analysis(
            search_data,
        )

        return detail

    @staticmethod
    def _to_date(value: date | str) -> date:
        if isinstance(value, date):
            return value

        return date.fromisoformat(value)

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
                        "color_match_rate": detail.color_match_rate,
                        "final_score": _compute_final_score(
                            detail.matching_rate, detail.color_match_rate
                        ),
                        "recorded_at": detail.video.recorded_at if detail.video else None,
                        "video_region": (
    detail.video.region.full_name
    if detail.video and detail.video.region
    else None
),
                    }
                )

        analysis_results.sort(key=lambda item: item["final_score"], reverse=True)

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

    def list_for_admin(
        self,
        page: int,
        size: int,
        keyword: str | None = None,
        search_type: str | None = None,
        requester_user_id: str | None = None,
        start_date=None,
        end_date=None,
    ) -> AdminSearchListResponse:
        """관리자 콘솔의 검색 요청 이력 화면용 — 전체 사용자 대상, 필터+오늘 요약."""
        items, total = self.repository.find_all_admin(
            page=page,
            per_page=size,
            keyword=keyword,
            search_type=search_type,
            requester_user_id=requester_user_id,
            start_date=start_date,
            end_date=end_date,
        )

        admin_items = []
        for item in items:
            preview = None
            if item.message is not None and item.message.msg_cn:
                preview = item.message.msg_cn[:60]

            data = AdminSearchItem.model_validate(item).model_dump()
            data.update(
                requester_name=item.user.full_name if item.user else None,
                requester_username=item.user.username if item.user else None,
                message_preview=preview,
            )
            admin_items.append(AdminSearchItem(**data))

        page_info = PagingInfo(
            total=total,
            total_pages=ceil(total / size) if total > 0 else 0,
            page=page,
            per_page=size,
            has_prev=page > 1,
            has_next=page * size < total,
        )

        summary = AdminSearchSummary(**self.repository.get_summary_counts())

        return AdminSearchListResponse(
            items=admin_items, page_info=page_info, summary=summary)