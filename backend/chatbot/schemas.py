from typing import Any
from pydantic import BaseModel, Field


class ChatbotRequest(BaseModel):
    user_id: str
    message: str
    state: dict[str, Any] | None = None


class ChatbotResponse(BaseModel):
    response: str
    state: dict[str, Any]


class ExtractedSearchSlots(BaseModel):
    region: str | None = Field(None, description="실종 발생 또는 목격 지역")
    start_time: str | None = Field(None, description="검색 시작 시간")
    end_time: str | None = Field(None, description="검색 종료 시간")
    appearance: str | None = Field(None, description="인상착의")

    missing_name: str | None = None
    gender: str | None = None
    age: int | None = None
