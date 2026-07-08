"""
[화면] SearchResults.jsx, SearchHistory.jsx
[서비스] detection_result_service.DetectionResultService
[테이블] search_result · data/results/ 미디어
"""
from typing import Literal, Optional

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from backend.services.detection_result_service import DetectionResultService

router = APIRouter()
_service = DetectionResultService()


@router.get("/list", include_in_schema=False)
async def missing_list(
    name: Optional[str] = None, age: Optional[int] = None, dummy: bool = False
):
    return await _service.list_missing_persons(name=name, age=age, dummy=dummy)


@router.get("/cctv/list/{region_code}", include_in_schema=False)
def cctv_list(region_code: str):
    return _service.list_cctv_files(region_code)


@router.get(
    "/history",
    include_in_schema=False,
    summary="검색 이력 조회 (레거시)",
)
def detection_history(
    person_name: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = 50,
):
    """하위 호환용. 신규 코드는 GET /detection-results?detail=summary 사용."""
    return _service.list_history(person_name=person_name, region=region, limit=limit)


@router.get(
    "",
    summary="탐지 결과 목록 조회",
    description=(
        "CCTV 분석 결과 목록. "
        "`detail=full`(기본): 클립·상세 포함 — 검색 결과 화면. "
        "`detail=summary`: 경량 응답 — 검색 이력 화면."
    ),
)
def search_results(
    person_name: Optional[str] = None,
    alert_text: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = 50,
    detail: Literal["full", "summary"] = Query(
        "full",
        description="full=클립 포함 상세, summary=검색 이력용 경량",
    ),
):
    if detail == "summary":
        return _service.list_history(
            person_name=person_name,
            region=region,
            limit=limit,
        )
    return _service.list_results(
        person_name=person_name,
        alert_text=alert_text,
        region=region,
        limit=limit,
    )


@router.get(
    "/{result_id}",
    summary="탐지 결과 상세 조회",
)
def search_result_detail(result_id: int):
    return _service.get_result(result_id)


@router.delete(
    "/{result_id}",
    summary="탐지 결과 1건 삭제",
)
def delete_search_result_endpoint(result_id: int):
    return _service.delete_result(result_id)


@router.delete(
    "",
    summary="탐지 결과 조건부 일괄 삭제",
)
def delete_search_results_endpoint(
    person_name: Optional[str] = None,
    alert_text: Optional[str] = None,
    region: Optional[str] = None,
):
    return _service.delete_results(
        person_name=person_name,
        alert_text=alert_text,
        region=region,
    )


@router.get(
    "/media/thumbnails/{filename}",
    summary="썸네일 이미지 다운로드",
    include_in_schema=False,
)
def get_thumbnail(filename: str):
    path = _service.resolve_thumbnail_path(filename)
    return FileResponse(path, media_type="image/jpeg")


@router.get(
    "/media/clips/{filename}",
    summary="탐지 클립 영상 다운로드",
    include_in_schema=False,
)
def get_clip(filename: str):
    path = _service.resolve_clip_path(filename)
    return FileResponse(
        path,
        media_type="video/mp4",
        headers={"Accept-Ranges": "bytes"},
    )
