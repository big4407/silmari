import base64

import cv2

from backend.core.vision.person_detector import check_color_in_region, detect_persons


def match_persons_in_frame(
    frame,
    frame_idx: float,
    timestamp_sec: float,
    alert_info: dict,
) -> list:
    target_color = alert_info.get("clothes")
    clothes_part = alert_info.get("clothes_part", "upper")
    results = []

    for det in detect_persons(frame):
        x1, y1, x2, y2 = det["bbox"]
        conf = det["confidence"]

        color_ratio = check_color_in_region(
            frame, x1, y1, x2, y2, target_color, clothes_part
        )
        if target_color and color_ratio < 0.2:
            continue

        person_crop = frame[y1:y2, x1:x2].copy()
        cv2.rectangle(
            person_crop,
            (0, 0),
            (person_crop.shape[1] - 1, person_crop.shape[0] - 1),
            (0, 255, 0),
            3,
        )

        _, buffer = cv2.imencode(".jpg", person_crop)
        img_base64 = base64.b64encode(buffer).decode("utf-8")

        results.append(
            {
                "frame": frame_idx,
                "confidence": round(conf, 4),
                "timestamp_sec": round(timestamp_sec, 2),
                "color_ratio": round(color_ratio, 2),
                "image_base64": img_base64,
                "bbox": [x1, y1, x2, y2],
            }
        )

    return results
