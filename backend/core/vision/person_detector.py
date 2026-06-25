from pathlib import Path

from ultralytics import YOLO
import cv2
import numpy as np

from backend.utils.config import YOLO_MODEL_PATH

_model_path = Path(YOLO_MODEL_PATH)
model = YOLO(str(_model_path) if _model_path.exists() else "yolov8n.pt")

COLOR_RANGES = {
    "빨간": [([0, 100, 100], [10, 255, 255]), ([160, 100, 100], [180, 255, 255])],
    "주황": [([11, 100, 100], [25, 255, 255])],
    "노란": [([26, 100, 100], [34, 255, 255])],
    "초록": [([35, 100, 100], [85, 255, 255])],
    "파란": [([100, 120, 50], [125, 255, 255])],
    "보라": [([131, 100, 100], [159, 255, 255])],
    "검은": [([0, 0, 0], [180, 255, 35])],
    "흰": [([0, 0, 200], [180, 30, 255])],
    "회색": [([0, 0, 50], [180, 30, 200])],
    "분홍": [([0, 50, 200], [10, 150, 255])],
}


def check_color_in_region(
    frame, x1, y1, x2, y2, target_color: str, clothes_part: str
) -> float:
    if not target_color or target_color not in COLOR_RANGES:
        return 1.0

    height = y2 - y1
    if clothes_part == "upper":
        region = frame[y1 : y1 + int(height * 0.6), x1:x2]
    elif clothes_part == "lower":
        region = frame[y1 + int(height * 0.5) : y2, x1:x2]
    else:
        region = frame[y1:y2, x1:x2]

    if region.size == 0:
        return 0.0

    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    total_pixels = region.shape[0] * region.shape[1]
    matched_pixels = 0

    for lower, upper in COLOR_RANGES[target_color]:
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        matched_pixels += cv2.countNonZero(mask)

    return matched_pixels / total_pixels


def detect_persons(frame, conf_threshold: float = 0.85):
    results = model(frame, classes=[0], verbose=False)
    detections = []

    for r in results:
        for box in r.boxes:
            conf = float(box.conf[0])
            if conf < conf_threshold:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            detections.append({"bbox": (x1, y1, x2, y2), "confidence": conf})

    return detections
