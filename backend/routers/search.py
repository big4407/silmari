from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.schemas.search_schema import (
    SearchCreate,
    SearchItem,
    SearchListResponse,
    SearchDetail,
    SearchStatus,
)
from backend.services.search_service import (
    SearchService,
    RegionNotFoundError,
    RegionAmbiguousError,
    InvalidVideoPeriodError,
    VideoNotFoundError,
)

from backend.deps import get_current_user
from backend.db.models import User


# Service 객체를 Depends로 주입하기 위해 생성한 함수
def get_search_service(db: Session = Depends(get_db)) -> SearchService:
    """
    DB 세션을 받아 SearchService 인스턴스를 생성합니다.
    """
    return SearchService(db)


router = APIRouter()


@router.post(
    "",
    response_model=SearchItem,
    status_code=status.HTTP_201_CREATED,
    summary="검색 요청 생성",
)
def create_search(
    search_data: SearchCreate,
    service: SearchService = Depends(get_search_service),
):
    try:
        return service.create_search(search_data)

    except RegionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="입력한 지역을 찾을 수 없습니다.",
        )

    except RegionAmbiguousError as e:
        candidate_names = ", ".join(e.candidate_names)

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "입력한 지역과 일치하는 후보가 여러 개 있습니다. "
                f"다음 후보를 참고하여 더 구체적으로 입력해 주세요: "
                f"{candidate_names}"
            ),
        )

    except InvalidVideoPeriodError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="시작일은 종료일보다 늦을 수 없습니다.",
        )

    except VideoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "해당 지역에는 입력한 기간의 CCTV 영상이 없습니다. "
                "다른 기간을 입력해 주세요."
            ),
        )


@router.get(
    "",
    response_model=SearchListResponse,
    summary="검색 요청 목록 조회",
)
def get_search_list(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(10, ge=1, le=100, description="페이지당 항목 수"),
    current_user: User = Depends(get_current_user),
    service: SearchService = Depends(get_search_service),
):
    return service.get_search_list(page=page, size=size, user_id=current_user.id)


# response_model => 단건이라 SearchDetail로 바꾸는게 좋아보임
@router.get(
    "/{search_id}",
    response_model=SearchDetail,
    summary="검색 요청 단건 조회",
)
def get_search(
    search_id: int,
    service: SearchService = Depends(get_search_service),
):
    try:
        return service.get_search(search_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete(
    "/{search_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="검색 요청 삭제",
)
def delete_search(
    search_id: int,
    service: SearchService = Depends(get_search_service),
):
    try:
        service.delete_search(search_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
