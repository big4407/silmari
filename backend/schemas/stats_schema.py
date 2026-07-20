"""
관리자 통계(CCTV·검색·인구통계·발견해결결과) API 스키마.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class PeriodResponse(BaseModel):
    from_date: date
    to_date: date


class CctvSummary(BaseModel):
    registered_videos: int = 0
    indexed_videos: int = 0
    detected_persons: int = 0
    covered_regions: int = 0


class CctvRegionItem(BaseModel):
    region: str
    registered_videos: int
    indexed_videos: int
    detected_persons: int


class CctvStatsResponse(BaseModel):
    period: PeriodResponse
    summary: CctvSummary
    by_region: list[CctvRegionItem] = Field(default_factory=list)


class SearchSummary(BaseModel):
    total_searches: int = 0
    successful_matches: int = 0
    average_similarity_percent: float = 0.0
    average_processing_seconds: float = 0.0


class SearchTypeItem(BaseModel):
    search_type: str
    count: int
    successful_matches: int
    success_rate: float


class DailySearchItem(BaseModel):
    date: date
    search_count: int
    successful_count: int


class SearchStatsResponse(BaseModel):
    period: PeriodResponse
    summary: SearchSummary
    by_type: list[SearchTypeItem] = Field(default_factory=list)
    daily: list[DailySearchItem] = Field(default_factory=list)


class DistributionItem(BaseModel):
    label: str
    count: int
    ratio: float


class RegionDemographicItem(BaseModel):
    """지역별 검색·케이스 처리 현황.

    "발견"은 대기⇄진행중을 오가는 유동적인 상태라 통계에 안 남기기로 했다
    (services/stats_service.py 참고) — 완료(resolved) 여부만 집계한다.
    """

    region: str
    search_requests: int
    resolved_cases: int
    resolution_rate: float


class DemographicStatsResponse(BaseModel):
    period: PeriodResponse
    gender_distribution: list[DistributionItem] = Field(default_factory=list)
    age_distribution: list[DistributionItem] = Field(default_factory=list)
    by_region: list[RegionDemographicItem] = Field(default_factory=list)


class MissingPersonCaseSummaryItem(BaseModel):
    """발견/해결 결과 통계 화면의 "최근 케이스" 표용 — MissingPersonCase 1건."""

    id: int
    sn: str
    missing_name: str | None
    gender: str | None
    age: int | None
    missing_location: str | None
    status: str
    assigned_investigator_name: str | None
    assigned_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime


class OutcomeSummary(BaseModel):
    total_cases: int = 0
    resolved_cases: int = 0
    pending_cases: int = 0  # 대기 + 진행중(=미완료)
    resolution_rate: float = 0.0
    average_resolution_hours: float | None = None  # 담당 배정~완료까지 평균 소요시간


class OutcomeRegionItem(BaseModel):
    region: str
    total_cases: int
    resolved_cases: int
    resolution_rate: float


class OutcomeStatsResponse(BaseModel):
    period: PeriodResponse
    summary: OutcomeSummary
    by_region: list[OutcomeRegionItem] = Field(default_factory=list)
    recent_cases: list[MissingPersonCaseSummaryItem] = Field(default_factory=list)


StatType = Literal["cctv", "search", "demographic", "outcomes"]


class ExportRequest(BaseModel):
    stat_type: StatType
    from_date: date
    to_date: date
    region: str | None = None
    search_type: str | None = None
    file_format: Literal["CSV"] = "CSV"


class ExportLogItem(BaseModel):
    id: int
    stat_type: str
    from_date: date
    to_date: date
    file_format: str
    file_name: str
    row_count: int
    requested_by_name: str
    created_at: datetime