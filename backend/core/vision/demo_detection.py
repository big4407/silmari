"""
개발용 데모 탐지 — YOLO 없이 업로드 영상에서 샘플 프레임을 추출한다.

실제 탐지 파이프라인 연결 전까지 CCTV 분석 → 결과 저장 → UI 흐름 검증용.
"""
from __future__ import annotations

import base64

import cv2


def build_demo_detections_from_video(video_path: str, max_samples: int = 3) -> list:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frame_count / fps if frame_count > 0 else 8.0

    if duration <= 1:
        sample_times = [0.0]
    else:
        step = duration / (max_samples + 1)
        sample_times = [round(step * (i + 1), 2) for i in range(max_samples)]

    detections = []
    for index, timestamp_sec in enumerate(sample_times):
        cap.set(cv2.CAP_PROP_POS_MSEC, max(0, timestamp_sec) * 1000)
        ret, frame = cap.read()
        if not ret:
            continue

        height, width = frame.shape[:2]
        box_w = max(40, int(width * 0.32))
        box_h = max(60, int(height * 0.55))
        x1 = max(0, (width - box_w) // 2)
        y1 = max(0, int(height * 0.18))
        x2 = min(width, x1 + box_w)
        y2 = min(height, y1 + box_h)

        crop = frame[y1:y2, x1:x2]
        ok, buffer = cv2.imencode(".jpg", crop)
        if not ok:
            continue

        detections.append(
            {
                "timestamp_sec": timestamp_sec,
                "bbox": (x1, y1, x2, y2),
                "confidence": round(0.68 + index * 0.07, 2),
                "image_base64": base64.b64encode(buffer).decode("ascii"),
            }
        )

    cap.release()
    return detections
