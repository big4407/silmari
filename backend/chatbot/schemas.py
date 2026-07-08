from pydantic import BaseModel, Field


class ChatbotRequest(BaseModel):
    session_id: str
    message: str


class ChatbotResponse(BaseModel):
    response: str
    session_id: str | None


class ExtractedSearchSlots(BaseModel):
    region: str | None = Field(None, description="실종 발생 또는 목격 지역")
    start_date: str | None = Field(None, description="검색 시작일")
    end_date: str | None = Field(None, description="검색 종료일")
    appearance: str | None = Field(None, description="인상착의")

    missing_name: str | None = None
    gender: str | None = None
    age: int | None = None
