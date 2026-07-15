"""재난문자(Message) API 요청/응답 Pydantic 스키마."""
from datetime import date, datetime

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    sn: str = Field(max_length=22)
    crt_dt: datetime = datetime.now()
    msg_cn: str
    rcptn_rgn_nm: str | None = None
    emrg_step_nm: str | None = Field(default=None, max_length=100)
    dst_se_nm: str | None = Field(default=None, max_length=100)
    reg_ymd: date | None = date.today()
    mdfcn_ymd: date | None = date.today()

    model_config = {
        "json_schema_extra": {
            "example": {
                "sn": "000001",
                "msg_cn": "메시지 내용",
                "rcptn_rgn_nm": "",
                "emrg_step_nm": "",
                "dst_se_nm": "",
            }
        }
    }


class MessageUpdate(BaseModel):
    crt_dt: datetime | None = None
    msg_cn: str | None = None
    rcptn_rgn_nm: str | None = None
    emrg_step_nm: str | None = Field(default=None, max_length=100)
    dst_se_nm: str | None = Field(default=None, max_length=100)
    reg_ymd: date | None = None
    mdfcn_ymd: date | None = None


class MessageResponse(BaseModel):
    sn: str
    crt_dt: datetime
    msg_cn: str
    rcptn_rgn_nm: str | None
    emrg_step_nm: str | None
    dst_se_nm: str | None
    reg_ymd: date | None
    mdfcn_ymd: date | None

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int
    page: int
    size: int


class MessageCollectResponse(BaseModel):
    fetched_count: int
    filtered_out_count: int
    saved_count: int
    skipped_duplicate_count: int


class AlertParseRequest(BaseModel):
    msg_cn: str = Field(description="안내문자 본문 원문")


class AlertParseResponse(BaseModel):
    """LLM이 안내문자 본문에서 뽑아낸 실종자 정보 — 검색 요청(SearchCreate)에
    그대로 흘려넣을 수 있는 필드만 담는다."""

    missing_name: str | None = None
    gender: str | None = None
    age: int | None = None
    clothing: str | None = None