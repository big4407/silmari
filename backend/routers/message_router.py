from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.schemas.message_schema import (
    MessageCollectResponse,
    MessageCreate,
    MessageResponse,
    MessageListResponse,
)
from backend.services.message_service import MessageService


# Service 객체를 Depends로 주입하기 위해 생성한 함수
def get_message_service(db: Session = Depends(get_db)) -> MessageService:
    """
    DB 세션을 받아 MessageService 인스턴스를 생성합니다.
    """
    return MessageService(db)


router = APIRouter(
    prefix="/messages",
    tags=["Messages"],
)


@router.post(
    "/collect",
    response_model=MessageCollectResponse,
)
async def collect_messages(
    page_no: int = Query(default=1, ge=1),
    num_of_rows: int = Query(default=10, ge=1, le=100),
    crt_dt: str | None = Query(default=None, description="조회시작일자 YYYYMMDD"),
    rgn_nm: str | None = Query(default=None, description="지역명"),
    service: MessageService = Depends(get_message_service),
):
    return await service.collect_messages(
        page_no=page_no,
        num_of_rows=num_of_rows,
        crt_dt=crt_dt,
        rgn_nm=rgn_nm,
    )


@router.post(
    "/manual_input",
    status_code=201,
    summary="문자 수동 등록, crt_dt(생성일시), reg_ymd(등록일자), mdfcn_ymd(수정일자)는 지정하지 않을 시 기본값, sn은 중복될시 오류 발생",
)
def manual_input(
    message_data: MessageCreate,
    service: MessageService = Depends(get_message_service),
):
    return service.manual_input_message(message_data=message_data)


@router.get("/{sn}", response_model=MessageResponse, summary="문자 단건 조회")
def get_message(
    sn: str = Path(..., min_length=1, max_length=22),
    service: MessageService = Depends(get_message_service),
):
    return service.get_message(sn)


@router.get("", response_model=MessageListResponse, summary="문자 전체 조회")
def get_list(
    page: int = Query(1, ge=1, description="페이지번호"),
    per_page: int = Query(10, ge=1, le=100, description="페이지당 항목 수"),
    search: str | None = Query(None, description="검색어"),
    order_by: str = Query("latest", description="정렬 기준 (기본값 : latest)"),
    service: MessageService = Depends(get_message_service),
):
    return service.get_message_list(page, per_page, search, order_by)
