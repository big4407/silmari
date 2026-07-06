"""
개발용 데모 CCTV 영상·탐지·클립 생성.

한 영상에 인상착의에 해당하는 후보 인물을 여러 명 배치하고,
클립·썸네일을 생성해 검색 결과 UI 미리보기에 사용한다.
"""
from __future__ import annotations

import base64
import os
import uuid

import cv2
import numpy as np

from backend.core.config import get_settings
from backend.core.vision.clip_generator import (
    generate_clips_for_result,
    save_thumbnail,
)

DEMO_APPEARANCE = "검은 점퍼, 파란 바지"

# (등장 시작·끝 초, x 위치, 신뢰도)
DEMO_PEOPLE = [
    (3.0, 6.0, 110, 0.84),
    (7.0, 10.0, 300, 0.76),
    (11.0, 14.0, 460, 0.68),
]


def _draw_person(frame: np.ndarray, center_x: int) -> tuple[int, int, int, int]:
    """검은 상의 + 파란 하의 실루엣을 그리고 bbox 반환."""
    h, w = frame.shape[:2]
    body_w = max(48, int(w * 0.12))
    body_h = max(90, int(h * 0.42))
    x1 = max(8, min(w - body_w - 8, center_x - body_w // 2))
    y1 = max(8, int(h * 0.28))
    x2 = x1 + body_w
    y2 = y1 + body_h

    top_h = int(body_h * 0.55)
    cv2.rectangle(frame, (x1, y1), (x2, y1 + top_h), (24, 24, 24), -1)
    cv2.rectangle(frame, (x1, y1 + top_h), (x2, y2), (196, 92, 32), -1)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (200, 200, 200), 1)
    return x1, y1, x2, y2


def _draw_street_scene(frame: np.ndarray, timestamp_sec: float) -> None:
    h, w = frame.shape[:2]
    frame[:] = (72, 78, 84)
    cv2.rectangle(frame, (0, int(h * 0.72)), (w, h), (58, 62, 68), -1)
    cv2.line(frame, (0, int(h * 0.72)), (w, int(h * 0.72)), (120, 120, 120), 2)

    for x in range(0, w, 80):
        cv2.rectangle(
            frame,
            (x + 10, int(h * 0.08)),
            (x + 50, int(h * 0.22)),
            (90, 95, 100),
            -1,
        )

    label = f"CCTV DEMO  {timestamp_sec:04.1f}s"
    cv2.putText(
        frame,
        label,
        (12, 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (230, 230, 230),
        1,
        cv2.LINE_AA,
    )


def create_demo_cctv_video(
    output_path: str,
    *,
    width: int = 640,
    height: int = 360,
    fps: float = 24.0,
    duration_sec: float = 15.0,
) -> list[dict]:
    """데모 거리 CCTV 영상을 만들고 탐지 메타데이터 목록을 반환한다."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"데모 영상을 생성할 수 없습니다: {output_path}")

    detections: list[dict] = []
    total_frames = int(duration_sec * fps)

    for frame_idx in range(total_frames):
        timestamp_sec = round(frame_idx / fps, 2)
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        _draw_street_scene(frame, timestamp_sec)

        for start_sec, end_sec, center_x, confidence in DEMO_PEOPLE:
            if start_sec <= timestamp_sec <= end_sec:
                bbox = _draw_person(frame, center_x)
                mid_sec = round((start_sec + end_sec) / 2, 2)
                if abs(timestamp_sec - mid_sec) < (1.0 / fps) * 0.6:
                    x1, y1, x2, y2 = bbox
                    crop = frame[y1:y2, x1:x2]
                    ok, buffer = cv2.imencode(".jpg", crop)
                    if ok and not any(
                        d["timestamp_sec"] == mid_sec for d in detections
                    ):
                        detections.append(
                            {
                                "timestamp_sec": mid_sec,
                                "bbox": (x1, y1, x2, y2),
                                "confidence": confidence,
                                "image_base64": base64.b64encode(buffer).decode(
                                    "ascii"
                                ),
                            }
                        )

        writer.write(frame)

    writer.release()
    detections.sort(key=lambda d: d["timestamp_sec"])
    return detections


def _write_candidate_clip(
    video_path: str,
    detection: dict,
    output_path: str,
    *,
    fps: float = 24.0,
    padding_sec: float = 1.5,
) -> bool:
    """단일 후보 구간 클립을 mp4v로 저장한다 (imageio 미설치 환경 대비)."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return False

    timestamp_sec = detection["timestamp_sec"]
    start_sec = max(0.0, timestamp_sec - padding_sec)
    end_sec = timestamp_sec + padding_sec
    x1, y1, x2, y2 = detection["bbox"]

    cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000)
    frames: list[np.ndarray] = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        pos_sec = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if pos_sec > end_sec:
            break
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            continue
        frames.append(crop)

    cap.release()
    if not frames:
        return False

    h, w = frames[0].shape[:2]
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (w, h),
    )
    if not writer.isOpened():
        return False

    for frame in frames:
        if frame.shape[1] != w or frame.shape[0] != h:
            frame = cv2.resize(frame, (w, h))
        writer.write(frame)
    writer.release()
    return os.path.exists(output_path) and os.path.getsize(output_path) > 0


