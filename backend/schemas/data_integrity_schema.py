"""데이터 정합성 점검 API 스키마."""

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
        default=None, description="직전 실행 대비 이슈 수 증감 (최초 실행 시 null)"
    )
    run_id: str | None = Field(default=None, description="실행 회차 ID")


class IntegrityCheckIssuesResponse(BaseModel):
    check_id: str
    label: str
    issue_count: int
    issues: list[str] = Field(default_factory=list)
