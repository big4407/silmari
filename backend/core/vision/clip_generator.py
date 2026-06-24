import base64
import os
import subprocess
from typing import Optional

import cv2
import numpy as np

from utils.config import RESULTS_DIR

SEGMENT_GAP_SEC = 2.0
BBOX_PADDING = 0.15


def group_detections_into_segments(detections: list, gap_sec: float = SEGMENT_GAP_SEC) -> list:
    if not detections:
        return []

    sorted_d = sorted(detections, key=lambda d: d["timestamp_sec"])
    segments = [[sorted_d[0]]]
    for det in sorted_d[1:]:
        if det["timestamp_sec"] - segments[-1][-1]["timestamp_sec"] > gap_sec:
            segments.append([det])
        else:
            segments[-1].append(det)
    return segments


def _nearest_detection(segment: list, timestamp_sec: float) -> Optional[dict]:
    return min(segment, key=lambda d: abs(d["timestamp_sec"] - timestamp_sec))


def _even(value: int) -> int:
    return max(2, value // 2 * 2)


def _segment_output_size(segment: list, frame_shape) -> tuple[int, int]:
    h, w = frame_shape[:2]
    max_w, max_h = 0, 0

    for det in segment:
        x1, y1, x2, y2 = det["bbox"]
        pad_x = int((x2 - x1) * BBOX_PADDING)
        pad_y = int((y2 - y1) * BBOX_PADDING)
        bw = min(w, x2 + pad_x) - max(0, x1 - pad_x)
        bh = min(h, y2 + pad_y) - max(0, y1 - pad_y)
        max_w = max(max_w, bw)
        max_h = max(max_h, bh)

    return _even(max_w), _even(max_h)


def _crop_person_frame(frame, det, out_w: int, out_h: int) -> Optional[np.ndarray]:
    x1, y1, x2, y2 = det["bbox"]
    h, w = frame.shape[:2]
    pad_x = int((x2 - x1) * BBOX_PADDING)
    pad_y = int((y2 - y1) * BBOX_PADDING)
    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(w, x2 + pad_x)
    y2 = min(h, y2 + pad_y)

    if x2 <= x1 or y2 <= y1:
        return None

    crop = frame[y1:y2, x1:x2]
    return cv2.resize(crop, (out_w, out_h), interpolation=cv2.INTER_LINEAR)


def _encode_frames_h264(frames: list[np.ndarray], fps: float, output_path: str) -> bool:
    if not frames:
        return False

    try:
        import imageio.v3 as iio

        rgb_frames = [cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) for frame in frames]
        iio.imwrite(
            output_path,
            rgb_frames,
            fps=fps,
            codec="libx264",
            plugin="ffmpeg",
            output_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        )
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception:
        return _encode_frames_opencv_fallback(frames, fps, output_path)


def _encode_frames_opencv_fallback(frames: list[np.ndarray], fps: float, output_path: str) -> bool:
    """imageio/ffmpeg 없을 때 임시 AVI → ffmpeg 재인코딩 시도."""
    temp_avi = output_path.replace(".mp4", "_temp.avi")
    h, w = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(temp_avi, fourcc, fps, (w, h))

    if not writer.isOpened():
        return False

    for frame in frames:
        writer.write(frame)
    writer.release()

    try:
        import imageio_ffmpeg

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [
                ffmpeg_exe,
                "-y",
                "-i",
                temp_avi,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                output_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        os.remove(temp_avi)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception:
        if os.path.exists(temp_avi):
            os.remove(temp_avi)
        return False


def _write_person_clip(
    video_path: str,
    segment: list,
    output_path: str,
) -> bool:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return False

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    start_sec = segment[0]["timestamp_sec"]
    end_sec = segment[-1]["timestamp_sec"] + (2.0 / fps)

    ret, first_frame = cap.read()
    if not ret:
        cap.release()
        return False

    out_w, out_h = _segment_output_size(segment, first_frame.shape)
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0, start_sec * 1000))

    frames = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        pos_sec = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if pos_sec > end_sec:
            break

        det = _nearest_detection(segment, pos_sec)
        if not det:
            continue

        crop = _crop_person_frame(frame, det, out_w, out_h)
        if crop is not None:
            frames.append(crop)

    cap.release()

    if not frames:
        return False

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    return _encode_frames_h264(frames, fps, output_path)


def save_thumbnail(image_base64: str, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(base64.b64decode(image_base64))


def generate_clips_for_result(
    video_path: str,
    detections: list,
    file_key: str,
) -> dict:
    """탐지 구간별 bbox 클립 생성 및 썸네일 저장."""
    clips_dir = os.path.join(RESULTS_DIR, "clips")
    thumbs_dir = os.path.join(RESULTS_DIR, "thumbnails")
    os.makedirs(clips_dir, exist_ok=True)
    os.makedirs(thumbs_dir, exist_ok=True)

    best = max(detections, key=lambda d: d["confidence"])
    thumb_filename = f"{file_key}.jpg"
    thumb_path = os.path.join(thumbs_dir, thumb_filename)
    save_thumbnail(best["image_base64"], thumb_path)

    segments = group_detections_into_segments(detections)
    clips = []

    for idx, segment in enumerate(segments):
        clip_filename = f"{file_key}_{idx}.mp4"
        clip_path = os.path.join(clips_dir, clip_filename)
        if _write_person_clip(video_path, segment, clip_path):
            clips.append(
                {
                    "order": idx,
                    "filename": clip_filename,
                    "start_sec": round(segment[0]["timestamp_sec"], 2),
                    "end_sec": round(segment[-1]["timestamp_sec"], 2),
                }
            )

    return {
        "thumbnail_filename": thumb_filename,
        "best_confidence": best["confidence"],
        "best_timestamp_sec": best["timestamp_sec"],
        "clips": clips,
    }
