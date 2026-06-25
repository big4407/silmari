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
    file_id, video_path = save_upload(video.file, video.filename)

    ref_path = None
    if reference_photo:
        _, ref_path = save_upload(reference_photo.file, f"ref_{reference_photo.filename}")

    result = run_detection_pipeline(video_path, sms_text.strip(), ref_path)
    search_result_id = None

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
