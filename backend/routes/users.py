"""
사용자 프로필 API.

GET/PATCH /users/me — 로그인 사용자 정보 조회·수정 (비밀번호 변경 포함)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.deps import get_current_user
from backend.db.database import get_db
from backend.db.models import User
from backend.schemas.auth import UserResponse
from backend.schemas.user import UpdateMyProfileRequest
from backend.services.auth_service import change_password

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    payload: UpdateMyProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if (payload.current_password is None) != (payload.new_password is None):
        raise HTTPException(status_code=422, detail="비밀번호 변경 시 현재 비밀번호와 새 비밀번호를 모두 입력해야 합니다.")

    if payload.current_password and payload.new_password:
        try:
            change_password(
                current_user,
                current_password=payload.current_password,
                new_password=payload.new_password,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payload.phone is not None:
        current_user.phone = payload.phone
    if payload.department is not None:
        current_user.department = payload.department
    if payload.position is not None:
        current_user.position = payload.position

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user
