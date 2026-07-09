"""
인증 API — 회원가입·로그인·토큰 갱신·로그아웃.

[승인 흐름] signup(pending) → admin 승인 → login → JWT 발급
[개발용]    POST /auth/dev/bootstrap-login — 로컬 전용, NO_PASSWORD 모드
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.deps import get_current_session_id, get_current_user
from backend.core.config import get_settings
from backend.db.database import get_db
from backend.db.models import LoginFailStatus, ApprovalStatus, User
from backend.schemas.auth_schema import (
    LoginRequest,
    RefreshRequest,
    SignUpRequest,
    SignUpResponse,
    TokenResponse,
)
from backend.services.auth_service import (
    AdminRoleRequestNotAllowedError,
    AuthService,
    DuplicateAccountError,
)

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/auth")


def _is_local_request(request: Request) -> bool:
    """Permit the insecure development bootstrap only from loopback/test clients."""
    client_host = request.client.host if request.client else ""
    return client_host in {"127.0.0.1", "::1", "localhost", "testclient"}


@router.post(
    "/signup", response_model=SignUpResponse, status_code=status.HTTP_201_CREATED
)
def signup(payload: SignUpRequest, db: Session = Depends(get_db)) -> SignUpResponse:
    try:
        user = AuthService(db).signup(payload)
    except AdminRoleRequestNotAllowedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except DuplicateAccountError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    return SignUpResponse(
        message="회원가입 신청이 접수되었습니다. 관리자 승인 후 로그인할 수 있습니다.",
        user=user,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest, request: Request, db: Session = Depends(get_db)
) -> TokenResponse:
    service = AuthService(db)
    _ip = request.client.host if request.client else None
    _ua = request.headers.get("user-agent")

    def _fail(
        reason: LoginFailStatus, status_code: int, detail: str, uid: str | None = None
    ):
        service.record_login_attempt(
            username=payload.username,
            success=False,
            user_id=uid,
            fail_reason=reason,
            ip_address=_ip,
            user_agent=_ua,
        )
        raise HTTPException(status_code=status_code, detail=detail)

    user = service.authenticate_user(payload.username, payload.password)
    if user is None:
        _fail(
            LoginFailStatus.BAD_CREDENTIALS,
            status.HTTP_401_UNAUTHORIZED,
            "아이디 또는 비밀번호가 올바르지 않습니다.",
        )
    if user.approval_status == ApprovalStatus.PENDING:
        _fail(
            LoginFailStatus.PENDING,
            status.HTTP_403_FORBIDDEN,
            "관리자 승인 대기 중인 계정입니다.",
            user.id,
        )
    if user.approval_status == ApprovalStatus.REJECTED:
        _fail(
            LoginFailStatus.REJECTED,
            status.HTTP_403_FORBIDDEN,
            "가입 신청이 반려된 계정입니다.",
            user.id,
        )
    if user.approval_status == ApprovalStatus.SUSPENDED:
        _fail(
            LoginFailStatus.SUSPENDED,
            status.HTTP_403_FORBIDDEN,
            "사용이 정지된 계정입니다.",
            user.id,
        )
    if user.role is None:
        _fail(
            LoginFailStatus.NO_ROLE,
            status.HTTP_403_FORBIDDEN,
            "역할이 부여되지 않은 계정입니다.",
            user.id,
        )

    # 성공 기록
    service.record_login_attempt(
        username=user.username,
        success=True,
        user_id=user.id,
        ip_address=_ip,
        user_agent=_ua,
    )
    return service.create_session_and_tokens(
        user=user,
        ip_address=_ip,
        user_agent=_ua,
    )


@router.post("/dev/bootstrap-login", response_model=TokenResponse)
def development_bootstrap_login(
    request: Request, db: Session = Depends(get_db)
) -> TokenResponse:
    """DEVELOPMENT/TEST ONLY: obtain a bootstrap-admin token without an admin password.

    This endpoint is intentionally unavailable unless both conditions are true:
    1. ENVIRONMENT is development or test.
    2. BOOTSTRAP_ADMIN_NO_PASSWORD=true.

    It also rejects non-loopback requests. Never enable this setting in production.
    """
    if (
        settings.environment not in {"development", "test"}
        or not settings.bootstrap_admin_no_password
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="개발용 bootstrap 로그인이 비활성화되어 있습니다.",
        )
    if not _is_local_request(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="개발용 bootstrap 로그인은 로컬 환경에서만 사용할 수 있습니다.",
        )

    admin_user = AuthService(db).get_bootstrap_admin()
    if admin_user is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bootstrap 관리자 계정이 준비되지 않았습니다. 서버를 다시 시작하십시오.",
        )

    logger.warning("Development bootstrap token issued for local testing only.")
    return AuthService(db).create_session_and_tokens(
        user=admin_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        return AuthService(db).rotate_refresh_token(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    # current_user validates that the access token belongs to an active approved user.
    _ = current_user
    AuthService(db).revoke_session(session_id)
