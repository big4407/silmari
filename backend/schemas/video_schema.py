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
    """ """

    cctv_serial_no: str | None = Field(default=None, max_length=50)
    file_path: str = Field(max_length=260)
    region_code: str | None = Field(default=None, max_length=10)
    recorded_at: date = Field(default_factory=_default_end_date)
    created_at: date = Field(default_factory=_default_end_date)
    embedding_id: str | None = Field(default=None, max_length=50)


class VideoDetail(BaseModel):
    """ """

    video_id: int
    video_timestamp: int
    crop_id: int
    position: str = Field(max_length=100)
