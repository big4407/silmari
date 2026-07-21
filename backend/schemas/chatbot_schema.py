from pydantic import BaseModel


class ChatbotRequest(BaseModel):
    session_id: str
    message: str


class CasePrefill(BaseModel):
    """챗봇이 대화 중 모은 정보 — "케이스 추가하기" 선택 시 등록 폼에 미리 채운다."""

    missing_name: str | None = None
    gender: str | None = None
    age: int | None = None
    clothing: str | None = None
    missing_location: str | None = None


class ChatbotResponse(BaseModel):
    response: str
    session_id: str | None
    search_id: int | None = None
    search_inserted: bool = False
    offer_case_registration: bool = False
    case_prefill: CasePrefill | None = None