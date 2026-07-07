"""
탐지 결과·검색 이력·미디어 제공 API.

[조회] GET / — SearchResult 목록 (구: /search)
[미디어] /media/thumbnails, /media/clips — data/results/ 정적 파일
[삭제] DELETE /{id} — DB 레코드 + 디스크 클립·썸네일 함께 제거
"""
import json
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.core.config import settings
from backend.db.crud import (
    get_search_results,
    get_search_result_by_id,
    delete_search_result,
    delete_search_results,
)
from backend.services.sms_receiver import fetch_missing_persons, fetch_missing_persons_dummy
from backend.services.storage import remove_file

router = APIRouter()

MEDIA_BASE = "/api/detection-results/media"


def _serialize_search_result(record) -> dict:
    clips = json.loads(record.clips_json or "[]")
    sms_info = json.loads(record.sms_info_json or "{}")

    return {
        "id": record.id,
        "person_name": record.person_name,
        "person_age": record.person_age,
        "region": record.region or "-",
        "video_filename": record.video_filename,
        "thumbnail_url": f"{MEDIA_BASE}/thumbnails/{record.thumbnail_filename}",
        "best_confidence": record.best_confidence,
        "best_timestamp_sec": record.best_timestamp_sec,
        "description": record.description or "",
        "clips": [
            {
                **clip,
                "url": f"{MEDIA_BASE}/clips/{clip['filename']}",
                **(
                    {
                        "thumbnail_url": (
                            f"{MEDIA_BASE}/thumbnails/{clip['thumbnail_filename']}"
                        ),
                    }
                    if clip.get("thumbnail_filename")
                    else {}
                ),
            }
            for clip in clips
        ],
        "candidate_count": len(clips),
        "sms_info": sms_info,
        "alert_text": record.alert_text,
        "created_at": record.created_at.isoformat(),
    }


@router.get("/list")
async def missing_list(
    name: Optional[str] = None, age: Optional[int] = None, dummy: bool = False
):
    if dummy:
        return fetch_missing_persons_dummy()
    if name is None and age is None:
        return await fetch_missing_persons()
    if age is None:
        return await fetch_missing_persons(name=name)
    if name is None:
        return await fetch_missing_persons(age=age)
    return await fetch_missing_persons(name=name, age=age)


@router.get("")
@router.get("/search")
def search_results(
    person_name: Optional[str] = None,
    alert_text: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = 50,
):
    records = get_search_results(
        person_name=person_name,
        alert_text=alert_text,
        region=region,
        limit=limit,
    )
    return [_serialize_search_result(r) for r in records]


@router.get("/{result_id}")
@router.get("/search/{result_id}")
def search_result_detail(result_id: int):
    record = get_search_result_by_id(result_id)
    if not record:
        raise HTTPException(status_code=404, detail="검색 결과를 찾을 수 없습니다.")
    return _serialize_search_result(record)


def _remove_result_media(record) -> None:
    if record.thumbnail_filename:
        remove_file(os.path.join(settings.results_dir, "thumbnails", record.thumbnail_filename))
    for clip in json.loads(record.clips_json or "[]"):
        filename = clip.get("filename")
        if filename:
            remove_file(os.path.join(settings.results_dir, "clips", filename))


@router.delete("/{result_id}")
@router.delete("/search/{result_id}")
def delete_search_result_endpoint(result_id: int):
    record = delete_search_result(result_id)
    if not record:
        raise HTTPException(status_code=404, detail="검색 결과를 찾을 수 없습니다.")
    _remove_result_media(record)
    return {"ok": True, "deleted_id": result_id}


@router.delete("")
@router.delete("/search")
def delete_search_results_endpoint(
    person_name: Optional[str] = None,
    alert_text: Optional[str] = None,
    region: Optional[str] = None,
):
    records = delete_search_results(
        person_name=person_name,
        alert_text=alert_text,
        region=region,
    )
    for record in records:
        _remove_result_media(record)
    return {"ok": True, "deleted_count": len(records)}


@router.get("/media/thumbnails/{filename}")
def get_thumbnail(filename: str):
    path = os.path.join(settings.results_dir, "thumbnails", filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="썸네일 없음")
    return FileResponse(path, media_type="image/jpeg")


@router.get("/media/clips/{filename}")
def get_clip(filename: str):
    path = os.path.join(settings.results_dir, "clips", filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="클립 없음")
    return FileResponse(
        path,
        media_type="video/mp4",
        headers={"Accept-Ranges": "bytes"},
    )
