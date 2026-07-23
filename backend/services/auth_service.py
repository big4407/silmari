"""
인증 비즈니스 로직 — 토큰·세션 생명주기.

[login]     authenticate_user → create_session_and_tokens
[refresh]   refresh token 회전 + access token 재발급
[logout]    revoke_session — revoked_at 설정으로 즉시 무효화
"""

import hmac
from datetime import timedelta

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
from backend.db.models import (
    ApprovalStatus,
    AuthSession,
    LoginFailStatus,
    LoginHistory,
    User,
    UserRole,
)
from backend.repositories.auth_repository import AuthRepository
from backend.schemas.auth_schema import SignUpRequest
from backend.utils.timeutils import as_utc

settings = get_settings()


class AdminRoleRequestNotAllowedError(ValueError):
    """회원가입 시 관리자 역할을 직접 신청한 경우."""


class DuplicateAccountError(ValueError):
    """아이디 또는 이메일이 이미 사용 중인 경우."""


class IdentityNotFoundError(ValueError):
    """아이디 찾기/비밀번호 재설정 시 입력한 본인확인 정보와 일치하는 계정이 없는 경우."""


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = AuthRepository(db)

    def signup(self, payload: SignUpRequest) -> User:
        if payload.requested_role == UserRole.ADMIN:
            raise AdminRoleRequestNotAllowedError(
                "관리자 역할은 직접 신청할 수 없습니다."
            )

        duplicate = self.repository.find_by_username_or_email(
            payload.username, str(payload.email)
        )
        if duplicate:
            raise DuplicateAccountError("이미 사용 중인 아이디 또는 이메일입니다.")

        user = User(
            username=payload.username,
            email=str(payload.email),
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            organization=payload.organization,
            department=payload.department,
            position=payload.position,
            phone=payload.phone,
            requested_role=payload.requested_role,
            approval_status=ApprovalStatus.PENDING,
            role=None,
        )
        return self.repository.add_user(user)

    def get_bootstrap_admin(self) -> User | None:
        """개발용 bootstrap 로그인 대상 관리자 계정(.env 설정과 일치하는)을 찾는다."""
        return self.repository.find_approved_admin(
            settings.bootstrap_admin_username, settings.bootstrap_admin_email
        )

    def record_login_attempt(
        self,
        *,
        username: str,
        success: bool,
        user_id: str | None = None,
        fail_reason: LoginFailStatus | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """로그인 시도를 감사 로그(login_history)에 기록.

        기록 실패가 로그인 자체를 막지 않도록 예외를 삼킨다(감사 로그는 부가 기능).
        """
        try:
            self.repository.add_login_history(
                LoginHistory(
                    user_id=user_id,
                    username=(username or "")[:50],
                    success=success,
                    fail_reason=fail_reason,
                    ip_address=ip_address,
                    user_agent=(user_agent or "")[:255] or None,
                )
            )
            self.db.commit()
        except Exception:
            self.db.rollback()

    def authenticate_user(self, username: str, password: str) -> User | None:
        user = self.repository.find_user_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            return None
        return user

    def create_session_and_tokens(
        self,
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
        self.repository.add_session(session)

        refresh_token = create_refresh_token(user_id=user.id, session_id=session.id)
        session.refresh_token_hash = sha256(refresh_token)
        access_token = create_access_token(
            user_id=user.id, session_id=session.id, role=user.role.value
        )
        self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "access_expires_in_seconds": settings.access_token_expire_minutes * 60,
        }

    def rotate_refresh_token(self, refresh_token: str) -> dict:
        payload = decode_token(refresh_token, expected_type="refresh")
        session = self.repository.get_session(payload["sid"])
        if session is None:
            raise ValueError("로그인 세션을 찾을 수 없습니다.")
        if session.revoked_at is not None or as_utc(session.expires_at) <= utc_now():
            raise ValueError("만료되었거나 로그아웃된 세션입니다.")
        if not hmac.compare_digest(session.refresh_token_hash, sha256(refresh_token)):
            raise ValueError("이미 사용되었거나 유효하지 않은 refresh token입니다.")

        user = self.repository.get_user(payload["sub"])
        if (
            user is None
            or user.approval_status != ApprovalStatus.APPROVED
            or user.role is None
        ):
            raise ValueError("현재 계정은 로그인 권한이 없습니다.")

        new_refresh_token = create_refresh_token(user_id=user.id, session_id=session.id)
        session.refresh_token_hash = sha256(new_refresh_token)
        session.expires_at = utc_now() + timedelta(
            days=settings.refresh_token_expire_days
        )
        access_token = create_access_token(
            user_id=user.id, session_id=session.id, role=user.role.value
        )
        self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "access_expires_in_seconds": settings.access_token_expire_minutes * 60,
        }

    def revoke_session(self, session_id: str) -> None:
        session = self.repository.get_session(session_id)
        if session is not None and session.revoked_at is None:
            session.revoked_at = utc_now()
            self.db.commit()

    def change_password(
        self, user: User, *, current_password: str, new_password: str
    ) -> None:
        if not verify_password(current_password, user.password_hash):
            raise ValueError("현재 비밀번호가 올바르지 않습니다.")
        if current_password == new_password:
            raise ValueError("새 비밀번호는 현재 비밀번호와 달라야 합니다.")
        user.password_hash = hash_password(new_password)

    def find_username(self, *, full_name: str, email: str) -> str:
        """아이디 찾기 — 이름+이메일이 정확히 일치하는 계정의 아이디를 돌려준다."""
        user = self.repository.find_by_full_name_and_email(full_name, email)
        if user is None:
            raise IdentityNotFoundError("입력하신 정보와 일치하는 계정을 찾을 수 없습니다.")
        return user.username

    def verify_identity(self, *, username: str, full_name: str, email: str) -> None:
        """비밀번호 재설정 1단계 — 본인확인만 하고 아무것도 안 바꾼다.

        reset_password도 같은 조회로 다시 한번 확인하므로(아래), 이 단계를
        건너뛰고 바로 reset_password를 호출해도 안전하다 — 이건 순전히
        프론트에서 "새 비밀번호 입력란을 열어도 되는지" 판단하기 위한 것.
        """
        user = self.repository.find_by_identity(username, full_name, email)
        if user is None:
            raise IdentityNotFoundError("입력하신 정보와 일치하는 계정을 찾을 수 없습니다.")

    def reset_password(
        self, *, username: str, full_name: str, email: str, new_password: str
    ) -> None:
        """본인확인(아이디+이름+이메일) 후 바로 비밀번호를 새 값으로 바꾼다."""
        user = self.repository.find_by_identity(username, full_name, email)
        if user is None:
            raise IdentityNotFoundError("입력하신 정보와 일치하는 계정을 찾을 수 없습니다.")
        user.password_hash = hash_password(new_password)
        self.db.commit()