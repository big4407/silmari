from pydantic import BaseModel, Field
from typing import Literal


class ExtractedSearchSlots(BaseModel):
    """extract_slots_node 에서 LLM 구조화 출력으로만 쓰는 내부 스키마.

    HTTP 요청/응답 스키마(ChatbotRequest/ChatbotResponse)는
    backend/schemas/chatbot_schema.py 에 있다.
    """

    region: str | None = Field(None, description="실종 발생 또는 목격 지역")
    start_date: str | None = Field(None, description="검색 시작일")
    end_date: str | None = Field(None, description="검색 종료일")
    appearance: str | None = Field(None, description="인상착의")

    missing_name: str | None = Field(None, description="실종자 이름")
    gender: Literal["M", "F"] | None = Field(
        None, description="성별. 남성은 M, 여성은 F, 알 수 없으면 null"
    )
    age: int | None = Field(None, description="실종자의 나이")
