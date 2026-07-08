"""
llm 사용량 체크 llm_call 테이블에 사용하는 Pydantic 스키마
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CallCreate(BaseModel):
    call_type: str = Field(max_length=100)

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
    call_type: str | None = Field(default=None, max_length=100)

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

    call_type: str

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
    call_type: str | None = Field(default=None, max_length=100)

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
