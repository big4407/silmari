"""
FastAPI 애플리케이션 진입점.

[시작 시 lifespan]
  1. ensure_dirs() — data/uploads, CCTV, results 폴더 생성
  2. Base.metadata.create_all() — ORM 테이블 자동 생성
  3. bootstrap_admin() — .env 기반 최초 관리자 계정 생성

[레거시] /api/alert, /api/cctv, /api/result, /api/alerts, /messages, /search,
         /chatbot, /api/sms, /api/video, /api/missing — 하위 호환(deprecated)
"""

# ── FastAPI 프레임워크 ─────────────────────────────────────────────────────
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── 도메인 라우터 (기능별 API 엔드포인트) ──────────────────────────────────
from backend.routers import (
    alert,
    cctv,
    result,
    disaster_alerts,
    messages,
    admin,
    auth,
    operations,
    users,
    search,
    chatbot,
    video,
)

# ── 인프라: DB, 설정, 보안, 스토리지 ─────────────────────────────────────
from backend.services.storage import ensure_dirs
from backend.db.database import Base, SessionLocal, engine, get_db
from backend.core.config import get_settings
from backend.core.security import hash_password
from backend.core.runtime import ensure_supported_python
from backend.db.models import ApprovalStatus, User, UserRole

# ── 백그라운드 스케줄러 (재난문자 수집 등 주기 작업) ─────────────────────
from contextlib import asynccontextmanager
from secrets import token_urlsafe
from sqlalchemy import or_, select
from backend.services.code_group_seed import seed_code_groups_if_empty
from backend.services.retention_policy_seed import seed_retention_policies_if_empty
from backend.core.scheduler import start_scheduler

# scheduler의 logging을 위한 import — 사용하지 않아도 import만으로 로깅 설정이 적용됨
import backend.core.scheduler_logging  # noqa: F401

# 모듈 로드 시점에 Python 버전·환경변수 검증
ensure_supported_python()
settings = get_settings()


def bootstrap_admin() -> None:
    """최초 관리자 계정을 한 번만 생성한다.

    .env에 BOOTSTRAP_ADMIN_USERNAME/EMAIL/PASSWORD를 설정하면 서버 기동 시
    DB에 관리자가 없을 때 자동 생성한다.
    로컬·pytest에서는 BOOTSTRAP_ADMIN_NO_PASSWORD=true로 비밀번호 없이
    랜덤 비밀번호 계정을 만들고, dev 전용 엔드포인트로 테스트 토큰을 발급한다.
    """
    has_admin_identity = bool(
        settings.bootstrap_admin_username and settings.bootstrap_admin_email
    )
    has_password_bootstrap = bool(settings.bootstrap_admin_password)
    has_dev_no_password_bootstrap = settings.bootstrap_admin_no_password

    # 부트스트랩에 필요한 env가 없으면 건너뜀
    if not has_admin_identity or not (
        has_password_bootstrap or has_dev_no_password_bootstrap
    ):
        return

    with SessionLocal() as db:
        # 동일 username 또는 email이 이미 있으면 중복 생성 방지
        exists = db.scalar(
            select(User).where(
                or_(
                    User.username == settings.bootstrap_admin_username,
                    User.email == settings.bootstrap_admin_email,
                )
            )
        )
        if exists is not None:
            return

        # 비밀번호 미설정 시 랜덤 생성 (dev no-password 모드)
        initial_password = settings.bootstrap_admin_password or token_urlsafe(48)
        admin_user = User(
            username=settings.bootstrap_admin_username,
            email=settings.bootstrap_admin_email,
            password_hash=hash_password(initial_password),
            full_name="Silmari System Administrator",
            organization="Silmari",
            department="Platform Operations",
            position="Administrator",
            phone="000-0000-0000",
            requested_role=UserRole.ADMIN,
            role=UserRole.ADMIN,
            approval_status=ApprovalStatus.APPROVED,
        )
        db.add(admin_user)
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """서버 시작·종료 시 한 번씩 실행되는 초기화 훅."""
    ensure_supported_python()  # Python 3.10+ 등 런타임 요구사항 확인
    ensure_dirs()  # data/uploads, CCTV, results 디렉터리 생성
    Base.metadata.create_all(
        bind=engine
    )  # ORM 모델 기준 테이블 자동 생성 (마이그레이션 없을 때)
    bootstrap_admin()  # .env 기반 최초 관리자 계정
    with SessionLocal() as db:
        seed_code_groups_if_empty(db)
        seed_retention_policies_if_empty(db)
    start_scheduler()  # APScheduler — 재난문자 수집 등 cron 작업 시작
    yield  # 이 지점부터 HTTP 요청 수신
    # shutdown 시 정리 작업이 필요하면 yield 아래에 추가


app = FastAPI(title="Silmari API", version="1.1.0", lifespan=lifespan)

# React 프론트엔드(다른 origin)에서 API 호출 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/member", tags=["member"])
app.include_router(users.router, prefix="/member", tags=["member"])
app.include_router(admin.router, prefix="/member", tags=["member"])
app.include_router(operations.router, prefix="/member", tags=["member"])

app.include_router(messages.router, prefix="/message", tags=["message"])
app.include_router(chatbot.router, prefix="/chatbot", tags=["chatbot"])

app.include_router(search.router, prefix="/search", tags=["search"])

app.include_router(video.router, prefix="/video", tags=["video"])

# legacy 미사용 라우터 추후 확인 및 처리
app.include_router(disaster_alerts.router, prefix="/api/alerts", tags=["legacy"])
app.include_router(alert.router, prefix="/api/sms", tags=["legacy"])
app.include_router(cctv.router, prefix="/api/video", tags=["legacy"])
app.include_router(
    result.router, prefix="/api/v1/detection-results", tags=["detection-results"]
)
app.include_router(result.router, prefix="/api/missing", tags=["legacy"])


@app.get("/health", tags=["System"])
def health_check():
    """로드밸런서·모니터링용 헬스체크."""
    return {"status": "ok"}


@app.get("/", tags=["System"])
def root():
    """루트 접속 시 서버 가동 여부 확인용."""
    return {"message": "실마리(Silmari) API 서버 실행 중"}
