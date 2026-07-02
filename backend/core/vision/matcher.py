# core/vision/matcher.py
# ──────────────────────────────────────────────────────────────────────────
# FashionCLIP 임베딩 기반 인덱싱 / 검색 (Chroma 연동).
#
# 구조 (수집-검색 분리):
#   [인덱싱·전날] index_video(...)  : 영상 → YOLO crop → 이미지 임베딩 → Chroma 저장
#                                     + video_detail 정보(timestamp·crop·bbox) 반환
#   [검색·당일]   search_persons(...): 인상착의(영문) → 텍스트 임베딩
#                                     → Chroma threshold 검색 → 후보(0건 가능)
#
# 점수 원칙:
#   - softmax/top-k(상대평가) 아님. 텍스트-이미지 코사인 절대값 + distance threshold.
#   - 기준 넘는 후보가 없으면 0건("매칭 없음")이 나온다.
# ──────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import uuid
import base64
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from backend.core.vision.person_detector import detect_persons
from backend.core.vision.frame_extractor import extract_frames
from backend.db.crud import (
    MatchCandidate,
    index_embeddings,
    search_embeddings,
)


# FashionCLIP 모델은 무거우므로 1회 로드 후 재사용.
_fclip = None


def _get_fclip():
    global _fclip
    if _fclip is None:
        from fashion_clip.fashion_clip import FashionCLIP

        _fclip = FashionCLIP("fashion-clip")
    return _fclip


def _embed_images(crops_bgr: list[np.ndarray]) -> np.ndarray:
    """OpenCV(BGR) crop 목록 → FashionCLIP 이미지 임베딩 (정규화).

    fashion_clip.encode_images 는 파일 경로 또는 PIL.Image 를 받는다.
    여기서는 메모리 crop을 PIL(RGB)로 변환해 직접 전달한다.
    """
    fclip = _get_fclip()
    pil_imgs = [Image.fromarray(cv2.cvtColor(c, cv2.COLOR_BGR2RGB)) for c in crops_bgr]
    emb = fclip.encode_images(pil_imgs, batch_size=32)
    emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
    return emb


def _embed_text(text_en: str) -> np.ndarray:
    """영문 인상착의 텍스트 1개 → FashionCLIP 텍스트 임베딩 (정규화)."""
    fclip = _get_fclip()
    emb = fclip.encode_text([text_en], batch_size=1)
    emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
    return emb[0]


# ──────────────────────────────────────────────────────────────────────────
# 인덱싱 (전날) — 영상 1개를 처리해 Chroma에 임베딩 저장
# ──────────────────────────────────────────────────────────────────────────
@dataclass
class IndexedDetection:
    """video_detail 한 행에 대응하는 인덱싱 결과."""
    embedding_id: str         # Chroma id = video_detail 과 매핑할 ID
    video_timestamp: int      # 초 단위
    crop_id: int              # 한 프레임 내 사람 구분
    position: str             # "x,y,w,h"


def index_video(
    video_path: str,
    video_id: int,
    region_code: Optional[str] = None,
    frame_stride: int = 1,
) -> list[IndexedDetection]:
    """영상에서 인물 crop을 추출·임베딩해 Chroma에 저장한다.

    반환된 IndexedDetection 목록을 호출부에서 video_detail 행으로 저장하면 된다.
    (embedding_id 를 video_detail/video 에 기록 → MySQL ↔ Chroma 매핑 완성)
    """
    crops: list[np.ndarray] = []
    metas: list[dict] = []
    ids: list[str] = []
    indexed: list[IndexedDetection] = []

    for frame_idx, frame, timestamp_sec in extract_frames(video_path):
        if frame_stride > 1 and int(frame_idx) % frame_stride != 0:
            continue

        for crop_id, det in enumerate(detect_persons(frame)):
            x1, y1, x2, y2 = det["bbox"]
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            emb_id = f"v{video_id}_t{int(timestamp_sec)}_c{crop_id}_{uuid.uuid4().hex[:8]}"
            position = f"{x1},{y1},{x2 - x1},{y2 - y1}"

            crops.append(crop.copy())
            ids.append(emb_id)
            metas.append(
                {
                    "video_id": video_id,
                    "region_code": region_code or "",
                    "video_timestamp": int(timestamp_sec),
                    "crop_id": crop_id,
                }
            )
            indexed.append(
                IndexedDetection(
                    embedding_id=emb_id,
                    video_timestamp=int(timestamp_sec),
                    crop_id=crop_id,
                    position=position,
                )
            )

    if not crops:
        return []

    # 배치 임베딩 → Chroma 저장
    embeddings = _embed_images(crops)
    index_embeddings(
        embedding_ids=ids,
        image_embeddings=[e.tolist() for e in embeddings],
        metadatas=metas,
    )
    return indexed


# ──────────────────────────────────────────────────────────────────────────
# 검색 (당일) — 인상착의 텍스트로 후보 검색
# ──────────────────────────────────────────────────────────────────────────
def search_persons(
    clothes_text_en: str,
    region_code: Optional[str] = None,
    video_ids: Optional[list] = None,
    threshold: Optional[float] = None,
) -> list[MatchCandidate]:
    """영문 인상착의로 Chroma를 검색해 후보를 반환한다.

    clothes_text_en: 한→영 변환된 인상착의 문장
                     (예: "a person wearing a red padded jacket and blue jeans").
    반환이 비어 있으면 "매칭 없음"(기준 넘는 후보 없음).

    후보의 embedding_id 로 MySQL video / video_detail / analysis_detail 을
    조회해 상세(위치·시각·썸네일)를 채운다.
    """
    if not clothes_text_en:
        return []

    text_emb = _embed_text(clothes_text_en)

    kwargs = {"region_code": region_code, "video_ids": video_ids}
    if threshold is not None:
        kwargs["threshold"] = threshold

    return search_embeddings(text_emb.tolist(), **kwargs)


# ──────────────────────────────────────────────────────────────────────────
# 레거시 — cctv.py 즉시 분석 파이프라인 호환
# ──────────────────────────────────────────────────────────────────────────
def match_persons_in_frame(
    frame,
    frame_idx: float,
    timestamp_sec: float,
    alert_info: dict,
    reference_img_path: Optional[str] = None,
) -> list:
    from backend.core.vision.person_detector import check_color_in_region

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

        if use_face and face_similarity < 0.3:
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