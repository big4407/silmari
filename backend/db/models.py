"""
ORM 모델 정의 — MySQL 테이블과 1:1 매핑.

[탐지] DetectionRecord(레거시), SearchResult(CCTV 분석 결과·클립 메타)
[인증] User, AuthSession — 승인 기반 RBAC + JWT 세션 철회
[외부] Message — 재난안전데이터 API 수집 재난문자
"""
# db/models.py
from sqlalchemy import (
    Column,
    Date,
    Integer,
    String,
    DateTime,
    Text,
    Float,
    Enum,
    ForeignKey,
    func,
    CHAR,
    JSON,
)
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

class ChatbotSession(Base):
    __tablename__ = "chatbot_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    session_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    state_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

# ──────────────────────────────────────────────────────────────────────────
# 설계서(테이블 명세) 기준 모델
# region / video / video_detail / search / analysis / analysis_detail
# (User · Message 등 위 모델과 같은 Base 를 공유)
# ──────────────────────────────────────────────────────────────────────────

class Region(Base):
    """지역명과 지역코드(행정동코드). parent_code 로 계층(self-FK)."""
    __tablename__ = "region"

    region_code: Mapped[str] = mapped_column(
        String(10), primary_key=True, comment="지역코드(행정동코드)"
    )
    full_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="지역명 전체(ex. 서울시 강남구 역삼동)"
    )
    specific_name: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="최하위 지역명(ex. 역삼동)"
    )
    parent_code: Mapped[str | None] = mapped_column(
        ForeignKey("region.region_code"), nullable=True, comment="상위 지역코드(self-FK)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="입력일시"
    )

    parent: Mapped["Region | None"] = relationship(
        remote_side=[region_code], foreign_keys=[parent_code]
    )


class Video(Base):
    """전체 영상에 대한 정보. embedding_id 로 Chroma 벡터와 매핑."""
    __tablename__ = "video"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cctv_serial_no: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="CCTV 일련번호"
    )
    file_path: Mapped[str] = mapped_column(
        String(260), nullable=False, comment="영상 파일의 경로"
    )
    region_code: Mapped[str | None] = mapped_column(
        ForeignKey("region.region_code"), nullable=True, comment="지역코드(region의 PK)"
    )
    recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="영상이 녹화된 일시"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="입력일시"
    )
    embedding_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Chroma DB 내 매핑할 ID (embedding, metadata 세트)"
    )

    region: Mapped["Region | None"] = relationship()
    details: Mapped[list["VideoDetail"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )


class VideoDetail(Base):
    """영상 상세정보 — 영상 내 인물 출현 구간(인덱싱 결과)."""
    __tablename__ = "video_detail"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("video.id"), nullable=False, comment="video 테이블 pk"
    )
    video_timestamp: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="영상 내 사람 출현 시간(초, ex 8:10 -> 490)"
    )
    crop_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="한 화면에 여러 사람일 때 구분 ID"
    )
    position: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="bbox (x,y,width,height)"
    )

    video: Mapped["Video"] = relationship(back_populates="details")


class Search(Base):
    """요청한 검색 내용. search_type 으로 출처 구분(1 SMS / 2 챗봇 / 3 자동)."""
    __tablename__ = "search"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False, comment="검색 요청한 유저 id (user의 PK)"
    )
    message_sn: Mapped[str | None] = mapped_column(
        ForeignKey("message.sn"), nullable=True, comment="지정 안내문자 id (message의 PK)"
    )
    missing_name: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="이름"
    )
    gender: Mapped[str | None] = mapped_column(
        CHAR(1), nullable=True, comment="성별 (M:남성, F:여성)"
    )
    age: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="나이")
    clothing: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="인상착의(모자, 상의, 하의, 신발, 기타)"
    )
    missing_location: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="실종지역(추후 region_code로 변경 가능)"
    )
    missing_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="실종시각"
    )
    searched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="검색한 일시"
    )
    search_type: Mapped[str] = mapped_column(
        CHAR(1), nullable=False, default="1",
        comment="1:SMS 파싱, 2:챗봇, 3:자동검색",
    )

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    message: Mapped["Message | None"] = relationship()
    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="search", cascade="all, delete-orphan"
    )


class Analysis(Base):
    """검색 요청에 대한 분석(실행) 상태."""
    __tablename__ = "analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False, comment="user 테이블 pk"
    )
    search_id: Mapped[int] = mapped_column(
        ForeignKey("search.id"), nullable=False, comment="search 테이블 pk"
    )
    analysis_status: Mapped[str] = mapped_column(
        CHAR(1), nullable=False, default="0",
        comment="0:분석 전, 1:부분분석완료, 2:완료",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="결과도출 시간"
    )

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    search: Mapped["Search"] = relationship(back_populates="analyses")
    details: Mapped[list["AnalysisDetail"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class AnalysisDetail(Base):
    """분석 결과 상세 — 매칭된 인물 후보(crop) 단위."""
    __tablename__ = "analysis_detail"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("analysis.id"), nullable=False, comment="analysis 테이블 pk"
    )
    video_id: Mapped[int] = mapped_column(
        ForeignKey("video.id"), nullable=False, comment="video 테이블 pk"
    )
    video_timestamp: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="영상 내 실종자 출현 시간(초)"
    )
    crop_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="한 화면에 여러 사람일 때 구분 ID"
    )
    position: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="bbox (x,y,width,height)"
    )
    matching_rate: Mapped[float] = mapped_column(
        Float, nullable=False, default=0, comment="매칭 정확도"
    )

    analysis: Mapped["Analysis"] = relationship(back_populates="details")
    video: Mapped["Video"] = relationship()