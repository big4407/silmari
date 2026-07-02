"""
실마리(Silmari) 탐지 파이프라인 오케스트레이터.

[발표용 흐름 요약]
  안내문자(sms_text) → LLM 파싱 → 인상착의 구조화
  CCTV 영상(video_path) → 프레임 추출 → 프레임별 인물 매칭
  (선택) 참조 사진(reference_img_path) → 얼굴 재식별 보조

호출 진입점: routes/cctv.py 의 POST /api/cctv/analyze
하위 모듈: core/llm/chain, core/vision/frame_extractor, core/vision/matcher
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
    db.flush()   # video.id 확보

    # 2) 영상 → crop 임베딩 → Chroma 저장 (matcher가 처리)
    indexed=[]
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
            return []   # 조건에 맞는 영상 자체가 없음 → 매칭 없음

    # 2) Chroma: 그 video 들의 임베딩 안에서만 텍스트 유사도 threshold 검색
    #    (벡터 유사도는 Chroma 담당. video_id 메타 $in 으로 범위 제한)
    kwargs = {"region_code": region_code, "video_ids": video_ids}
    if threshold is not None:
        kwargs["threshold"] = threshold

    # return search_persons(clothes_en, **kwargs)
    return ""


# ──────────────────────────────────────────────────────────────────────────
# (레거시) 업로드=즉시검색 — 기존 cctv.py 호환용. 점진적으로 제거 예정.
# ──────────────────────────────────────────────────────────────────────────
def run_detection_pipeline(
    video_path: str, sms_text: str, reference_img_path: Optional[str] = None
) -> dict:
    # 1단계: 실종 안내문자에서 이름·나이·의류색 등 인상착의 추출
    alert_info = run_alert_parse_chain(sms_text)
    detections = []

    # 2단계: 영상을 프레임 단위로 순회하며 후보 인물 탐지·필터링
    for frame_idx, frame, timestamp_sec in extract_frames(video_path):
        detections.extend(
            # match_persons_in_frame(
            #     frame,
            #     frame_idx,
            #     timestamp_sec,
            #     alert_info.model_dump(),
            #     reference_img_path,
            # )
        )

    return {
        "sms_info": {"raw_text": sms_text},
        "total_detections": 0,
        "face_recognition_used": reference_img_path is not None,
        "detections": [],
        "deprecated": True,
    }

# 엄태윤 파이프라인 — 호출 시에만 무거운 vision 모듈 로드
def detect_missing_person_pipeline(
        query:str,
        video_path:str="data/CCTV/output_video_1_1_1.mp4", 
        frame_interval:int=5,
        frame_path:str="data/results/frames",
        detected_path:str="data/results/detected",
        unique_person_path:str="data/results/unique_persons",
        max_results:int=5
):
    from backend.core.vision.frame_extractor import frame_extract
    from backend.core.vision.person_detector import person_detect
    from backend.core.vision.check_same_person import check_same_person
    from backend.core.vision.crop_embedding import (
        get_image_paths,
        create_image_embeddings,
        normalize_embeddings,
        make_metadata,
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
    for image_path, embedding, metadata in zip(image_paths, normalized_embeddings, metadatas):
        save_embedding(
            id = image_path.stem,
            embedding = embedding.tolist(),
            metadata = metadata
        )
    result = search_embedding(query, max_results)
    ids = result["ids"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]

    search_results = []
    for rank, (person_id, metadata, distance) in enumerate(
        zip(ids, metadatas, distances),
        start=1
        ):
        search_results.append({
            "rank": rank,
            "id": person_id,
            "image_path": metadata["image_path"],
            "distance": distance
        })
    return search_results

if __name__ == "__main__":
    query = input("착의정보를 입력하세요:")
    result = detect_missing_person_pipeline(query)
    print(result)