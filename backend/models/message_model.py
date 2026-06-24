from datetime import datetime, date

from sqlalchemy import DateTime, Text, String, Date
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.database import Base

# 재난문자 원문 그대로, 단 date/datetime의 경우 파싱
class Message(Base):
    __tablename__ = "message"

    sn: Mapped[str] = mapped_column(
        String(22), primary_key=True, comment="일련번호"
    )

    crt_dt: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="생성일시"
    )

    msg_cn: Mapped[str] = mapped_column(Text, nullable=False, comment="메시지내용")

    rcptn_rgn_nm: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="수신지역명"
    )

    emrg_step_nm: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="긴급단계명 (긴급재난, 안전안내, 위급재난)"
    )

    dst_se_nm: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="재해구분명"
    )

    reg_ymd: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="등록일자"
    )

    mdfcn_ymd: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="수정일자"
    )
