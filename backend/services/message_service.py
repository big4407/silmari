from sqlalchemy.orm import Session

from backend.services.disaster_message_client import DisasterMessageClient
from backend.db.models import Message
from backend.repositories.message_repository import MessageRepository
from backend.schemas.message_schema import (
    MessageCreate,
    MessageResponse,
    MessageListResponse,
)
from backend.utils.datetime_parser import parse_date, parse_datetime
from backend.utils.message_filter import is_missing_person_message

from fastapi import HTTPException
from datetime import date


# api로부터 메시지를 받아오거나, 수동으로 입력하는 서비스단
class MessageService:
    def __init__(self, db: Session):
        self.db = db
        self.client = DisasterMessageClient()
        self.repository = MessageRepository(db)

    def _get_or_404(self, sn: str):
        """
        문자를 sn으로 조회하고 없으면 404 예외를 발생시킵니다.
        """
        message = self.repository.find_by_sn(sn)
        if not message:
            raise HTTPException(status_code=404, detail="문자를 찾을 수 없습니다.")

        return message

    async def collect_messages(
        self,
        page_no: int = 1,
        num_of_rows: int = 10,
        crt_dt: str | None = None,
        rgn_nm: str | None = None,
    ) -> dict:
        items = await self.client.fetch_messages(
            page_no=page_no,
            num_of_rows=num_of_rows,
            crt_dt=crt_dt,
            rgn_nm=rgn_nm,
        )

        fetched_count = len(items)
        filtered_out_count = 0
        saved_count = 0
        skipped_duplicate_count = 0

        try:
            for item in items:
                msg_cn = item.get("MSG_CN", "")
                dst_se_nm = item.get("DST_SE_NM")

                if not is_missing_person_message(
                    msg_cn=msg_cn,
                    dst_se_nm=dst_se_nm,
                ):
                    filtered_out_count += 1
                    continue

                sn = str(item["SN"])

                if self.repository.find_by_sn(sn):
                    skipped_duplicate_count += 1
                    continue

                message = Message(
                    sn=sn,
                    crt_dt=parse_datetime(item.get("CRT_DT")),
                    msg_cn=msg_cn,
                    rcptn_rgn_nm=item.get("RCPTN_RGN_NM"),
                    emrg_step_nm=item.get("EMRG_STEP_NM"),
                    dst_se_nm=dst_se_nm,
                    reg_ymd=parse_date(item.get("REG_YMD")),
                    mdfcn_ymd=parse_date(item.get("MDFCN_YMD")),
                )

                self.repository.save(message)
                saved_count += 1

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return {
            "fetched_count": fetched_count,
            "filtered_out_count": filtered_out_count,
            "saved_count": saved_count,
            "skipped_duplicate_count": skipped_duplicate_count,
        }

    def manual_input_message(self, message_data: MessageCreate) -> MessageResponse:
        """
        수동으로 문자를 입력하는 서비스 함수
        """
        message = self.repository.insert(
            sn=message_data.sn,
            crt_dt=message_data.crt_dt,
            msg_cn=message_data.msg_cn,
            rcptn_rgn_nm=message_data.rcptn_rgn_nm,
            emrg_step_nm=message_data.emrg_step_nm,
            dst_se_nm=message_data.dst_se_nm,
            reg_ymd=message_data.reg_ymd,
            mdfcn_ymd=message_data.mdfcn_ymd,
        )

        return MessageResponse.model_validate(message)

    def get_message(self, sn: str) -> MessageResponse:
        message = self._get_or_404(sn)
        return MessageResponse.model_validate(message)

    # services/message_service.py

    def get_message_list(
        self,
        page: int,
        per_page: int,
        search_content: str | None,
        start_date: date | None = None,
        end_date: date | None = None,
        region: str | None = None,
        order_by: str = "latest",
    ) -> MessageListResponse:

        messages, total = self.repository.find_all(
            page=page,
            per_page=per_page,
            search_content=search_content,
            start_date=start_date,
            end_date=end_date,
            region=region,
            order_by=order_by,
        )

        return MessageListResponse(
            items=[MessageResponse.model_validate(message) for message in messages],
            total=total,
            page=page,
            size=per_page,
        )

    def delete_message(self, sn: str) -> None:
        """
        sn을 받아서 메시지를 삭제하는 함수
        """
        message = self._get_or_404(sn)
        self.repository.delete(message)
