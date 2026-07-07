"""
개발용 검색 결과 시드 — DB + 데모 영상·클립·후보 썸네일 생성.

검색 결과 페이지 UI 확인용. ENVIRONMENT=development 에서만 호출 가능.
"""
from __future__ import annotations

from backend.db.crud import create_search_result

DEMO_ALERT_TEXT = (
    "실종자 홍길동(남, 65세)은 검은 점퍼와 파란 바지를 착용하고 있습니다. "
    "2026년 7월 2일 14시경 서울특별시 강남구 역삼동 인근에서 보행 중 실종되었습니다."
)

DEMO_SMS_INFO = {
    "name": "홍길동",
    "age": 65,
    "gender": "남",
    "clothes": "검은, 파란",
    "clothes_part": "both",
    "raw_text": DEMO_ALERT_TEXT,
}

DEMO_ITEMS = [
    {
        "video_filename": "demo_cctv_역삼역_01.mp4",
        "region": "서울특별시 강남구",
        "description": "demo_cctv_역삼역_01.mp4 · 후보 3명 탐지",
    },
    {
        "video_filename": "demo_cctv_테헤란로_02.mp4",
        "region": "서울특별시 강남구",
        "description": "demo_cctv_테헤란로_02.mp4 · 후보 3명 탐지",
    },
    {
        "video_filename": "demo_cctv_강남대로_03.mp4",
        "region": "서울특별시 강남구",
        "description": "demo_cctv_강남대로_03.mp4 · 후보 3명 탐지",
    },
]


def seed_demo_search_results() -> dict:
    from backend.services.demo_media import build_demo_result_media

    created_ids: list[int] = []
    total_candidates = 0

    for item in DEMO_ITEMS:
        media = build_demo_result_media(item["video_filename"])
        total_candidates += media["candidate_count"]

        record = create_search_result(
            alert_text=DEMO_ALERT_TEXT,
            person_name=DEMO_SMS_INFO["name"],
            person_age=DEMO_SMS_INFO["age"],
            region=item["region"],
            video_filename=item["video_filename"],
            thumbnail_filename=media["thumbnail_filename"],
            best_confidence=media["best_confidence"],
            best_timestamp_sec=media["best_timestamp_sec"],
            clips=media["clips"],
            sms_info=DEMO_SMS_INFO,
            description=item["description"],
        )
        created_ids.append(record.id)

    return {
        "ok": True,
        "created_ids": created_ids,
        "count": len(created_ids),
        "total_candidates": total_candidates,
        "alert_text": DEMO_ALERT_TEXT,
        "region": "서울특별시 강남구",
        "sms_info": DEMO_SMS_INFO,
    }
