# db/models.py
from sqlalchemy import Column, Date, Integer, String, DateTime, Text, Float, Enum, ForeignKey, func, CHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date, datetime
import enum
import uuid

from backend.db.database import Base   # ← 단일 Base 사용

class DetectionRecord(Base):
    __tablename__ = "detection_records"

    id = Column(Integer, primary_key=True, index=True)
    alert_text = Column(Text)
    video_filename = Column(String(255))
    result_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class SearchResult(Base):
    __tablename__ = "search_results"

    id = Column(Integer, primary_key=True, index=True)
    alert_text = Column(Text)
    person_name = Column(String(100), index=True)
    person_age = Column(Integer, nullable=True)
    region = Column(String(100), nullable=True)
    video_filename = Column(String(255))
    thumbnail_filename = Column(String(255))
    best_confidence = Column(Float)
    best_timestamp_sec = Column(Float)
    clips_json = Column(Text)
    sms_info_json = Column(Text)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserRole(str, enum.Enum):
    INVESTIGATOR = "investigator"
    PUBLIC_OFFICIAL = "public_official"
    ADMIN = "admin"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    organization: Mapped[str] = mapped_column(String(150), nullable=False)
    department: Mapped[str | None] = mapped_column(String(150), nullable=True)
    position: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)

    requested_role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False), nullable=False, default=UserRole.INVESTIGATOR
    )
    role: Mapped[UserRole | None] = mapped_column(Enum(UserRole, native_enum=False), nullable=True)
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, native_enum=False), nullable=False, default=ApprovalStatus.PENDING, index=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    approved_by: Mapped["User | None"] = relationship(remote_side=[id], foreign_keys=[approved_by_id])
    sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="sessions")

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

class Search(Base):
    __tablename__ = "search"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("users.id"),
        nullable=False,
    )

    message_sn: Mapped[str | None] = mapped_column(
        String(22),
        ForeignKey("message.sn"),
        nullable=True,
    )

    missing_name: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gender: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)

    clothing: Mapped[str | None] = mapped_column(String(100), nullable=True)
    missing_location: Mapped[str | None] = mapped_column(String(20), nullable=True)
    missing_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    searched_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    search_type: Mapped[str] = mapped_column(
        CHAR(1),
        nullable=False,
        server_default="1",
    )