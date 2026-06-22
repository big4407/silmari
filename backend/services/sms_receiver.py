from sqlalchemy.orm import Session

from backend.clients.disaster_message_client import DisasterMessageClient
from backend.models.message_model import Message
from backend.repositories.message_repository import MessageRepository
from backend.utils.datetime_parser import parse_date, parse_datetime
from backend.utils.message_filter import is_missing_person_message

# api로부터 메시지를 받아오는 서비스단
class MessageService:
    def __init__(self, db: Session):
        self.db = db
        self.client = DisasterMessageClient()
        self.repository = MessageRepository(db)

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
