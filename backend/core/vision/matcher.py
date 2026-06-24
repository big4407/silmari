import base64
from typing import Optional

import cv2

from core.vision.feature_extractor import compare_face
from core.vision.person_detector import check_color_in_region, detect_persons

# matcher파일 동일인물 검증 기능으로 분리된 이미지를 text query문과 비교해서 점수를 뽑아내 상위 5명을 가져온다.
from fashion_clip.fashion_clip import FashionCLIP
from pathlib import Path
import numpy as np
import os


def match_persons_in_frame(
    frame,
    frame_idx: float,
    timestamp_sec: float,
    alert_info: dict,
    reference_img_path: Optional[str] = None,
) -> list:
    target_color = alert_info.get("clothes")
    clothes_part = alert_info.get("clothes_part", "upper")
    use_face = reference_img_path is not None
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
        face_similarity = 0.0

        if use_face:
            face_similarity = compare_face(person_crop, reference_img_path)
            if face_similarity < 0.3:
                continue

        color = (0, 255, 0) if not use_face else (0, 200, 255)
        cv2.rectangle(
            person_crop,
            (0, 0),
            (person_crop.shape[1] - 1, person_crop.shape[0] - 1),
            color,
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
                "face_similarity": face_similarity,
                "image_base64": img_base64,
                "bbox": [x1, y1, x2, y2],
            }
        )

    return results

image_dir = Path("data/results/unique_persons")
image_dir.mkdir(parents=True, exist_ok=True)
texts = [
    "a person wearing white shirt and gray pants"
]
image_paths = []
for ext in ["*.jpg"]:
    image_paths.extend(image_dir.glob(ext))
image_paths_str = [str(path) for path in image_paths]


fclip = FashionCLIP("fashion-clip")

image_embeddings = fclip.encode_images(image_paths_str, batch_size=32)
text_embeddings = fclip.encode_text(texts, batch_size=32)
image_embeddings /= np.linalg.norm(
    image_embeddings,
    axis =1,
    keepdims=True
)
text_embeddings /= np.linalg.norm(
    text_embeddings,
    axis =1,
    keepdims=True
)
similarities = image_embeddings @ text_embeddings[0]

top_k = 5
top_indices = np.argsort(similarities)[::-1][:top_k]

candidates = []

for rank, index in enumerate(top_indices, start=1):
    candidates.append({
        "rank":rank,
        "image_path": image_paths[index],
        "score": float(similarities[index])
    })

print(candidates)
