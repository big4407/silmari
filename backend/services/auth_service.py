import hmac
from datetime import timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    sha256,
    utc_now,
    verify_password,
)
from backend.db.models import ApprovalStatus, AuthSession, User

settings = get_settings()


def _as_utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def create_session_and_tokens(
    db: Session,
    *,
    user: User,
    ip_address: str | None,
    user_agent: str | None,
) -> dict:
    session = AuthSession(
        user_id=user.id,
        refresh_token_hash="pending",
        expires_at=utc_now() + timedelta(days=settings.refresh_token_expire_days),
        ip_address=ip_address,
        user_agent=(user_agent or "")[:255] or None,
    )
    db.add(session)
    db.flush()

    refresh_token = create_refresh_token(user_id=user.id, session_id=session.id)
    session.refresh_token_hash = sha256(refresh_token)
    access_token = create_access_token(user_id=user.id, session_id=session.id, role=user.role.value)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "access_expires_in_seconds": settings.access_token_expire_minutes * 60,
    }


def rotate_refresh_token(db: Session, refresh_token: str) -> dict:
    payload = decode_token(refresh_token, expected_type="refresh")
    session = db.get(AuthSession, payload["sid"])
    if session is None:
        raise ValueError("로그인 세션을 찾을 수 없습니다.")
    if session.revoked_at is not None or _as_utc(session.expires_at) <= utc_now():
        raise ValueError("만료되었거나 로그아웃된 세션입니다.")
    if not hmac.compare_digest(session.refresh_token_hash, sha256(refresh_token)):
        raise ValueError("이미 사용되었거나 유효하지 않은 refresh token입니다.")

    user = db.get(User, payload["sub"])
    if user is None or user.approval_status != ApprovalStatus.APPROVED or user.role is None:
        raise ValueError("현재 계정은 로그인 권한이 없습니다.")

    new_refresh_token = create_refresh_token(user_id=user.id, session_id=session.id)
    session.refresh_token_hash = sha256(new_refresh_token)
    session.expires_at = utc_now() + timedelta(days=settings.refresh_token_expire_days)
    access_token = create_access_token(user_id=user.id, session_id=session.id, role=user.role.value)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "access_expires_in_seconds": settings.access_token_expire_minutes * 60,
    }


def revoke_session(db: Session, session_id: str) -> None:
    session = db.get(AuthSession, session_id)
    if session is not None and session.revoked_at is None:
        session.revoked_at = utc_now()
        db.commit()


def change_password(user: User, *, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise ValueError("현재 비밀번호가 올바르지 않습니다.")
    if current_password == new_password:
        raise ValueError("새 비밀번호는 현재 비밀번호와 달라야 합니다.")
    user.password_hash = hash_password(new_password)
