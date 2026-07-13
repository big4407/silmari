"""
ORM 모델 정의 — MySQL 테이블과 1:1 매핑.

[인증] User, AuthSession — 승인 기반 RBAC + JWT 세션 철회
[외부] Message — 재난안전데이터 API 수집 재난문자
"""

# db/models.py
from sqlalchemy import (
    Date,
    Integer,
    Boolean,
    String,
    DateTime,
    Text,
    Float,
    Enum,
    ForeignKey,
    JSON,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date, datetime, timedelta
import enum
import uuid

from backend.db.database import Base  # ← 단일 Base 사용
from backend.utils.timeutils import kst_now


def _default_start_date() -> date:
    """검색 기본 시작일 — 오늘(KST) 기준 7일 전."""
    return (kst_now() - timedelta(days=7)).date()


def _default_end_date() -> date:
    """검색 기본 종료일 — 오늘(KST)."""
    return kst_now().date()


class UserRole(str, enum.Enum):
    """사용자 역할. value 는 DB 저장용 코드값."""

    ADMIN = "1"
    INVESTIGATOR = "2"
    PUBLIC_OFFICIAL = "3"


class ApprovalStatus(str, enum.Enum):
    """가입 승인 상태. value 는 DB 저장용 코드값."""

    PENDING = "0"
    APPROVED = "1"
    REJECTED = "2"
    SUSPENDED = "3"


class SearchType(str, enum.Enum):
    """검색 요청 출처. value 는 기존 CHAR(1) 코드값을 유지(DB 호환)."""

    SMS = "1"  # 안내문자(SMS) 파싱
    CHATBOT = "2"  # 챗봇
    AUTO = "3"  # 자동검색


class AnalysisStatus(str, enum.Enum):
    """분석(실행) 상태. value 는 기존 CHAR(1) 코드값을 유지(DB 호환)."""

    NOT_STARTED = "0"  # 분석 전
    PARTIAL = "1"  # 부분분석완료
    COMPLETED = "2"  # 완료


class Gender(str, enum.Enum):
    """성별. value 는 기존 CHAR(1) 코드값을 유지(DB 호환)."""

    MALE = "M"
    FEMALE = "F"


# 재난문자 원문 그대로, 단 date/datetime의 경우 파싱
class LoginFailStatus(str, enum.Enum):
    """로그인 실패 사유. value 는 DB 저장용 코드값(숫자).

    성공(success=True)이면 fail_reason 은 NULL. 실패 시에만 아래 코드 중 하나.
    """

    BAD_CREDENTIALS = "1"  # 아이디 없음 또는 비밀번호 불일치
    PENDING = "2"  # 승인 대기 중인 계정
    REJECTED = "3"  # 가입 반려된 계정
    SUSPENDED = "4"  # 정지된 계정
    NO_ROLE = "5"  # 역할이 부여되지 않은 계정


class AdminAction(str, enum.Enum):
    """관리자 행동 유형. value 는 DB 저장용 코드값(숫자)."""

    APPROVE = "1"  # 가입 승인
    REJECT = "2"  # 가입 반려
    SUSPEND = "3"  # 계정 정지
    REACTIVATE = "4"  # 정지·반려 해제(재승인)
    DELETE = "5"  # 데이터 삭제 (안내문자 등, 향후 확장)
    UPDATE = "6"  # 데이터 수정 (향후 확장)


class User(Base):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    organization: Mapped[str] = mapped_column(String(150), nullable=False)
    department: Mapped[str | None] = mapped_column(String(150), nullable=True)
    position: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)

    requested_role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole, native_enum=False, values_callable=lambda e: [m.value for m in e]
        ),
        nullable=False,
        default=UserRole.INVESTIGATOR,
    )
    role: Mapped[UserRole | None] = mapped_column(
        Enum(
            UserRole, native_enum=False, values_callable=lambda e: [m.value for m in e]
        ),
        nullable=True,
    )
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        Enum(
            ApprovalStatus,
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ApprovalStatus.PENDING,
        index=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("user.id"), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=kst_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=kst_now,
        onupdate=kst_now,
        nullable=False,
    )

    approved_by: Mapped["User | None"] = relationship(
        remote_side=[id], foreign_keys=[approved_by_id]
    )
    sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user.id"), index=True, nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=kst_now, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="sessions")


class LoginHistory(Base):
    """로그인 시도 이력 — 감사 로그. 성공·실패 모두 영구 기록."""

    __tablename__ = "login_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # 실패(없는 아이디)면 user_id 는 NULL, username 은 시도한 값을 항상 기록
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("user.id"), index=True, nullable=True
    )
    username: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    # 실패 사유 — 성공 시 NULL. 다른 enum 과 동일하게 숫자 코드로 저장(values_callable).
    fail_reason: Mapped[LoginFailStatus | None] = mapped_column(
        Enum(
            LoginFailStatus,
            native_enum=False,
            length=1,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=True,
    )
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=kst_now,
        nullable=False,
        index=True,
        comment="로그인 시도 일시",
    )


class AdminHistory(Base):
    """관리자 행동 이력 — 감사 로그. 승인·반려·정지·삭제 등 모든 관리 작업을 기록."""

    __tablename__ = "admin_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # 행동한 관리자 (user의 PK)
    actor_id: Mapped[str] = mapped_column(
        ForeignKey("user.id"), index=True, nullable=False
    )
    action_type: Mapped[AdminAction] = mapped_column(
        Enum(
            AdminAction,
            native_enum=False,
            length=1,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        index=True,
    )
    # 대상 종류: "user" / "message" 등
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # 대상 식별자 (user_id, message_sn 등)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 변경 내용 — JSON. 예: {"before": {"role": null}, "after": {"role": "2"}, "reason": "..."}
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 일괄 작업 묶음 ID (다중 대상 작업이면 같은 값). 단일 작업이면 NULL
    batch_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=kst_now, nullable=False, index=True, comment="행동 일시"
    )


