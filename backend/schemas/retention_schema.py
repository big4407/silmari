"""보존 정책 API 스키마."""

from datetime import datetime

from pydantic import BaseModel, Field


class RetentionPolicyItem(BaseModel):
    id: int
    data_type: str
    data_label: str
    storage_target: str
    retention_days: int
    expiry_action: str
    is_active: bool
    notes: str | None = None
    updated_at: datetime | None = None
    current_count: int = 0
    expired_count: int = 0


class RetentionDryRunItem(BaseModel):
    policy_id: int
    data_type: str
    data_label: str
    expiry_action: str
    expired_count: int = 0
    samples: list[str] = Field(default_factory=list)
    is_active: bool = True
    skipped_reason: str | None = None


class RetentionPolicyPatch(BaseModel):
    id: int
    retention_days: int | None = Field(default=None, ge=1, le=3650)
    expiry_action: str | None = Field(default=None, max_length=30)
    is_active: bool | None = None
    notes: str | None = Field(default=None, max_length=300)


class RetentionDryRunRequest(BaseModel):
    """UI에서 수정 중인 값으로 미리보기할 때 사용."""

    policies: list[RetentionPolicyPatch] | None = None


class RetentionDryRunResponse(BaseModel):
    items: list[RetentionDryRunItem]
    total_affected: int


class RetentionPolicyListResponse(BaseModel):
    items: list[RetentionPolicyItem]


class RetentionPolicyBulkUpdate(BaseModel):
    policies: list[RetentionPolicyPatch]