def _build_clips_from_detections(
    video_path: str,
    detections: list[dict],
    file_key: str,
) -> dict:
    """탐지 목록에서 후보별 클립·썸네일을 생성한다."""
    settings = get_settings()
    clips_dir = os.path.join(settings.results_dir, "clips")
    thumbs_dir = os.path.join(settings.results_dir, "thumbnails")
    os.makedirs(clips_dir, exist_ok=True)
    os.makedirs(thumbs_dir, exist_ok=True)

    best = max(detections, key=lambda d: d["confidence"])
    thumb_filename = f"{file_key}.jpg"
    save_thumbnail(best["image_base64"], os.path.join(thumbs_dir, thumb_filename))

    clips: list[dict] = []
    for idx, det in enumerate(detections):
        clip_filename = f"{file_key}_{idx}.mp4"
        clip_path = os.path.join(clips_dir, clip_filename)
        if not _write_candidate_clip(video_path, det, clip_path):
            continue

        candidate_thumb = f"{file_key}_c{idx}.jpg"
        save_thumbnail(
            det["image_base64"],
            os.path.join(thumbs_dir, candidate_thumb),
        )
        clips.append(
            {
                "order": idx,
                "filename": clip_filename,
                "start_sec": round(max(0.0, det["timestamp_sec"] - 1.5), 2),
                "end_sec": round(det["timestamp_sec"] + 1.5, 2),
                "confidence": det["confidence"],
                "appearance": DEMO_APPEARANCE,
                "candidate_index": idx + 1,
                "thumbnail_filename": candidate_thumb,
            }
        )

    return {
        "thumbnail_filename": thumb_filename,
        "best_confidence": best["confidence"],
        "best_timestamp_sec": best["timestamp_sec"],
        "clips": clips,
    }


def build_demo_result_media(video_label: str) -> dict:
    """단일 검색 결과용 데모 원본 영상·클립·후보 썸네일을 생성한다."""
    settings = get_settings()
    demo_dir = os.path.join(settings.results_dir, "demo_sources")
    os.makedirs(demo_dir, exist_ok=True)

    file_key = f"demo_{uuid.uuid4().hex[:10]}"
    video_path = os.path.join(demo_dir, f"{file_key}.mp4")

    detections = create_demo_cctv_video(video_path)

    try:
        clip_meta = generate_clips_for_result(video_path, detections, file_key)
        if not clip_meta["clips"]:
            raise RuntimeError("h264 clip generation unavailable")
        thumbs_dir = os.path.join(settings.results_dir, "thumbnails")
        clips: list[dict] = []
        for idx, clip in enumerate(clip_meta["clips"]):
            det = detections[idx] if idx < len(detections) else detections[-1]
            thumb_filename = f"{file_key}_c{idx}.jpg"
            save_thumbnail(
                det["image_base64"],
                os.path.join(thumbs_dir, thumb_filename),
            )
            clips.append(
                {
                    **clip,
                    "confidence": det["confidence"],
                    "appearance": DEMO_APPEARANCE,
                    "candidate_index": idx + 1,
                    "thumbnail_filename": thumb_filename,
                }
            )
    except Exception:
        clip_meta = _build_clips_from_detections(video_path, detections, file_key)
        clips = clip_meta["clips"]

    return {
        "video_filename": video_label,
        "thumbnail_filename": clip_meta["thumbnail_filename"],
        "best_confidence": clip_meta["best_confidence"],
        "best_timestamp_sec": clip_meta["best_timestamp_sec"],
        "clips": clips,
        "candidate_count": len(clips),
    }