class Message(Base):
    __tablename__ = "message"

    sn: Mapped[str] = mapped_column(String(22), primary_key=True, comment="일련번호")

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

    session_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, nullable=False
    )

    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    state_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=kst_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=kst_now,
        onupdate=kst_now,
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
        ForeignKey("region.region_code"),
        nullable=True,
        comment="상위 지역코드(self-FK)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=kst_now, nullable=False, comment="입력일시"
    )

    parent: Mapped["Region | None"] = relationship(
        remote_side=[region_code], foreign_keys=[parent_code]
    )
    legal_dongs: Mapped[list["RegionLegalDong"]] = relationship(
        back_populates="admin_region"
    )


class RegionLegalDong(Base):
    """행정동 ↔ 법정동 매핑 — administrative_dong.csv 기준."""

    __tablename__ = "region_legal_dong"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    legal_dong_code: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True, comment="법정동코드(10자리)"
    )
    admin_dong_code: Mapped[str] = mapped_column(
        ForeignKey("region.region_code"),
        nullable=False,
        index=True,
        comment="행정동코드(region.region_code)",
    )
    legal_dong_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="법정동명"
    )
    admin_area_code: Mapped[str | None] = mapped_column(
        String(10), nullable=True, comment="행정구역코드(CSV 행정구역코드)"
    )
    revised_at: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="개정일자"
    )
    link_no: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="연결번호(복수일 수 있음)"
    )

    admin_region: Mapped["Region"] = relationship(back_populates="legal_dongs")


class Video(Base):
    """전체 영상에 대한 정보. Chroma 벡터는 video.id 로 매핑."""

    __tablename__ = "video"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cctv_serial_no: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="CCTV 일련번호(Chroma DB 내 매핑할 ID)"
    )
    file_path: Mapped[str] = mapped_column(
        String(260), nullable=False, comment="영상 파일의 경로"
    )
    region_code: Mapped[str | None] = mapped_column(
        ForeignKey("region.region_code"), nullable=True, comment="지역코드(region의 PK)"
    )
    recorded_at: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="영상이 녹화된 날짜(파일명에 시각 없음)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=kst_now, nullable=False, comment="입력일시"
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
        ForeignKey("user.id"),
        nullable=False,
        comment="검색 요청한 유저 id (user의 PK)",
    )
    message_sn: Mapped[str | None] = mapped_column(
        ForeignKey("message.sn"),
        nullable=True,
        comment="지정 안내문자 id (message의 PK)",
    )
    missing_name: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="이름"
    )
    gender: Mapped[Gender | None] = mapped_column(
        Enum(
            Gender,
            native_enum=False,
            length=1,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=True,
        comment="성별 (M:남성, F:여성)",
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
        DateTime, default=kst_now, nullable=False, comment="검색한 일시"
    )
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=_default_start_date,
        comment="영상 검색 시작일자 (기본: 오늘 기준 7일 전)",
    )
    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=_default_end_date,
        comment="영상 검색 종료일자 (기본: 오늘)",
    )
    search_type: Mapped[SearchType] = mapped_column(
        Enum(
            SearchType,
            native_enum=False,
            length=1,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=SearchType.SMS,
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
        ForeignKey("user.id"), nullable=False, comment="user 테이블 pk"
    )
    search_id: Mapped[int] = mapped_column(
        ForeignKey("search.id"), nullable=False, comment="search 테이블 pk"
    )
    analysis_status: Mapped[AnalysisStatus] = mapped_column(
        Enum(
            AnalysisStatus,
            native_enum=False,
            length=1,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=AnalysisStatus.NOT_STARTED,
        comment="0:분석 전, 1:부분분석완료, 2:완료",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=kst_now, nullable=False, comment="결과도출 시간"
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
    crop_img_path: Mapped[str | None] = mapped_column(
        String(260), nullable=True, comment="매칭된 인물 crop 이미지 경로(썸네일)"
    )
    matching_rate: Mapped[float] = mapped_column(
        Float, nullable=False, default=0, comment="매칭 정확도"
    )

    analysis: Mapped["Analysis"] = relationship(back_populates="details")
    video: Mapped["Video"] = relationship()


class RetentionPolicy(Base):
    """데이터 유형별 보존·만료 정책."""

    __tablename__ = "retention_policy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_type: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    data_label: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_target: Mapped[str] = mapped_column(String(150), nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    expiry_action: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="delete | archive | anonymize"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=kst_now, onupdate=kst_now, nullable=False
    )


class LlmCall(Base):
    __tablename__ = "llm_call"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="자동 증분 ID",
    )

    call_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="호출 유형 (1: 인상착의 한영변환, 2: 챗봇)",
    )

    search_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("search.id"),
        nullable=True,
        comment="연계된 검색 요청 (search의 PK), 없으면 NULL",
    )

    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user.id"),
        nullable=True,
        comment="요청자 (users의 PK), 챗봇 등 비로그인은 NULL",
    )

    chatbot_s_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        comment="챗봇 대화 단위 묶음 ID (LangGraph 멀티 호출 대비)",
    )

    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="사용 모델",
    )

    prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="입력 프롬프트",
    )

    response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="응답 원문 (실패 시 NULL)",
    )

    input_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="입력 토큰 수",
    )

    output_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="출력 토큰 수",
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="응답 소요 시간(ms)",
    )

    cost: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="환산 비용 (모델 단가 * 토큰)",
    )

    status: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="호출 상태 (0: 실패, 1: 성공)",
    )

    error_msg: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="실패 사유 (status=0일 때)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        comment="호출 일시",
    )
