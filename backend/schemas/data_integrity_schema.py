"""??? ??? ?? ?? ???."""

from datetime import datetime

from pydantic import BaseModel, Field


class IntegrityCheckResult(BaseModel):
    check_id: str
    label: str
    target: str
    description: str
    status: str = Field(description="ok | warn | error")
    issue_count: int = 0
    samples: list[str] = Field(default_factory=list)


class IntegrityRunResponse(BaseModel):
    ran_at: datetime
    total_issues: int
    checks: list[IntegrityCheckResult]
    delta_issues: int | None = Field(
        default=None, description="?? ?? ?? ?? ?? (??? null)"
    )
    run_id: str | None = Field(default=None, description="?? ?? ID")


class IntegrityCheckIssuesResponse(BaseModel):
    check_id: str
    label: str
    issue_count: int
    issues: list[str] = Field(default_factory=list)


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
