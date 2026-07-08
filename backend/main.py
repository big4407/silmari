"""
FastAPI 애플리케이션 진입점.

[시작 시 lifespan]
  1. ensure_dirs() — data/uploads, CCTV, results 폴더 생성
  2. Base.metadata.create_all() — ORM 테이블 자동 생성
  3. bootstrap_admin() — .env 기반 최초 관리자 계정 생성

[아키텍처] Router → Service → Repository/crud → Model
  상세 연결표: docs/api-connection-map.md

[API 분류 — 신규 엔드포인트는 여기에 해당하는지 먼저 확인]
  제품 핵심 (프론트 프로덕션)
    /messages/*              → Dashboard.jsx        (MessageService)
    /alerts/parse            → DevAlert (파싱 미리보기)
    /cctv/analyze            → DevCctv              (CctvAnalyzeService)
    /detection-results/*     → SearchResults, SearchHistory (DetectionResultService)
    /auth/*, /users/me       → Login, Signup
    /chatbot/chat            → ChatbotPage

  관리자 콘솔
    /admin/*                 → pages/admin/*        (routers/admin/ 태그별 파일)

  실험·내부 (docs 숨김 또는 Dev 전용)
    /search-requests/*       → DevSearchPage만      (SearchService)
    /operations/*            → RBAC 데모
    /auth/dev/bootstrap-login
    /alerts/parse, /cctv/analyze, /messages/{sn} 등 → Dev 페이지

[Swagger]
  /docs         — 제품 API (인증·재난문자·탐지결과·챗봇)
  /docs/admin   — 관리자 API (/admin/* + 로그인)
"""

# ── FastAPI 프레임워크 ─────────────────────────────────────────────────────
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

