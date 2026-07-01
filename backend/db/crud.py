# db/crud.py
import json
from typing import Optional

from backend.db.database import SessionLocal      
from backend.db.models import DetectionRecord, SearchResult


def save_detection_result(alert_text: str, video_filename: str, result_json: str):
    db = SessionLocal()
    try:
        record = DetectionRecord(
            alert_text=alert_text,
            video_filename=video_filename,
            result_json=result_json,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    finally:
        db.close()


def get_detection_results(limit: int = 20):
    db = SessionLocal()
    try:
        return db.query(DetectionRecord).order_by(DetectionRecord.created_at.desc()).limit(limit).all()
    finally:
        db.close()


def create_search_result(
    alert_text: str,
    person_name: str,
    person_age: Optional[int],
    region: Optional[str],
    video_filename: str,
    thumbnail_filename: str,
    best_confidence: float,
    best_timestamp_sec: float,
    clips: list,
    sms_info: dict,
    description: Optional[str] = None,
) -> SearchResult:
    db = SessionLocal()
    try:
        record = SearchResult(
            alert_text=alert_text,
            person_name=person_name,
            person_age=person_age,
            region=region,
            video_filename=video_filename,
            thumbnail_filename=thumbnail_filename,
            best_confidence=best_confidence,
            best_timestamp_sec=best_timestamp_sec,
            clips_json=json.dumps(clips, ensure_ascii=False),
            sms_info_json=json.dumps(sms_info, ensure_ascii=False),
            description=description,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    finally:
        db.close()


def get_search_results(
    person_name: Optional[str] = None,
    alert_text: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = 50,
) -> list:
    db = SessionLocal()
    try:
        query = _filter_search_results_query(
            db.query(SearchResult).order_by(SearchResult.created_at.desc()),
            person_name=person_name,
            alert_text=alert_text,
            region=region,
        )
        return query.limit(limit).all()
    finally:
        db.close()


def get_search_result_by_id(result_id: int) -> Optional[SearchResult]:
    db = SessionLocal()
    try:
        return db.query(SearchResult).filter(SearchResult.id == result_id).first()
    finally:
        db.close()


def _filter_search_results_query(
    query,
    person_name: Optional[str] = None,
    alert_text: Optional[str] = None,
    region: Optional[str] = None,
):
    if alert_text:
        query = query.filter(SearchResult.alert_text == alert_text.strip())
    elif person_name:
        query = query.filter(SearchResult.person_name == person_name)
    if region and region != "전국":
        query = query.filter(SearchResult.region.contains(region))
    return query


def delete_search_result(result_id: int) -> Optional[SearchResult]:
    db = SessionLocal()
    try:
        record = db.query(SearchResult).filter(SearchResult.id == result_id).first()
        if not record:
            return None
        db.delete(record)
        db.commit()
        return record
    finally:
        db.close()


def delete_search_results(
    person_name: Optional[str] = None,
    alert_text: Optional[str] = None,
    region: Optional[str] = None,
) -> list:
    db = SessionLocal()
    try:
        query = _filter_search_results_query(
            db.query(SearchResult),
            person_name=person_name,
            alert_text=alert_text,
            region=region,
        )
        records = query.all()
        for record in records:
            db.delete(record)
        db.commit()
        return records
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
# Chroma (벡터 임베딩) CRUD — 인물 임베딩 저장/검색/삭제
# 연결은 database.get_chromadb(). MariaDB CRUD 와 같은 파일에 두되
# 함수명에 embeddings 를 붙여 구분한다.
#
# 검색 원칙: top-k 아님. distance threshold 로 거르므로
#           기준 넘는 후보가 없으면 0건("매칭 없음")이 나온다.
# ──────────────────────────────────────────────────────────────
from dataclasses import dataclass

import numpy as np

from backend.db.database import get_chromadb


# 코사인 "거리" 임계값(작을수록 유사). 운영 데이터로 캘리브레이션.
EMBEDDING_DISTANCE_THRESHOLD = 0.35


@dataclass
class MatchCandidate:
    embedding_id: str
    similarity: float      # 1 - distance
    distance: float
    metadata: dict


def _normalize(vec) -> list:
    arr = np.asarray(vec, dtype=np.float32)
    norm = np.linalg.norm(arr)
    return arr.tolist() if norm == 0 else (arr / norm).tolist()


def index_embeddings(embedding_ids: list, image_embeddings: list, metadatas: list) -> None:
    """인물 crop 이미지 임베딩들을 Chroma에 저장(upsert).
    embedding_ids 는 MySQL video.embedding_id 와 동일 ID로 매핑."""
    if not embedding_ids:
        return
    get_chromadb().upsert(
        ids=embedding_ids,
        embeddings=[_normalize(e) for e in image_embeddings],
        metadatas=metadatas,
    )


def search_embeddings(
    text_embedding,
    threshold: float = EMBEDDING_DISTANCE_THRESHOLD,
    region_code: str = None,
    video_ids: list = None,
    max_candidates: int = 100,
) -> list:
    """인상착의 텍스트 임베딩으로 검색하고 threshold 넘는 후보만 반환.
    기준 넘는 후보가 없으면 빈 리스트("매칭 없음").

    방식 B (정형은 MySQL, 벡터는 Chroma):
      video_ids 를 주면 해당 영상들의 임베딩 안에서만 검색한다.
      MySQL에서 지역·기간으로 거른 video.id 목록을 넘기며,
      Chroma 는 임베딩 메타(video_id)의 $in 필터로 그 안만 본다.
      빈 리스트면 대상 영상이 없으므로 즉시 [] 반환."""
    if video_ids is not None and len(video_ids) == 0:
        return []   # 지역·기간에 맞는 영상이 없음 → 매칭 없음

    # where 조건 조합 (region_code 메타 + video_id $in)
    conditions = []
    if region_code:
        conditions.append({"region_code": region_code})
    if video_ids:
        conditions.append({"video_id": {"$in": list(video_ids)}})

    if not conditions:
        where = None
    elif len(conditions) == 1:
        where = conditions[0]
    else:
        where = {"$and": conditions}

    res = get_chromadb().query(
        query_embeddings=[_normalize(text_embedding)],
        n_results=max_candidates,
        where=where,
        include=["distances", "metadatas"],
    )
    ids, dists, metas = res["ids"][0], res["distances"][0], res["metadatas"][0]

    out = [
        MatchCandidate(emb_id, round(1.0 - d, 4), round(d, 4), meta or {})
        for emb_id, d, meta in zip(ids, dists, metas)
        if d <= threshold
    ]
    out.sort(key=lambda c: c.distance)
    return out


def delete_embeddings(embedding_ids: list) -> None:
    """Chroma 임베딩 삭제. video 삭제 시 함께 호출해 정합성 유지."""
    if embedding_ids:
        get_chromadb().delete(ids=embedding_ids)


def count_embeddings() -> int:
    return get_chromadb().count()