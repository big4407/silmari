"""
FastAPI 애플리케이션 진입점.

[시작 시 lifespan]
  1. ensure_dirs() — data/uploads, CCTV, results 폴더 생성
  2. Base.metadata.create_all() — ORM 테이블 자동 생성
  3. bootstrap_admin() — .env 기반 최초 관리자 계정 생성

"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── 도메인 라우터 (기능별 API 엔드포인트) ──────────────────────────────────
from backend.routers import (
    llm_call,
    messages,
    admin,
    auth,
    operations,
    users,
    search,
    chatbot,
    video,
)

from backend.db.database import Base, SessionLocal, engine, get_db
from contextlib import asynccontextmanager
from secrets import token_urlsafe
from sqlalchemy import or_, select
from backend.core.config import get_settings
from backend.core.security import hash_password
from backend.core.runtime import ensure_supported_python
from backend.db.models import ApprovalStatus, User, UserRole
from backend.core.scheduler import start_scheduler

# scheduler의 logging을 위한 import
# 아래에서 모듈 사용하지 않는다고 지우면 동작하지 않음
import backend.core.scheduler_logging

ensure_supported_python()
settings = get_settings()


def bootstrap_admin() -> None:
    """Create the first administrator once.

    Production/deployment use should provide BOOTSTRAP_ADMIN_PASSWORD. In local
    development or pytest only, BOOTSTRAP_ADMIN_NO_PASSWORD=true creates an
    administrator with an unknown random password; the local-only development
    endpoint then issues a test token without an administrator password.
    """
    has_admin_identity = bool(
        settings.bootstrap_admin_username and settings.bootstrap_admin_email
    )
    has_password_bootstrap = bool(settings.bootstrap_admin_password)
    has_dev_no_password_bootstrap = settings.bootstrap_admin_no_password

    if not has_admin_identity or not (
        has_password_bootstrap or has_dev_no_password_bootstrap
    ):
        return

    with SessionLocal() as db:
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
    ensure_supported_python()
    Base.metadata.create_all(bind=engine)  # ← 단 1회
    bootstrap_admin()
    start_scheduler()  # 메시지 수집 스케줄러 시작
    yield


app = FastAPI(title="Silmari API", version="1.1.0", lifespan=lifespan)

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
app.include_router(llm_call.router, prefix="/llm_call", tags=["llm_call"])


app.include_router(video.router, prefix="/video", tags=["video"])


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "실마리(Silmari) API 서버 실행 중"}
