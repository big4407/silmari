from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.schemas.message_schema import (
    MessageCollectResponse,
    MessageCreate,
)
from backend.services.sms_receiver import MessageService


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


@router.post("/manual_input", status_code=201, summary="문자 수동 등록")
def manual_input(
    message_data: MessageCreate,
    service: MessageService = Depends(get_message_service),
):
    return service.manual_input_message(message_data=message_data)
