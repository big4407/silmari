"""보존 정책 기본 시드."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.db.models import RetentionPolicy
from backend.repositories.retention_repository import RetentionRepository

_DEFAULT_POLICIES: list[tuple[str, str, str, int, str, str | None]] = [
    ("cctv_video", "CCTV·분석 영상", "video · data/CCTV", 90, "delete", "원본·분석 영상 파일"),
    (
        "clip_thumbnail",
        "탐지 클립·썸네일",
        "data/results/clips · thumbnails",
        90,
        "delete",
        "검색 결과 클립·썸네일",
    ),
    ("chroma_embedding", "Chroma 임베딩", "data/chroma", 90, "delete", "영상 삭제 시 함께 제거 필요"),
    ("search_result", "CCTV 검색 결과", "search_results", 365, "archive", "탐지 이력·클립 메타"),
    ("search_request", "검색 요청", "search", 365, "archive", "사용자 검색 요청"),
    ("login_history", "로그인 이력", "login_history", 180, "anonymize", "감사 로그"),
    ("disaster_message", "재난·안내문자", "message", 730, "archive", "외부 API 수집 메시지"),
]


def seed_retention_policies_if_empty(db: Session) -> int:
    if RetentionRepository(db).count() > 0:
        return 0

    for dtype, label, target, days, action, notes in _DEFAULT_POLICIES:
        db.add(
            RetentionPolicy(
                data_type=dtype,
                data_label=label,
                storage_target=target,
                retention_days=days,
                expiry_action=action,
                is_active=True,
                notes=notes,
            )
        )

    db.commit()
    return len(_DEFAULT_POLICIES)
