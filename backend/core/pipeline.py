"""
실마리(Silmari) 탐지 파이프라인 오케스트레이터.

[발표용 흐름 요약]
  안내문자(sms_text) → LLM 파싱 → 인상착의 구조화
  CCTV 영상(video_path) → 프레임 추출 → 프레임별 인물 매칭
  (선택) 참조 사진(reference_img_path) → 얼굴 재식별 보조

호출 진입점: routes/cctv.py 의 POST /api/cctv/analyze
하위 모듈: core/llm/chain, core/vision/frame_extractor, core/vision/matcher
"""
from backend.core.llm.chain import run_alert_parse_chain
from backend.core.vision.frame_extractor import extract_frames
from backend.core.vision.matcher import match_persons_in_frame
from typing import Optional


def run_detection_pipeline(
    video_path: str, sms_text: str, reference_img_path: Optional[str] = None
) -> dict:
    # 1단계: 실종 안내문자에서 이름·나이·의류색 등 인상착의 추출
    alert_info = run_alert_parse_chain(sms_text)
    detections = []

    # 2단계: 영상을 프레임 단위로 순회하며 후보 인물 탐지·필터링
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
