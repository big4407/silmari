"""
실종자 관리 케이스 API — 담당하기/담당취소/완료처리.

조회(목록·상세)는 로그인한 사람 전원(공무원 포함) 가능하다. 상태를 바꾸는
쓰기 작업(담당하기/취소/완료/등록/메모/AI채우기)은 수사관·관리자만 가능하고
공무원은 조회만 할 수 있다.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import User, UserRole
from backend.deps import get_current_user, require_roles
from backend.schemas.missing_person_case_schema import (
    MissingPersonCaseItem,
    MissingPersonCaseListResponse,
    MissingPersonCaseManualCreate,
    MissingPersonCaseNotesUpdate,
)
from backend.services.missing_person_case_service import MissingPersonCaseService

router = APIRouter(tags=["missing-person-cases"])

# 담당하기/취소/완료/등록/메모/AI채우기 — 공무원은 조회만 가능하므로 여기서 제외.
require_case_writer = require_roles(UserRole.ADMIN, UserRole.INVESTIGATOR)


@router.get("", response_model=MissingPersonCaseListResponse)
def list_cases(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None, description="1:대기, 2:진행중, 3:완료"),
    assigned_to_me: bool = Query(default=False),
    keyword: str | None = Query(default=None, description="이름·지역·SN 부분 검색"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 수사관은 자기 담당 건만 본다(강제 — assigned_to_me 값과 무관). 전체
    # 목록은 관리자·공무원만 볼 수 있다. 프론트 체크박스만으로는 API를 직접
    # 호출해 우회할 수 있어서 여기서 강제한다.
    if user.role == UserRole.INVESTIGATOR:
        scoped_investigator_id = user.id
    else:
        scoped_investigator_id = user.id if assigned_to_me else None

    return MissingPersonCaseService(db).list_cases(
        page,
        per_page,
        status=status,
        assigned_investigator_id=scoped_investigator_id,
        keyword=keyword,
    )


@router.get("/{case_id}", response_model=MissingPersonCaseItem)
def get_case(
    case_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return MissingPersonCaseService(db).get_case(case_id)


@router.post("", response_model=MissingPersonCaseItem, status_code=201)
def create_manual_case(
    payload: MissingPersonCaseManualCreate,
    user: User = Depends(require_case_writer),
    db: Session = Depends(get_db),
):
    """안내문자에 안 묶인 케이스 수동 등록(챗봇 상담 결과 등) — 등록자가 바로 담당자가 된다."""
    return MissingPersonCaseService(db).create_manual(payload, actor_id=user.id)


@router.post("/{case_id}/assign", response_model=MissingPersonCaseItem)
def assign_case(
    case_id: int,
    user: User = Depends(require_case_writer),
    db: Session = Depends(get_db),
):
    """"담당하기" 버튼."""
    return MissingPersonCaseService(db).assign(case_id, actor_id=user.id)


@router.post("/{case_id}/enrich", response_model=MissingPersonCaseItem)
def enrich_case(
    case_id: int,
    _: User = Depends(require_case_writer),
    db: Session = Depends(get_db),
):
    """"AI로 채우기" 버튼 — 안내문자 원문에서 이름·성별·나이·인상착의를 그때
    1건만 LLM으로 뽑는다(수집 시점엔 비용 때문에 안 돌림, db/models.py의
    MissingPersonCase docstring 참고)."""
    return MissingPersonCaseService(db).enrich_from_message(case_id)


@router.post("/{case_id}/unassign", response_model=MissingPersonCaseItem)
def unassign_case(
    case_id: int,
    _: User = Depends(require_case_writer),
    db: Session = Depends(get_db),
):
    """"담당 취소" 버튼 — 대기 상태로 되돌린다."""
    return MissingPersonCaseService(db).unassign(case_id)


@router.post("/{case_id}/resolve", response_model=MissingPersonCaseItem)
def resolve_case(
    case_id: int,
    _: User = Depends(require_case_writer),
    db: Session = Depends(get_db),
):
    """"완료 처리" 버튼 — 되돌릴 수 없다."""
    return MissingPersonCaseService(db).resolve(case_id)


@router.patch("/{case_id}/notes", response_model=MissingPersonCaseItem)
def update_case_notes(
    case_id: int,
    payload: MissingPersonCaseNotesUpdate,
    _: User = Depends(require_case_writer),
    db: Session = Depends(get_db),
):
    return MissingPersonCaseService(db).update_notes(case_id, payload.notes)