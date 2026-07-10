"""행정구역 API 스키마."""

from datetime import datetime

from pydantic import BaseModel, Field


class RegionItem(BaseModel):
    region_code: str
    full_name: str | None = None
    specific_name: str | None = None
    parent_code: str | None = None
    child_count: int = 0
    video_count: int = 0
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class RegionListResponse(BaseModel):
    items: list[RegionItem]
    total: int
    page: int
    size: int
    parent_code: str | None = None


class RegionCreate(BaseModel):
    region_code: str = Field(..., min_length=1, max_length=10)
    full_name: str | None = Field(default=None, max_length=100)
    specific_name: str = Field(..., min_length=1, max_length=20)
    parent_code: str | None = Field(default=None, max_length=10)


class RegionUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=100)
    specific_name: str | None = Field(default=None, max_length=20)
    parent_code: str | None = Field(default=None, max_length=10)


class RegionOption(BaseModel):
    region_code: str
    label: str
    parent_code: str | None = None


class RegionOptionsResponse(BaseModel):
    items: list[RegionOption]


class RegionImportResult(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = Field(default_factory=list)
    format: str = Field(default="region", description="region | administrative_dong")
    legal_dong_created: int = 0
    legal_dong_updated: int = 0
    csv_rows: int = 0


class RegionClearResult(BaseModel):
    region_deleted: int = 0
    legal_dong_deleted: int = 0
    video_unlinked: int = 0


class AdministrativeDongImportResult(BaseModel):
    sido_count: int = 0
    sigungu_count: int = 0
    admin_dong_count: int = 0
    legal_dong_count: int = 0
    csv_rows: int = 0
    errors: list[str] = Field(default_factory=list)
