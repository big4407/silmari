from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


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
    region: str
    search_requests: int
    found_cases: int
    resolved_cases: int
    finding_rate: float
    resolution_rate: float


class DemographicStatsResponse(BaseModel):
    period: PeriodResponse
    gender_distribution: list[DistributionItem] = Field(default_factory=list)
    age_distribution: list[DistributionItem] = Field(default_factory=list)
    by_region: list[RegionDemographicItem] = Field(default_factory=list)


CaseEventType = Literal["FOUND", "RESOLVED"]


class CaseEventCreate(BaseModel):
    case_key: str | None = Field(default=None, max_length=100)
    event_type: CaseEventType
    occurred_at: datetime

    actor_id: int | None = None
    actor_name: str | None = Field(default=None, max_length=100)
    actor_role: str | None = Field(default=None, max_length=50)

    location_text: str | None = Field(default=None, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    region: str | None = Field(default=None, max_length=255)

    source_search_id: int | None = None
    source_analysis_id: int | None = None
    source_analysis_detail_id: int | None = None
    reported_at: datetime | None = None
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_reference(self):
        if not self.case_key and self.source_search_id is None:
            raise ValueError(
                "case_key 또는 source_search_id 중 하나는 필요합니다."
            )
        return self


class CaseEventResponse(BaseModel):
    id: int
    case_key: str
    event_type: CaseEventType
    occurred_at: datetime
    reported_at: datetime | None
    region: str | None
    actor_name: str | None
    actor_role: str | None
    recorded_by_name: str
    location_text: str | None
    source_search_id: int | None
    source_analysis_id: int | None
    source_analysis_detail_id: int | None
    note: str | None
    created_at: datetime


class OutcomeSummary(BaseModel):
    found_cases: int = 0
    resolved_cases: int = 0
    resolution_after_found_rate: float = 0.0
    average_hours_to_find: float | None = None
    average_hours_to_resolve: float | None = None


class OutcomeRegionItem(BaseModel):
    region: str
    found_cases: int
    resolved_cases: int
    resolution_rate: float


class OutcomeStatsResponse(BaseModel):
    period: PeriodResponse
    summary: OutcomeSummary
    by_region: list[OutcomeRegionItem] = Field(default_factory=list)
    recent_records: list[CaseEventResponse] = Field(default_factory=list)


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
