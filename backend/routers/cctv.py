"""
CCTV 영상 분석 API.

[역할] 프론트엔드(CCTVUpload.jsx)에서 업로드된 영상·안내문자를 받아
       탐지 파이프라인을 실행하고, 결과가 있으면 DB에 검색 이력을 저장한다.

[후처리] 탐지 구간 → clip_generator로 클립·썸네일 생성 → SearchResult 레코드 생성
[정리]   분석에 쓴 임시 업로드 파일은 응답 직전에 삭제(storage.remove_file)
"""
import uuid

from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional

from backend.core.pipeline import run_detection_pipeline
from backend.core.vision.clip_generator import generate_clips_for_result
from backend.db.crud import create_search_result
from backend.services.storage import save_upload, remove_file

router = APIRouter()


@router.post("/analyze")
async def analyze_video(
    sms_text: str = Form(...),
    video: UploadFile = File(...),
    reference_photo: Optional[UploadFile] = File(None),
    region: Optional[str] = Form(None),
):
    # 업로드 파일을 data/uploads/ 에 임시 저장 (분석 후 삭제)
    file_id, video_path = save_upload(video.file, video.filename)

    ref_path = None
    if reference_photo:
        _, ref_path = save_upload(reference_photo.file, f"ref_{reference_photo.filename}")

    result = run_detection_pipeline(video_path, sms_text.strip(), ref_path)
    search_result_id = None

    # 탐지가 1건 이상일 때만 클립 생성 + DB 저장 (없으면 API는 결과만 반환)
    if result["detections"]:
        sms_info = result["sms_info"]
        if hasattr(sms_info, "model_dump"):
            sms_dict = sms_info.model_dump()
        else:
            sms_dict = sms_info

        file_key = str(uuid.uuid4())
        clip_meta = generate_clips_for_result(video_path, result["detections"], file_key)

        if clip_meta["clips"]:
            person_name = sms_dict.get("name") or "미상"
            record = create_search_result(
                alert_text=sms_text.strip(),
                person_name=person_name,
                person_age=sms_dict.get("age"),
                region=region or None,
                video_filename=video.filename,
                thumbnail_filename=clip_meta["thumbnail_filename"],
                best_confidence=clip_meta["best_confidence"],
                best_timestamp_sec=clip_meta["best_timestamp_sec"],
                clips=clip_meta["clips"],
                sms_info=sms_dict,
                description=f"{video.filename} · {len(clip_meta['clips'])}개 구간 탐지",
            )
            search_result_id = record.id

    remove_file(video_path)
    remove_file(ref_path)

    return {
        **result,
        "search_result_id": search_result_id,
    }
