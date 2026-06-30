from backend.core.llm.chain import run_alert_parse_chain
from backend.core.vision.frame_extractor import extract_frames
from backend.core.vision.matcher import match_persons_in_frame
from typing import Optional


def run_detection_pipeline(
    video_path: str, sms_text: str, reference_img_path: Optional[str] = None
) -> dict:
    alert_info = run_alert_parse_chain(sms_text)
    detections = []

    for frame_idx, frame, timestamp_sec in extract_frames(video_path):
        detections.extend(
            match_persons_in_frame(
                frame,
                frame_idx,
                timestamp_sec,
                alert_info.model_dump(),
                reference_img_path,
            )
        )

    return {
        "sms_info": alert_info,
        "total_detections": len(detections),
        "face_recognition_used": reference_img_path is not None,
        "detections": detections,
    }
