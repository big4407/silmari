"""
재난문자 수집·조회 API.

POST /messages/collect — 외부 API에서 재난문자 수집 후 DB 저장
GET  /messages         — 저장된 메시지 목록 (실종 필터 등)
"""
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

from datetime import date


# Service 객체를 Depends로 주입하기 위해 생성한 함수
def get_message_service(db: Session = Depends(get_db)) -> MessageService:
    """
    DB 세션을 받아 MessageService 인스턴스를 생성합니다.
    """
    return MessageService(db)


router = APIRouter()

TAG_MESSAGES = ["Messages"]


@router.post(
    "/collect",
    response_model=MessageCollectResponse,
    summary="재난문자 수집",
    description=(
        "행정안전부 재난문자 API에서 데이터를 가져와 실종 관련 문자만 필터링한 뒤 "
        "`message` 테이블에 저장합니다. "
        "연결: `MessageService.collect_messages` → `DisasterMessageClient` → DB `Message`"
    ),
    tags=TAG_MESSAGES,
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
    summary="재난문자 수동 등록",
    description="테스트·보완용으로 `message` 테이블에 문자를 직접 등록합니다. `sn` 중복 시 오류.",
    tags=TAG_MESSAGES,
    include_in_schema=False,
)
def manual_input(
    message_data: MessageCreate,
    service: MessageService = Depends(get_message_service),
):
    return service.manual_input_message(message_data=message_data)


@router.get(
    "",
    response_model=MessageListResponse,
    summary="재난문자 목록 조회",
    description=(
        "DB `message` 테이블에서 저장된 재난문자를 페이지네이션·기간·지역·검색어로 조회합니다. "
        "대시보드(`Dashboard.jsx`)가 이 API를 사용합니다. "
        "연결: `MessageService.get_message_list` → `MessageRepository.find_all`"
    ),
    tags=TAG_MESSAGES,
)
def get_list(
    page: int = Query(1, ge=1, description="페이지번호"),
    per_page: int = Query(10, ge=1, le=100, description="페이지당 항목 수"),
    search_content: str | None = Query(None, description="검색어"),
    start_date: date | None = Query(None, description="시작일"),
    end_date: date | None = Query(None, description="종료일"),
    region: str | None = Query(None, description="지역"),
    order_by: str = Query("latest", description="정렬 기준 (기본값 : latest)"),
    service: MessageService = Depends(get_message_service),
):
    return service.get_message_list(
        page, per_page, search_content, start_date, end_date, region, order_by
    )


@router.get(
    "/{sn}",
    response_model=MessageResponse,
    summary="재난문자 단건 조회",
    description="일련번호(`sn`)로 `message` 테이블에서 문자 1건을 조회합니다.",
    tags=TAG_MESSAGES,
    include_in_schema=False,
)
def get_message(
    sn: str = Path(..., min_length=1, max_length=22),
    service: MessageService = Depends(get_message_service),
):
    return service.get_message(sn)


@router.delete(
    "/{sn}",
    status_code=204,
    summary="재난문자 삭제",
    description="일련번호(`sn`)로 `message` 테이블에서 문자 1건을 삭제합니다.",
    tags=TAG_MESSAGES,
    include_in_schema=False,
)
def delete_message(
    sn: str = Path(..., min_length=1, max_length=22),
    service: MessageService = Depends(get_message_service),
):
    return service.delete_message(sn)
