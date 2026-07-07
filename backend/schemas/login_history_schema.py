"""로그인 이력(감사 로그) 응답 스키마."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.db.models import LoginFailStatus


class LoginHistoryItem(BaseModel):
    """로그인 시도 1건."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None
    username: str
    full_name: str | None = None  # 조인으로 채움 (없는 계정 시도면 None)
    success: bool
    fail_reason: LoginFailStatus | None  # 코드값("1"~"5"), 프론트에서 라벨 변환
    ip_address: str | None
    user_agent: str | None
    created_at: datetime


class LoginHistoryListResponse(BaseModel):
    """로그인 이력 목록 + 페이지네이션 + 요약 통계."""

    items: list[LoginHistoryItem]
    total: int
    page: int
    size: int
    # 요약 (오늘 기준)
    today_success: int
    today_failed: int
