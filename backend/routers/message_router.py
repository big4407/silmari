from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.schemas.message_schema import MessageCollectResponse
from backend.services.sms_receiver import MessageService


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
    db: Session = Depends(get_db),
):
    service = MessageService(db)

    return await service.collect_messages(
        page_no=page_no,
        num_of_rows=num_of_rows,
        crt_dt=crt_dt,
        rgn_nm=rgn_nm,
    )
