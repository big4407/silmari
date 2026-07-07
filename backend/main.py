"""
FastAPI 애플리케이션 진입점.

[시작 시 lifespan]
  1. ensure_dirs() — data/uploads, CCTV, results 폴더 생성
  2. Base.metadata.create_all() — ORM 테이블 자동 생성
  3. bootstrap_admin() — .env 기반 최초 관리자 계정 생성

[라우터 — canonical]
  /api/auth|users|admin|operations  — 인증·RBAC
  /api/messages                     — 재난문자 수집·조회
  /api/disaster-alerts              — 대시보드 재난 알림
  /api/alerts                       — 안내문자 파싱
  /api/search-requests              — 검색 요청 CRUD
  /api/detection-results            — CCTV 탐지 결과·미디어
  /api/cctv                         — 영상 분석
  /api/chatbot                      — 챗봇

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

# 모든 신규 API의 공통 prefix (프론트엔드·OpenAPI 문서 기준 경로)
API_V1 = "/api"

# Swagger UI(/docs)에서 API를 기능별로 묶어 보여주는 태그 정의
OPENAPI_TAGS = [
    {"name": "Authentication", "description": "회원가입·로그인·토큰"},
    {"name": "Users", "description": "내 프로필"},
    {"name": "Admin", "description": "회원 승인·관리"},
    {"name": "Protected example", "description": "RBAC 데모"},
    {"name": "Messages", "description": "재난문자 수집·조회"},
    {"name": "Disaster Alerts", "description": "대시보드 재난 알림"},
    {"name": "Alert Parsing", "description": "안내문자 인상착의 파싱"},
    {"name": "Search Requests", "description": "실종 검색 요청 CRUD"},
    {"name": "Detection Results", "description": "CCTV 탐지 결과·미디어"},
    {"name": "CCTV", "description": "영상 업로드·분석"},
    {"name": "Chatbot", "description": "대화형 검색"},
    {"name": "legacy (deprecated)", "description": "구 URI — 제거 예정"},
]

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

# ── /api (canonical) — 신규 클라이언트는 이 경로만 사용 ──────────────────
# 인증·RBAC
app.include_router(auth.router, prefix=API_V1)       # /api/auth — 로그인·회원가입·토큰
app.include_router(users.router, prefix=API_V1)      # /api/users — 내 프로필
app.include_router(admin.router, prefix=API_V1)      # /api/admin — 회원 승인·관리
app.include_router(operations.router, prefix=API_V1)  # /api/operations — RBAC 데모

# 재난·검색·분석 도메인
app.include_router(messages.router, prefix=f"{API_V1}/messages", tags=["Messages"])
app.include_router(disaster_alerts.router, prefix=f"{API_V1}/disaster-alerts", tags=["Disaster Alerts"])
app.include_router(alert.router, prefix=f"{API_V1}/alerts", tags=["Alert Parsing"])
app.include_router(search.router, prefix=f"{API_V1}/search-requests", tags=["Search Requests"])
app.include_router(result.router, prefix=f"{API_V1}/detection-results", tags=["Detection Results"])
app.include_router(cctv.router, prefix=f"{API_V1}/cctv", tags=["CCTV"])
app.include_router(chatbot.router, prefix=f"{API_V1}/chatbot", tags=["Chatbot"])
app.include_router(video.router, prefix="/video", tags=["video"])

# ── legacy (deprecated) — 구 프론트·스크립트 하위 호환, 제거 예정 ────────
app.include_router(messages.router, prefix="/messages", tags=["legacy (deprecated)"])
app.include_router(disaster_alerts.router, prefix="/api/alerts", tags=["legacy (deprecated)"])
app.include_router(alert.router, prefix="/api/alert", tags=["legacy (deprecated)"])
app.include_router(search.router, prefix="/search", tags=["legacy (deprecated)"])
app.include_router(result.router, prefix="/api/result", tags=["legacy (deprecated)"])
app.include_router(cctv.router, prefix="/api/cctv", tags=["legacy (deprecated)"])
app.include_router(chatbot.router, tags=["legacy (deprecated)"])
app.include_router(alert.router, prefix="/api/sms", tags=["legacy (deprecated)"])
app.include_router(cctv.router, prefix="/api/video", tags=["legacy (deprecated)"])
app.include_router(result.router, prefix="/api/missing", tags=["legacy (deprecated)"])


@app.get("/health", tags=["System"])
def health_check():
    """로드밸런서·모니터링용 헬스체크."""
    return {"status": "ok"}


@app.get("/", tags=["System"])
def root():
    """루트 접속 시 서버 가동 여부 확인용."""
    return {"message": "실마리(Silmari) API 서버 실행 중"}
