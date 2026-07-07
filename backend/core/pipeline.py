"""
실마리(Silmari) 탐지 파이프라인 오케스트레이터.

[발표용 흐름 요약]
  안내문자(sms_text) → LLM 파싱 → 인상착의 구조화
  CCTV 영상(video_path) → 프레임 추출 → YOLO 탐지 → crop 임베딩 → Chroma 검색

호출 진입점: routers/cctv.py 의 POST /api/cctv/analyze
하위 모듈: core/llm/chain, core/vision/frame_extractor, core/vision/crop_embedding,
          core/vision/search_embedding
"""

from __future__ import annotations

from datetime import datetime

from backend.core.llm.chain import run_alert_parse_chain
from backend.core.vision.frame_extractor import extract_frames
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.crud import MatchCandidate, search_embeddings
from backend.db.models import Video, VideoDetail


# ──────────────────────────────────────────────────────────────────────────
# 인덱싱 (전날) — 영상 1개를 처리해 Chroma 저장 + video_detail 기록
# ──────────────────────────────────────────────────────────────────────────
def index_video_pipeline(
    db: Session,
    video_path: str,
    cctv_serial_no: Optional[str] = None,
    region_code: Optional[str] = None,
    recorded_at: Optional[datetime] = None,
) -> dict:
    """영상을 인덱싱한다: video 행 생성 → crop 임베딩(Chroma) → video_detail 저장.

    반환: {"video_id", "indexed_count"}
    """
    # 1) video 행 먼저 생성 (id 확보)
    video = Video(
        cctv_serial_no=cctv_serial_no,
        file_path=video_path,
        region_code=region_code,
        recorded_at=recorded_at,
    )
    db.add(video)
    db.flush()  # video.id 확보

    # 2) 영상 → crop 임베딩 → Chroma 저장 (crop_embedding 경로 — ISSUE-002)
    indexed = []
    # indexed = index_video(
    #     video_path=video_path,
    #     video_id=video.id,
    #     region_code=region_code,
    # )

    # 3) video_detail 행들 저장 (Chroma id = embedding_id 로 매핑)
    for d in indexed:
        db.add(
            VideoDetail(
                video_id=video.id,
                video_timestamp=d.video_timestamp,
                crop_id=d.crop_id,
                position=d.position,
            )
        )

    # 4) video.embedding_id 에 대표 임베딩 키 기록(이 영상의 임베딩 묶음 식별용)
    #    개별 crop 의 embedding_id 는 video_detail 단위로 Chroma 에 있다.
    if indexed:
        video.embedding_id = f"video:{video.id}"

    db.commit()
    return {"video_id": video.id, "indexed_count": len(indexed)}


# ──────────────────────────────────────────────────────────────────────────
# 검색 (당일) — 지역·기간 필터(MySQL) → Chroma threshold 검색
# ──────────────────────────────────────────────────────────────────────────
def search_pipeline(
    db: Session,
    clothes_en: str,
    region_code: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    threshold: Optional[float] = None,
) -> list[MatchCandidate]:
    """인상착의(영문)로 검색. 방식 B: MySQL로 지역·기간을 먼저 거른 뒤,
    그 영상들의 임베딩 안에서만 Chroma 유사도 검색을 수행한다.

    기준을 넘는 후보가 없으면 빈 리스트("매칭 없음")를 반환한다.
    후보의 embedding_id 메타로 video / video_detail 상세를 채워 쓰면 된다.
    """
    if not clothes_en:
        return []

    has_filter = bool(region_code or start_time or end_time)

    # 1) MySQL: 지역·기간에 맞는 video.id 목록 (정형 필터는 MySQL 담당)
    video_ids = None
    if has_filter:
        stmt = select(Video.id)
        if region_code:
            stmt = stmt.where(Video.region_code == region_code)
        if start_time:
            stmt = stmt.where(Video.recorded_at >= start_time)
        if end_time:
            stmt = stmt.where(Video.recorded_at <= end_time)

        video_ids = [vid for (vid,) in db.execute(stmt).all()]
        if not video_ids:
            return []  # 조건에 맞는 영상 자체가 없음 → 매칭 없음

    # 2) Chroma: 그 video 들의 임베딩 안에서만 텍스트 유사도 threshold 검색
    #    (벡터 유사도는 Chroma 담당. video_id 메타 $in 으로 범위 제한)
    kwargs = {"region_code": region_code, "video_ids": video_ids}
    if threshold is not None:
        kwargs["threshold"] = threshold

    # TODO(ISSUE-002): search_embedding / search_missing_person 경로로 연결
    return []


