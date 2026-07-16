from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw is not None else default


@dataclass(frozen=True)
class StatsSourceMap:
    """
    기존 운영 DB의 테이블·컬럼 이름을 한곳에서 매핑합니다.

    실제 프로젝트의 이름이 다르면 이 파일 또는 .env의 STATS_* 값만
    수정하면 repository/service/router 코드는 건드리지 않아도 됩니다.
    """

    # CCTV
    video_table: str = _env("STATS_VIDEO_TABLE", "video")
    video_id: str = _env("STATS_VIDEO_ID", "id")
    video_created_at: str = _env("STATS_VIDEO_CREATED_AT", "created_at")
    video_status: str = _env("STATS_VIDEO_STATUS", "status")
    video_completed_value: str = _env(
        "STATS_VIDEO_COMPLETED_VALUE",
        "COMPLETED",
    )
    video_region: str = _env("STATS_VIDEO_REGION", "region")

    video_detail_table: str = _env(
        "STATS_VIDEO_DETAIL_TABLE",
        "video_detail",
    )
    video_detail_video_id: str = _env(
        "STATS_VIDEO_DETAIL_VIDEO_ID",
        "video_id",
    )
    video_detail_track_id: str = _env(
        "STATS_VIDEO_DETAIL_TRACK_ID",
        "track_id",
    )

    # 검색
    search_table: str = _env("STATS_SEARCH_TABLE", "search")
    search_id: str = _env("STATS_SEARCH_ID", "id")
    search_created_at: str = _env(
        "STATS_SEARCH_CREATED_AT",
        "created_at",
    )
    search_type: str = _env("STATS_SEARCH_TYPE", "search_type")
    search_gender: str = _env("STATS_SEARCH_GENDER", "gender")
    search_age: str = _env("STATS_SEARCH_AGE", "age")
    search_region: str = _env(
        "STATS_SEARCH_REGION",
        "missing_location",
    )
    # 동일 실종 사건을 식별하는 컬럼. 없으면 search.id를 사용합니다.
    search_case_key: str = _env(
        "STATS_SEARCH_CASE_KEY",
        "",
    )

    analysis_table: str = _env(
        "STATS_ANALYSIS_TABLE",
        "analysis",
    )
    analysis_id: str = _env("STATS_ANALYSIS_ID", "id")
    analysis_search_id: str = _env(
        "STATS_ANALYSIS_SEARCH_ID",
        "search_id",
    )
    # 없으면 빈 문자열로 둡니다.
    analysis_processing_ms: str = _env(
        "STATS_ANALYSIS_PROCESSING_MS",
        "processing_time_ms",
    )

    analysis_detail_table: str = _env(
        "STATS_ANALYSIS_DETAIL_TABLE",
        "analysis_detail",
    )
    analysis_detail_analysis_id: str = _env(
        "STATS_ANALYSIS_DETAIL_ANALYSIS_ID",
        "analysis_id",
    )
    analysis_detail_similarity: str = _env(
        "STATS_ANALYSIS_DETAIL_SIMILARITY",
        "similarity_score",
    )

    match_threshold: float = _env_float(
        "STATS_MATCH_THRESHOLD",
        0.75,
    )
    similarity_multiplier: float = _env_float(
        "STATS_SIMILARITY_MULTIPLIER",
        100.0,
    )


SOURCE_MAP = StatsSourceMap()
