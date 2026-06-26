from sqlalchemy.orm import Session

from backend.db.models import Message

from datetime import datetime, date
from sqlalchemy import desc, asc

class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_sn(self, sn: str) -> Message | None:
        return self.db.query(Message).filter(Message.sn == sn).first()

    def save(self, message: Message) -> Message:
        self.db.add(message)
        self.db.flush()
        return message
    # 수동 input을 위한 함수
    def insert(
        self,
        sn: str,
        crt_dt: datetime,
        msg_cn: str,
        rcptn_rgn_nm: str,
        emrg_step_nm: str,
        dst_se_nm: str,
        reg_ymd: date,
        mdfcn_ymd: date,
    ) -> Message:
        message = Message(
            sn=sn,
            crt_dt=crt_dt,
            msg_cn=msg_cn,
            rcptn_rgn_nm=rcptn_rgn_nm,
            emrg_step_nm=emrg_step_nm,
            dst_se_nm=dst_se_nm,
            reg_ymd=reg_ymd,
            mdfcn_ymd=mdfcn_ymd,
        )
        self.db.add(message)  # 실제 insert 쿼리문 실행
        self.db.commit()  # 데이터베이스에 영구 반영
        self.db.refresh(message)  # id가 존재하는 Post 객체
        return message

    def find_all(
        self,
        page: int,
        per_page: int,
        search: str | None = None,
        order_by: str = "latest",
    ) -> tuple[list[Message], int]:
        query = self.db.query(Message)

        if search:
            query = query.filter(
                Message.msg_cn.like(f"%{search}%")
            )

        total = query.count()

        if order_by == "oldest":
            query = query.order_by(asc(Message.crt_dt))
        else:
            query = query.order_by(desc(Message.crt_dt))

        messages = (
            query
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return messages, total