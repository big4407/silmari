"""
탐지 결과(SearchResult) 조회·삭제·미디어 경로.

[호출] routers/result.py
[데이터] db/crud (search_result) · data/results/ 클립·썸네일
"""
import json
import os
from typing import Optional

from fastapi import HTTPException

from backend.core.config import settings
from backend.db import crud
from backend.services.cctv_reader import list_cctv_files
from backend.services.sms_receiver import fetch_missing_persons, fetch_missing_persons_dummy
from backend.services.storage import remove_file

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


def _serialize_history_item(record) -> dict:
    return {
        "id": record.id,
        "person_name": record.person_name,
        "person_age": record.person_age,
        "region": record.region or "-",
        "alert_text": record.alert_text,
        "video_filename": record.video_filename,
        "best_confidence": record.best_confidence,
        "description": record.description or "",
        "thumbnail_url": f"{MEDIA_BASE}/thumbnails/{record.thumbnail_filename}",
        "sms_info": json.loads(record.sms_info_json or "{}"),
        "candidate_count": len(json.loads(record.clips_json or "[]")),
        "created_at": record.created_at.isoformat(),
    }


def _remove_result_media(record) -> None:
    if record.thumbnail_filename:
        remove_file(
            os.path.join(settings.results_dir, "thumbnails", record.thumbnail_filename)
        )
    for clip in json.loads(record.clips_json or "[]"):
        filename = clip.get("filename")
        if filename:
            remove_file(os.path.join(settings.results_dir, "clips", filename))


class DetectionResultService:
    async def list_missing_persons(
        self,
        *,
        name: Optional[str] = None,
        age: Optional[int] = None,
        dummy: bool = False,
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

    def list_cctv_files(self, region_code: str) -> dict:
        return {"region_code": region_code, "files": list_cctv_files(region_code)}

    def list_history(
        self,
        *,
        person_name: Optional[str] = None,
        region: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        records = crud.get_search_results(
            person_name=person_name,
            region=region,
            limit=limit,
        )
        return [_serialize_history_item(r) for r in records]

    def list_results(
        self,
        *,
        person_name: Optional[str] = None,
        alert_text: Optional[str] = None,
        region: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        records = crud.get_search_results(
            person_name=person_name,
            alert_text=alert_text,
            region=region,
            limit=limit,
        )
        return [_serialize_search_result(r) for r in records]

    def get_result(self, result_id: int) -> dict:
        record = crud.get_search_result_by_id(result_id)
        if not record:
            raise HTTPException(status_code=404, detail="검색 결과를 찾을 수 없습니다.")
        return _serialize_search_result(record)

    def delete_result(self, result_id: int) -> dict:
        record = crud.delete_search_result(result_id)
        if not record:
            raise HTTPException(status_code=404, detail="검색 결과를 찾을 수 없습니다.")
        _remove_result_media(record)
        return {"ok": True, "deleted_id": result_id}

    def delete_results(
        self,
        *,
        person_name: Optional[str] = None,
        alert_text: Optional[str] = None,
        region: Optional[str] = None,
    ) -> dict:
        records = crud.delete_search_results(
            person_name=person_name,
            alert_text=alert_text,
            region=region,
        )
        for record in records:
            _remove_result_media(record)
        return {"ok": True, "deleted_count": len(records)}

    def resolve_thumbnail_path(self, filename: str) -> str:
        path = os.path.join(settings.results_dir, "thumbnails", filename)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="썸네일 없음")
        return path

    def resolve_clip_path(self, filename: str) -> str:
        path = os.path.join(settings.results_dir, "clips", filename)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="클립 없음")
        return path
