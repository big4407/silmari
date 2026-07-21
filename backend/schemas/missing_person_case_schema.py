"""
실종자 관리 케이스(MissingPersonCase) API 스키마.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MissingPersonCaseItem(BaseModel):
    id: int
    sn: str
    missing_name: str | None
    gender: str | None
    age: int | None
    clothing: str | None
    missing_location: str | None
    missing_time: datetime | None
    msg_cn: str | None
    status: str
    assigned_investigator_id: str | None
    assigned_investigator_name: str | None = None
    assigned_at: datetime | None
    resolved_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MissingPersonCaseListResponse(BaseModel):
    items: list[MissingPersonCaseItem]
    total: int
    page: int
    per_page: int


class MissingPersonCaseManualCreate(BaseModel):
    """챗봇 상담 등 안내문자에 안 묶인 케이스를 수동으로 등록할 때 쓴다.

    sn은 서버가 자동으로 "C"+6자리 증가값을 채운다(요청에서 안 받음).
    """

    missing_name: str | None = Field(default=None, max_length=20)
    gender: str | None = None
    age: int | None = Field(default=None, ge=0, le=150)
    clothing: str | None = Field(default=None, max_length=100)
    missing_location: str | None = Field(default=None, max_length=20)
    missing_time: datetime | None = None
    notes: str | None = None


class MissingPersonCaseNotesUpdate(BaseModel):
    notes: str | None = None