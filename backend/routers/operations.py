"""
역할 기반 보호 API 예시.

GET /operations/case-search — investigator 역할 전용 (RBAC 데모·향후 검색 연동)
"""
from fastapi import APIRouter, Depends

from backend.deps import require_roles
from backend.db.models import User, UserRole

router = APIRouter(prefix="/operations")


@router.get("/case-search")
def case_search_access(
    current_user: User = Depends(require_roles(UserRole.INVESTIGATOR)),
) -> dict:
    """A single investigator-only placeholder for the future CCTV search pipeline."""
    return {
        "message": "수사관 전용 실종자 후보 검색 기능에 접근할 수 있습니다.",
        "user": current_user.username,
        "role": current_user.role,
    }