# ── 도메인 라우터 (기능별 API 엔드포인트) ──────────────────────────────────
# admin → backend/routers/admin/ (태그별 서브 라우터)
from backend.routers import (
    alert,
    cctv,
    result,
    messages,
    admin,
    auth,
    operations,
    users,
    search,
    chatbot,
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

# 모든 API의 공통 URL prefix (버전 아님 — 단일 /api 경로)
API_PREFIX = "/api"

# Swagger: /docs(제품) · /docs/admin(관리자)
OPENAPI_TAGS = [
    {"name": "System", "description": "서버 상태 확인 (헬스체크)"},
    {"name": "Authentication", "description": "회원가입·로그인·토큰 갱신"},
    {"name": "Messages", "description": "재난문자 수집·DB 조회 — 대시보드·스케줄러 연동"},
    {"name": "Detection Results", "description": "CCTV 탐지 결과 조회·삭제"},
    {"name": "Chatbot", "description": "대화형 검색"},
]

ADMIN_OPENAPI_TAGS = [
    {"name": "Authentication", "description": "관리자 콘솔 로그인·토큰 (Try it out용)"},
    {"name": "Admin · Members", "description": "회원 목록·승인·반려·정지"},
    {"name": "Admin · Audit", "description": "로그인 이력·관리자 작업 감사 로그"},
    {"name": "Admin · Regions", "description": "행정구역 CRUD·CSV 가져오기/보내기"},
    {"name": "Admin · Code Groups", "description": "시스템 enum 코드 그룹·항목 수정"},
    {"name": "Admin · Retention", "description": "데이터 보존 정책 조회·수정·시뮬레이션"},
    {"name": "Admin · Data Integrity", "description": "DB 무결성 검사 실행·이력·리포트"},
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


app = FastAPI(
    title="Silmari API",
    version="1.1.0",
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
)

# React 프론트엔드(다른 origin)에서 API 호출 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── /api 마운트 (경로 → 라우터 모듈) ─────────────────────────────────────
# 인증·RBAC
app.include_router(auth.router, prefix=API_PREFIX, tags=["Authentication"])
app.include_router(users.router, prefix=API_PREFIX, tags=["Users"], include_in_schema=False)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(operations.router, prefix=API_PREFIX, tags=["Operations"], include_in_schema=False)

# 재난문자 — 수집·DB 조회 (대시보드·스케줄러)
app.include_router(messages.router, prefix=f"{API_PREFIX}/messages")

# dev·내부용 — HTTP는 동작하나 /docs 에는 노출하지 않음
app.include_router(alert.router, prefix=f"{API_PREFIX}/alerts", include_in_schema=False)
app.include_router(search.router, prefix=f"{API_PREFIX}/search-requests", include_in_schema=False)
app.include_router(result.router, prefix=f"{API_PREFIX}/detection-results", tags=["Detection Results"])
app.include_router(cctv.router, prefix=f"{API_PREFIX}/cctv", include_in_schema=False)
app.include_router(chatbot.router, prefix=f"{API_PREFIX}/chatbot", tags=["Chatbot"])


@app.get("/health", tags=["System"], summary="헬스체크")
def health_check():
    """로드밸런서·모니터링용 헬스체크."""
    return {"status": "ok"}


@app.get("/", tags=["System"], summary="서버 상태 확인")
def root():
    """루트 접속 시 서버 가동 여부 확인용."""
    return {"message": "실마리(Silmari) API 서버 실행 중"}


def _strip_api_prefix(schema: dict) -> dict:
    """실제 /api/* 경로를 문서용 /auth/login 형태로 변환."""
    api_paths: dict = {}
    root_paths: dict = {}
    for path, path_item in schema.get("paths", {}).items():
        if path == API_PREFIX or path.startswith(f"{API_PREFIX}/"):
            stripped = path[len(API_PREFIX) :] or "/"
            api_paths[stripped] = path_item
        else:
            root_paths[path] = path_item
    schema["paths"] = {**api_paths, **root_paths}
    return schema


def _filter_paths(schema: dict, predicate) -> dict:
    filtered = {k: v for k, v in schema.get("paths", {}).items() if predicate(k)}
    schema = {**schema, "paths": filtered}
    used_tags: set[str] = set()
    for path_item in filtered.values():
        for operation in path_item.values():
            if isinstance(operation, dict) and "tags" in operation:
                used_tags.update(operation["tags"])
    if "tags" in schema:
        schema["tags"] = [t for t in schema["tags"] if t["name"] in used_tags]
    return schema


_product_openapi_schema: dict | None = None
_admin_openapi_schema: dict | None = None


def _generate_openapi(*, product_only: bool, admin_only: bool) -> dict:
    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
        tags=ADMIN_OPENAPI_TAGS if admin_only else OPENAPI_TAGS,
    )
    schema = _strip_api_prefix(schema)

    if admin_only:
        schema = _filter_paths(
            schema,
            lambda p: p.startswith("/admin") or p.startswith("/auth"),
        )
        schema["servers"] = [{"url": API_PREFIX, "description": "Silmari Admin API"}]
        schema["info"] = {
            **schema.get("info", {}),
            "title": "Silmari Admin API",
            "description": "관리자 콘솔 전용 API. 로그인 후 Bearer 토큰으로 Try it out.",
        }
    elif product_only:
        schema = _filter_paths(schema, lambda p: not p.startswith("/admin"))
        schema["servers"] = [
            {"url": API_PREFIX, "description": "Silmari API (제품)"},
            {"url": "", "description": "System — /health, / (루트)"},
        ]
    else:
        schema["servers"] = [
            {"url": API_PREFIX, "description": "Silmari API (기본)"},
            {"url": "", "description": "System — /health, / (루트)"},
        ]

    return schema


def product_openapi():
    """제품 API 문서 — /docs"""
    global _product_openapi_schema
    if _product_openapi_schema is None:
        _product_openapi_schema = _generate_openapi(product_only=True, admin_only=False)
    return _product_openapi_schema


def admin_openapi():
    """관리자 API 문서 — /docs/admin"""
    global _admin_openapi_schema
    if _admin_openapi_schema is None:
        _admin_openapi_schema = _generate_openapi(product_only=False, admin_only=True)
    return _admin_openapi_schema


def custom_openapi():
    """하위 호환 — 제품 OpenAPI와 동일."""
    return product_openapi()


app.openapi = custom_openapi


@app.get("/docs/admin", include_in_schema=False)
async def admin_swagger_ui():
    return get_swagger_ui_html(
        openapi_url="/openapi/admin.json",
        title="Silmari Admin API",
    )


@app.get("/openapi/admin.json", include_in_schema=False)
async def admin_openapi_json():
    return JSONResponse(admin_openapi())
