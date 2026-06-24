from contextlib import asynccontextmanager
from secrets import token_urlsafe

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select

from backend.api.routes import admin, auth, operations, users
from backend.core.config import get_settings
from backend.core.security import hash_password
from backend.core.runtime import ensure_supported_python
from backend.db.database import Base, SessionLocal, engine
from backend.db.models import ApprovalStatus, User, UserRole

ensure_supported_python()
settings = get_settings()


def bootstrap_admin() -> None:
    """Create the first administrator once.

    Production/deployment use should provide BOOTSTRAP_ADMIN_PASSWORD. In local
    development or pytest only, BOOTSTRAP_ADMIN_NO_PASSWORD=true creates an
    administrator with an unknown random password; the local-only development
    endpoint then issues a test token without an administrator password.
    """
    has_admin_identity = bool(settings.bootstrap_admin_username and settings.bootstrap_admin_email)
    has_password_bootstrap = bool(settings.bootstrap_admin_password)
    has_dev_no_password_bootstrap = settings.bootstrap_admin_no_password

    if not has_admin_identity or not (has_password_bootstrap or has_dev_no_password_bootstrap):
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
    Base.metadata.create_all(bind=engine)
    bootstrap_admin()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.1.0",
    description="Silmari RBAC authentication and approval workflow API",
    lifespan=lifespan,
)

# React/Vite development origin only. Replace this with exact production origins before deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(operations.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health_check() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "dev_bootstrap_no_password_enabled": settings.bootstrap_admin_no_password,
    }
