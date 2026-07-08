"""
[화면] DevCctvPage (프로덕션 업로드 UI 연동 예정)
[서비스] cctv_analyze_service.CctvAnalyzeService
[테이블] search_result
"""
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from backend.services.cctv_analyze_service import CctvAnalyzeService

router = APIRouter()
_service = CctvAnalyzeService()


@router.post(
    "/analyze",
    summary="CCTV 영상 분석",
    description=(
        "영상+안내문자 업로드 → 탐지 파이프라인 실행 → 클립·썸네일 생성 및 DB 저장. "
        "연결: CctvAnalyzeService → run_detection_pipeline → crud.create_search_result"
    ),
    include_in_schema=False,
)
async def analyze_video(
    sms_text: str = Form(...),
    video: UploadFile = File(...),
    reference_photo: Optional[UploadFile] = File(None),
    region: Optional[str] = Form(None),
):
    return _service.analyze_upload(
        sms_text=sms_text,
        video_file=video.file,
        video_filename=video.filename,
        reference_file=reference_photo.file if reference_photo else None,
        reference_filename=reference_photo.filename if reference_photo else None,
        region=region,
    )
