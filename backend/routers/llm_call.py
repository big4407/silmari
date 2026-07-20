"""
LLM 사용량 체크를 위한 라우터단
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import LlmCallType
from backend.schemas.llm_call_schema import (
    CallCreate,
    CallUpdate,
    CallResponse,
    CallSearchParams,
    CallListResponse,
    LlmCallGroupListResponse,
    LlmCallAdminSearchParams,
    LlmUsageSummary,
    MessageLlmCallDetail,
    ChatbotLlmCallDetail,
)
from backend.services.llm_call_service import LlmCallService


def get_llm_service(db: Session = Depends(get_db)) -> LlmCallService:
    """
    DB 세션을 받아 LlmCallService 인스턴스를 생성합니다.
    """
    return LlmCallService(db)


router = APIRouter()


@router.get("/summary", response_model=LlmUsageSummary)
def get_llm_usage_summary(
    service: LlmCallService = Depends(get_llm_service),
):
    """LLM 사용량 화면 상단 통계 카드 — 오늘 총 호출 + 유형별 전체 누적."""
    return service.get_usage_summary()


@router.post(
    "",
    response_model=CallResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_llm_call(
    payload: CallCreate,
    service: LlmCallService = Depends(get_llm_service),
):
    """
    LLM 호출 기록 생성
    """
    return service.input_call(payload)


@router.get(
    "",
    response_model=CallListResponse,
)
def get_llm_calls(
    call_type: LlmCallType | None = Query(
        default=None,
        description="1: 인상착의 한영변환, 2: 챗봇, 3: 안내문자 파싱, 미입력: 전체",
    ),
    search_id: int | None = Query(default=None),
    user_id: str | None = Query(default=None, max_length=36),
    chatbot_s_id: str | None = Query(default=None, max_length=36),
    model_name: str | None = Query(default=None, max_length=100),
    status_value: str | None = Query(default=None, alias="status", max_length=10),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    order_by: str = Query(default="latest"),
    service: LlmCallService = Depends(get_llm_service),
):
    """
    LLM 호출 기록 목록 조회
    """
    params = CallSearchParams(
        call_type=call_type,
        search_id=search_id,
        user_id=user_id,
        chatbot_s_id=chatbot_s_id,
        model_name=model_name,
        status=status_value,
        start_date=start_date,
        end_date=end_date,
        page=page,
        size=size,
        order_by=order_by,
    )

    items, total = service.get_calls(params)

    return CallListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
    )


@router.get(
    "/detail/{llm_call_id}",
    response_model=CallResponse,
)
def get_llm_call(
    llm_call_id: int = Path(..., ge=1),
    service: LlmCallService = Depends(get_llm_service),
):
    """
    LLM 호출 기록 단건 조회
    """
    return service.get_call(llm_call_id)


@router.patch(
    "/{llm_call_id}",
    response_model=CallResponse,
)
def update_llm_call(
    payload: CallUpdate,
    llm_call_id: int = Path(..., ge=1),
    service: LlmCallService = Depends(get_llm_service),
):
    """
    LLM 호출 기록 수정
    """
    return service.update_call(llm_call_id, payload)


@router.delete(
    "/{llm_call_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_llm_call(
    llm_call_id: int = Path(..., ge=1),
    service: LlmCallService = Depends(get_llm_service),
):
    """
    LLM 호출 기록 삭제
    """
    service.delete_call(llm_call_id)
    return None


@router.get(
    "/admin",
    response_model=LlmCallGroupListResponse,
    status_code=status.HTTP_200_OK,
)
def get_admin_llm_calls(
    call_type: LlmCallType | None = Query(
        default=None,
        description="1: 인상착의 한영변환, 2: 챗봇, 3: 안내문자 파싱",
    ),
    search_id: int | None = Query(default=None),
    user_id: str | None = Query(default=None, max_length=36),
    model_name: str | None = Query(default=None, max_length=100),
    status_value: str | None = Query(
        default=None,
        alias="status",
        pattern="^[01]$",
    ),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    order_by: str = Query(
        default="latest",
        pattern="^(latest|oldest)$",
    ),
    service: LlmCallService = Depends(get_llm_service),
):
    """
    관리자용 LLM 호출 목록 조회.

    - call_type=1: LLM 호출 한 건당 한 행
    - call_type=2: chatbot_s_id 단위로 집계하여 한 행
    - call_type=3(안내문자 파싱)은 아직 이 그룹 조회에 포함되지 않음(TODO) —
      call_type을 지정 안 하면 1·2만 합쳐서 보여준다.
    """
    params = LlmCallAdminSearchParams(
        call_type=call_type,
        search_id=search_id,
        user_id=user_id,
        model_name=model_name,
        status=status_value,
        start_date=start_date,
        end_date=end_date,
        page=page,
        size=size,
        order_by=order_by,
    )

    return service.get_admin_list(params)


@router.get(
    "/admin/message/{llm_call_id}",
    response_model=MessageLlmCallDetail,
    status_code=status.HTTP_200_OK,
)
def get_message_llm_call_detail(
    llm_call_id: int,
    service: LlmCallService = Depends(get_llm_service),
):
    """
    안내문자 LLM 호출 상세 조회.
    """
    return service.get_message_call_detail(llm_call_id)


@router.get(
    "/admin/chatbot/{chatbot_s_id}",
    response_model=ChatbotLlmCallDetail,
    status_code=status.HTTP_200_OK,
)
def get_chatbot_llm_call_detail(
    chatbot_s_id: str,
    service: LlmCallService = Depends(get_llm_service),
):
    """
    챗봇 세션 단위 LLM 호출 상세 조회.
    """
    return service.get_chatbot_call_detail(chatbot_s_id)