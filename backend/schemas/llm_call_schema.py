"""
llm 사용량 체크 llm_call 테이블에 사용하는 Pydantic 스키마
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.db.models import LlmCallType


class CallCreate(BaseModel):
    call_type: LlmCallType

    search_id: int | None = None
    user_id: str | None = Field(default=None, max_length=36)
    chatbot_s_id: str | None = None

    model_name: str = Field(max_length=100)

    prompt: str
    response: str | None = None

    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    cost: float | None = None

    status: str = Field(max_length=10)
    error_msg: str | None = Field(default=None, max_length=255)


class CallUpdate(BaseModel):
    call_type: LlmCallType | None = None

    search_id: int | None = None
    user_id: str | None = Field(default=None, max_length=36)
    chatbot_s_id: str | None = None

    model_name: str | None = Field(default=None, max_length=100)

    prompt: str | None = None
    response: str | None = None

    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    cost: float | None = None

    status: str | None = Field(default=None, max_length=10)
    error_msg: str | None = Field(default=None, max_length=255)


class CallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int

    call_type: LlmCallType

    search_id: int | None
    user_id: str | None
    chatbot_s_id: str | None

    model_name: str

    prompt: str
    response: str | None

    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    cost: float | None

    status: str
    error_msg: str | None

    created_at: datetime


class CallSearchParams(BaseModel):
    call_type: LlmCallType | None = None

    search_id: int | None = None
    user_id: str | None = Field(default=None, max_length=36)
    chatbot_s_id: str | None = None

    model_name: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, max_length=10)

    start_date: datetime | None = None
    end_date: datetime | None = None

    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

    order_by: str = Field(default="latest")


class CallListResponse(BaseModel):
    items: list[CallResponse]
    total: int
    page: int
    size: int


class LlmCallGroupItem(BaseModel):
    call_type: LlmCallType
    row_key:str
    model:str | None = None

    chatbot_s_id: str | None = None
    llm_call_id: int | None = None

    user_id: str | None = None
    username: str | None = None
    search_id: int | None = None

    call_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float | None = None

    total_latency_ms: int
    avg_latency_ms: float

    first_called_at: datetime
    last_called_at: datetime


class MessageLlmCallDetail(BaseModel):
    llm_call: CallResponse
    search_id: int | None = None


class ChatbotLlmCallDetail(BaseModel):
    chatbot_s_id: str
    session_id: str
    user_id: str | None
    search_id: int | None = None

    call_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    success_count: int
    failure_count: int
    success_rate: float
    avg_latency_ms: float

    calls: list[CallResponse]


class LlmCallGroupListResponse(BaseModel):
    items: list[LlmCallGroupItem]
    page: int
    size: int
    total: int
    total_pages: int


class LlmCallAdminSearchParams(BaseModel):
    call_type: LlmCallType | None = None

    search_id: int | None = None
    user_id: str | None = None
    model_name: str | None = None
    status: str | None = None

    start_date: datetime | None = None
    end_date: datetime | None = None

    page: int = 1
    size: int = 20
    order_by: str = "latest"