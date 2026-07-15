from datetime import date, datetime, timedelta
from pydantic import BaseModel, Field
from backend.utils.timeutils import kst_now


def _default_start_date() -> date:
    """검색 기본 시작일 — 오늘(KST) 기준 7일 전."""
    return (kst_now() - timedelta(days=7)).date()


def _default_end_date() -> date:
    """검색 기본 종료일 — 오늘(KST)."""
    return kst_now().date()


class VideoCreate(BaseModel):
    """영상 등록 입력 — process_videos 에서 경로 파싱 결과를 담는다."""

    cctv_serial_no: str | None = Field(default=None, max_length=50)
    file_path: str = Field(max_length=260)
    region_code: str | None = Field(default=None, max_length=10)
    recorded_at: date = Field(default_factory=_default_end_date)


class VideoDetailCreate(BaseModel):
    """영상 내 인물 탐지 1건 — video_timestamp(경과 초), crop_id, 위치."""

    video_id: int
    video_timestamp: int
    crop_id: int
    position: str = Field(max_length=100)


class CctvRegionCoverageItem(BaseModel):
    """지역 1건의 CCTV 수집 현황 — 관리자 콘솔 지역별 현황 표용."""

    region_code: str
    region_name: str | None = None
    cctv_count: int
    video_count: int
    status: str  # "수집됨" | "미수집"


class CctvSourceSummary(BaseModel):
    """CCTV 영상 수집 현황 화면 상단 통계 카드용.

    용량은 Video 테이블에 파일 크기 컬럼이 없어서 집계하지 않는다.
    """

    collected_region_count: int = 0
    video_file_count: int = 0
    missing_region_count: int = 0


class CctvRegionCoverageResponse(BaseModel):
    summary: CctvSourceSummary
    items: list[CctvRegionCoverageItem]