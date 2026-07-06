"""관리자 행동 이력(감사 로그) 응답 스키마."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.db.models import AdminAction


class AdminHistoryItem(BaseModel):
    """관리자 행동 1건."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_id: str
    actor_name: str | None = None  # 조인으로 채움 (행위자 이름)
    action_type: AdminAction  # 코드값("1"~"6"), 프론트에서 라벨 변환
    target_type: str
    target_id: str | None
    detail: dict | None  # {before, after, reason, target_name ...}
    batch_id: str | None
    success: bool
    ip_address: str | None
    created_at: datetime


class AdminHistoryListResponse(BaseModel):
    """관리자 행동 이력 목록 + 페이지네이션."""

    items: list[AdminHistoryItem]
    total: int
    page: int
    size: int
