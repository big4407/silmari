"""
CCTV 영상 분석 오케스트레이션.

[호출] routers/cctv.py
[흐름] storage.save_upload → run_detection_pipeline → clip_generator → crud.create_search_result
[테이블] search_result
"""
import uuid
from typing import BinaryIO, Optional

from backend.core.pipeline import run_detection_pipeline
from backend.core.vision.clip_generator import generate_clips_for_result
from backend.db import crud
from backend.services.storage import remove_file, save_upload


class CctvAnalyzeService:
    def analyze_upload(
        self,
        *,
        sms_text: str,
        video_file: BinaryIO,
        video_filename: str,
        reference_file: Optional[BinaryIO] = None,
        reference_filename: Optional[str] = None,
        region: Optional[str] = None,
    ) -> dict:
        file_id, video_path = save_upload(video_file, video_filename)

        ref_path = None
        if reference_file and reference_filename:
            _, ref_path = save_upload(reference_file, f"ref_{reference_filename}")

        try:
            result = run_detection_pipeline(video_path, sms_text.strip(), ref_path)
            search_result_id = None

            if result["detections"]:
                sms_info = result["sms_info"]
                if hasattr(sms_info, "model_dump"):
                    sms_dict = sms_info.model_dump()
                else:
                    sms_dict = sms_info

                file_key = str(uuid.uuid4())
                clip_meta = generate_clips_for_result(
                    video_path, result["detections"], file_key
                )

                if clip_meta.get("thumbnail_filename"):
                    clip_count = len(clip_meta["clips"])
                    person_name = sms_dict.get("name") or "미상"
                    record = crud.create_search_result(
                        alert_text=sms_text.strip(),
                        person_name=person_name,
                        person_age=sms_dict.get("age"),
                        region=region or None,
                        video_filename=video_filename,
                        thumbnail_filename=clip_meta["thumbnail_filename"],
                        best_confidence=clip_meta["best_confidence"],
                        best_timestamp_sec=clip_meta["best_timestamp_sec"],
                        clips=clip_meta["clips"],
                        sms_info=sms_dict,
                        description=(
                            f"{video_filename} · {clip_count}개 구간 탐지"
                            if clip_count
                            else f"{video_filename} · 탐지 후보 저장"
                        ),
                    )
                    search_result_id = record.id

            return {
                **result,
                "search_result_id": search_result_id,
                "saved_to_db": search_result_id is not None,
            }
        finally:
            remove_file(video_path)
            remove_file(ref_path)
