import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from backend.core.config import get_settings

settings = get_settings()
password_hash = PasswordHash.recommended()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, stored_hash: str) -> bool:
    return password_hash.verify(plain_password, stored_hash)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _encode_token(*, subject: str, session_id: str, role: str | None, token_type: str, expires_delta: timedelta) -> str:
    now = utc_now()
    payload = {
        "sub": subject,
        "sid": session_id,
        "role": role,
        "type": token_type,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "nbf": now,
        "exp": now + expires_delta,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(*, user_id: str, session_id: str, role: str) -> str:
    return _encode_token(
        subject=user_id,
        session_id=session_id,
        role=role,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(*, user_id: str, session_id: str) -> str:
    return _encode_token(
        subject=user_id,
        session_id=session_id,
        role=None,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str, *, expected_type: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "sid", "type", "jti"]},
        )
    except InvalidTokenError as exc:
        raise ValueError("유효하지 않거나 만료된 토큰입니다.") from exc

    if payload.get("type") != expected_type:
        raise ValueError("토큰 유형이 올바르지 않습니다.")
    return payload
