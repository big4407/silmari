from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.db.models import ApprovalStatus, AuthSession, LoginHistory, User, UserRole


class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── User ────────────────────────────────────────────────────────────
    def find_user_by_username(self, username: str) -> User | None:
        return self.db.scalar(select(User).where(User.username == username))

    def get_user(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def find_by_username_or_email(self, username: str, email: str) -> User | None:
        """회원가입 중복 체크 — 아이디/이메일 둘 중 하나라도 겹치면 반환."""
        return self.db.scalar(
            select(User).where(or_(User.username == username, User.email == email))
        )

    def find_by_full_name_and_email(self, full_name: str, email: str) -> User | None:
        """아이디 찾기 — 이름+이메일이 정확히 일치하는 계정만."""
        return self.db.scalar(
            select(User).where(User.full_name == full_name, User.email == email)
        )

    def find_by_identity(
        self, username: str, full_name: str, email: str
    ) -> User | None:
        """비밀번호 재설정 본인확인 — 아이디+이름+이메일 셋 다 일치해야 한다."""
        return self.db.scalar(
            select(User).where(
                User.username == username,
                User.full_name == full_name,
                User.email == email,
            )
        )

    def add_user(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def find_approved_admin(self, username: str, email: str) -> User | None:
        """개발용 bootstrap 로그인 대상 — 승인된 관리자 계정만."""
        return self.db.scalar(
            select(User).where(
                User.username == username,
                User.email == email,
                User.role == UserRole.ADMIN,
                User.approval_status == ApprovalStatus.APPROVED,
            )
        )

    # ── AuthSession ─────────────────────────────────────────────────────
    def get_session(self, session_id: str) -> AuthSession | None:
        return self.db.get(AuthSession, session_id)

    def add_session(self, session: AuthSession) -> AuthSession:
        """세션을 추가하고 flush만 한다(커밋 전 session.id가 필요한 호출부 때문)."""
        self.db.add(session)
        self.db.flush()
        return session

    # ── LoginHistory ────────────────────────────────────────────────────
    def add_login_history(self, entry: LoginHistory) -> None:
        self.db.add(entry)