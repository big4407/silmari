"""사용자 프로필·관리자 승인 요청 Pydantic 스키마."""
from pydantic import BaseModel, Field

from backend.db.models import ApprovalStatus, UserRole


class UpdateMyProfileRequest(BaseModel):
    phone: str | None = Field(default=None, min_length=7, max_length=30)
    department: str | None = Field(default=None, max_length=150)
    position: str | None = Field(default=None, max_length=100)
    current_password: str | None = Field(default=None, min_length=1, max_length=128)
    new_password: str | None = Field(default=None, min_length=12, max_length=128)


class ApprovalRequest(BaseModel):
    status: ApprovalStatus
    role: UserRole | None = None
    rejection_reason: str | None = Field(default=None, max_length=500)
