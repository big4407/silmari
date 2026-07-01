"""
탐지·검색 결과 CRUD.

[주요 함수]
  create_search_result — CCTV 분석 후 DB 저장 (routes/cctv.py)
  get_search_results   — 필터(이름·지역·안내문자) + 목록 조회
  delete_search_result — 레코드 + 연관 미디어 삭제 연동 (routes/result.py)
"""
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
