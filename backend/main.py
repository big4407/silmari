"""
FastAPI application entrypoint.

[startup lifespan]
  1. Ensure ORM tables exist
  2. Bootstrap the first admin account from .env when configured
  3. Start the background scheduler
"""

from contextlib import asynccontextmanager
from pathlib import Path
from secrets import token_urlsafe

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import or_, select

from backend.core.config import get_settings
from backend.core.runtime import ensure_supported_python
from backend.core.scheduler import start_scheduler
from backend.core.security import hash_password
from backend.db.database import Base, SessionLocal, engine
from backend.db.models import ApprovalStatus, User, UserRole
from backend.routers import (
    admin,
    auth,
    chatbot,
    llm_call,
    messages,
    operations,
    search,
    stats,
    users,
    video,
)

# scheduler logging side effects
import backend.core.scheduler_logging  # noqa: F401

ensure_supported_python()
settings = get_settings()


def bootstrap_admin() -> None:
    """Create the first administrator once."""
    has_admin_identity = bool(
        settings.bootstrap_admin_username
        and settings.bootstrap_admin_email
    )
    has_password_bootstrap = bool(
        settings.bootstrap_admin_password
    )
    has_dev_no_password_bootstrap = (
        settings.bootstrap_admin_no_password
    )

    if not has_admin_identity or not (
        has_password_bootstrap
        or has_dev_no_password_bootstrap
    ):
        return

    with SessionLocal() as db:
        exists = db.scalar(
            select(User).where(
                or_(
                    User.username
                    == settings.bootstrap_admin_username,
                    User.email
                    == settings.bootstrap_admin_email,
                )
            )
        )
        if exists is not None:
            return

        initial_password = (
            settings.bootstrap_admin_password
            or token_urlsafe(48)
        )
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
    Base.metadata.create_all(bind=engine)
    bootstrap_admin()
    start_scheduler()
    yield


app = FastAPI(
    title="Silmari API",
    version="1.1.0",
    lifespan=lifespan,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

app.mount(
    "/media",
    StaticFiles(directory=DATA_DIR),
    name="media",
)
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
app.include_router(
    operations.router,
    prefix="/member",
    tags=["member"],
)
app.include_router(messages.router, prefix="/message", tags=["message"])
app.include_router(chatbot.router, prefix="/chatbot", tags=["chatbot"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(
    llm_call.router,
    prefix="/llm_call",
    tags=["llm_call"],
)
app.include_router(video.router, prefix="/video", tags=["video"])
app.include_router(stats.router, prefix="/member", tags=["member"])


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "Silmari API server is running"}