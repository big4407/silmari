"""인증 API 요청/응답 Pydantic 스키마 — signup, login, token, user profile."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.db.models import ApprovalStatus, UserRole


class SignUpRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)
    organization: str = Field(min_length=2, max_length=150)
    department: str | None = Field(default=None, max_length=150)
    position: str | None = Field(default=None, max_length=100)
    phone: str = Field(min_length=7, max_length=30)
    requested_role: UserRole = UserRole.INVESTIGATOR


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_expires_in_seconds: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: EmailStr
    full_name: str
    organization: str
    department: str | None
    position: str | None
    phone: str
    requested_role: UserRole
    role: UserRole | None
    approval_status: ApprovalStatus
    rejection_reason: str | None
    created_at: datetime
    approved_at: datetime | None


class SignUpResponse(BaseModel):
    message: str
    user: UserResponse


class FindUsernameRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr


class FindUsernameResponse(BaseModel):
    username: str


class ResetPasswordRequest(BaseModel):
    """본인확인(아이디+이름+이메일) 후 바로 새 비밀번호로 바꾼다 — 이메일 인증
    링크 없이 처리한다(내부 소규모 시스템이라 관리자 승인 계정 전제, 사내
    도구 수준의 보안으로 충분하다고 판단 — 필요시 추후 이메일 인증으로 강화 가능)."""

    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    new_password: str = Field(min_length=12, max_length=128)