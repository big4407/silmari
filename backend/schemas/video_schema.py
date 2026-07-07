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
