"""
LLM 사용량 체크를 위한 라우터단
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.schemas.llm_call_schema import (
    CallCreate,
    CallUpdate,
    CallResponse,
    CallSearchParams,
)
from backend.services.llm_call_service import LlmCallService


def get_llm_service(db: Session = Depends(get_db)) -> LlmCallService:
    """
    DB 세션을 받아 LlmCallService 인스턴스를 생성합니다.
    """
    return LlmCallService(db)


router = APIRouter()


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
    response_model=dict,
)
def get_llm_calls(
    call_type: str | None = Query(default=None, max_length=100),
    search_id: int | None = Query(default=None),
    user_id: str | None = Query(default=None, max_length=36),
    conversation_id: int | None = Query(default=None),
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
        conversation_id=conversation_id,
        model_name=model_name,
        status=status_value,
        start_date=start_date,
        end_date=end_date,
        page=page,
        size=size,
        order_by=order_by,
    )

    items, total = service.get_calls(params)

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
    }


@router.get(
    "/{llm_call_id}",
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