# ──────────────────────────────────────────────────────────────────────────
# (레거시) 업로드=즉시검색 — 기존 cctv.py 호환용. 점진적으로 제거 예정.
# ──────────────────────────────────────────────────────────────────────────
def run_detection_pipeline(
    video_path: str, sms_text: str, reference_img_path: Optional[str] = None
) -> dict:
    from backend.core.config import get_settings
    from backend.core.vision.demo_detection import build_demo_detections_from_video

    # 1단계: 실종 안내문자에서 이름·나이·의류색 등 인상착의 추출
    sms_info = run_alert_parse_chain(sms_text)
    if hasattr(sms_info, "model_dump"):
        sms_dict = sms_info.model_dump()
    else:
        sms_dict = dict(sms_info)

    settings = get_settings()
    detections: list = []

    # TODO: detect_missing_person_pipeline / YOLO 경로로 교체
    # 개발 환경에서는 업로드 영상 기반 데모 탐지로 결과 UI 흐름 검증
    if settings.environment == "development":
        detections = build_demo_detections_from_video(video_path)

    return {
        "sms_info": sms_dict,
        "total_detections": len(detections),
        "face_recognition_used": reference_img_path is not None,
        "detections": detections,
        "demo_mode": bool(detections) and settings.environment == "development",
    }


def detect_missing_person_pipeline(
    query: str,
    video_path: str = "data/CCTV/output_video_1_1_1.mp4",
    frame_interval: int = 5,
    frame_path: str = "data/results/frames",
    detected_path: str = "data/results/detected",
    unique_person_path: str = "data/results/unique_persons",
    max_results: int = 5,
):
    # ML 스택(torchreid, FashionCLIP 등)은 이 함수 호출 시에만 로드
    from backend.core.vision.frame_extractor import frame_extract
    from backend.core.vision.person_detector import person_detect
    from backend.core.vision.check_same_person import check_same_person
    from backend.core.vision.crop_embedding import (
        create_image_embeddings,
        get_image_paths,
        make_metadata,
        normalize_embeddings,
        save_embedding,
    )
    from backend.core.vision.search_embedding import search_embedding

    frame_extract(video_path, frame_interval)
    person_detect(frame_path)
    check_same_person(detected_path)
    image_paths = get_image_paths(unique_person_path)
    embeddings = create_image_embeddings(image_paths)
    normalized_embeddings = normalize_embeddings(embeddings)
    metadatas = make_metadata(image_paths)
    for image_path, embedding, metadata in zip(
        image_paths, normalized_embeddings, metadatas
    ):
        save_embedding(
            id=image_path.stem,
            embedding=embedding.tolist(),
            metadata=metadata,
        )
    result = search_embedding(query, max_results)
    ids = result["ids"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]

    search_results = []
    for rank, (person_id, metadata, distance) in enumerate(
        zip(ids, metadatas, distances), start=1
    ):
        search_results.append(
            {
                "rank": rank,
                "id": person_id,
                "image_path": metadata["image_path"],
                "distance": distance,
            }
        )
    return search_results


if __name__ == "__main__":
    query = input("착의정보를 입력하세요:")
    result = detect_missing_person_pipeline(query)
    print(result)
