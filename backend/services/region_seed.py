"""행정구역(region) 기본 시드 — CSV 우선, 없으면 시·도·시군구 최소 데이터."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.db.models import Region
from backend.services.administrative_dong_import import import_administrative_dong_csv

# 시·도 (parent_code=None)
_SIDO_ROWS: list[tuple[str, str, str]] = [
    ("11", "서울특별시", "서울"),
    ("26", "부산광역시", "부산"),
    ("27", "대구광역시", "대구"),
    ("28", "인천광역시", "인천"),
    ("29", "광주광역시", "광주"),
    ("30", "대전광역시", "대전"),
    ("36", "세종특별자치시", "세종"),
    ("31", "울산광역시", "울산"),
    ("41", "경기도", "경기"),
    ("42", "강원특별자치도", "강원"),
    ("43", "충청북도", "충북"),
    ("44", "충청남도", "충남"),
    ("45", "전북특별자치도", "전북"),
    ("46", "전라남도", "전남"),
    ("47", "경상북도", "경북"),
    ("48", "경상남도", "경남"),
    ("50", "제주특별자치도", "제주"),
]

# (parent_sido_code, region_code, full_name, specific_name)
_SIGUNGU_ROWS: list[tuple[str, str, str, str]] = [
    # 서울
    ("11", "1100", "서울특별시 종로구", "종로구"),
    ("11", "1101", "서울특별시 중구", "중구"),
    ("11", "1102", "서울특별시 용산구", "용산구"),
    ("11", "1103", "서울특별시 성동구", "성동구"),
    ("11", "1104", "서울특별시 광진구", "광진구"),
    ("11", "1105", "서울특별시 동대문구", "동대문구"),
    ("11", "1106", "서울특별시 중랑구", "중랑구"),
    ("11", "1107", "서울특별시 성북구", "성북구"),
    ("11", "1108", "서울특별시 강북구", "강북구"),
    ("11", "1109", "서울특별시 도봉구", "도봉구"),
    ("11", "1110", "서울특별시 노원구", "노원구"),
    ("11", "1111", "서울특별시 은평구", "은평구"),
    ("11", "1112", "서울특별시 서대문구", "서대문구"),
    ("11", "1113", "서울특별시 마포구", "마포구"),
    ("11", "1114", "서울특별시 양천구", "양천구"),
    ("11", "1115", "서울특별시 강서구", "강서구"),
    ("11", "1116", "서울특별시 구로구", "구로구"),
    ("11", "1117", "서울특별시 금천구", "금천구"),
    ("11", "1118", "서울특별시 영등포구", "영등포구"),
    ("11", "1119", "서울특별시 동작구", "동작구"),
    ("11", "1120", "서울특별시 관악구", "관악구"),
    ("11", "1121", "서울특별시 서초구", "서초구"),
    ("11", "1122", "서울특별시 강남구", "강남구"),
    ("11", "1123", "서울특별시 송파구", "송파구"),
    ("11", "1124", "서울특별시 강동구", "강동구"),
    # 부산
    ("26", "2600", "부산광역시 중구", "중구"),
    ("26", "2601", "부산광역시 서구", "서구"),
    ("26", "2602", "부산광역시 동구", "동구"),
    ("26", "2603", "부산광역시 영도구", "영도구"),
    ("26", "2604", "부산광역시 부산진구", "부산진구"),
    ("26", "2605", "부산광역시 동래구", "동래구"),
    ("26", "2606", "부산광역시 남구", "남구"),
    ("26", "2607", "부산광역시 북구", "북구"),
    ("26", "2608", "부산광역시 해운대구", "해운대구"),
    ("26", "2609", "부산광역시 사하구", "사하구"),
    ("26", "2610", "부산광역시 금정구", "금정구"),
    ("26", "2611", "부산광역시 강서구", "강서구"),
    ("26", "2612", "부산광역시 연제구", "연제구"),
    ("26", "2613", "부산광역시 수영구", "수영구"),
    ("26", "2614", "부산광역시 사상구", "사상구"),
    ("26", "2615", "부산광역시 기장군", "기장군"),
    # 세종
    ("36", "36010", "세종특별자치시 세종시", "세종시"),
]


def seed_regions_if_empty(db: Session) -> int:
    """region 테이블이 비어 있으면 administrative_dong.csv 또는 최소 시드."""
    count = db.scalar(select(func.count()).select_from(Region)) or 0
    if count > 0:
        return 0

    csv_path: Path = settings.administrative_dong_csv
    if csv_path.is_file():
        result = import_administrative_dong_csv(db, csv_path, replace=False)
        if not result.errors:
            return (
                result.sido_count
                + result.sigungu_count
                + result.admin_dong_count
            )
        # CSV 실패 시 아래 최소 시드로 폴백

    for code, full_name, specific in _SIDO_ROWS:
        db.add(
            Region(
                region_code=code,
                full_name=full_name,
                specific_name=specific,
                parent_code=None,
            )
        )

    for parent, code, full_name, specific in _SIGUNGU_ROWS:
        db.add(
            Region(
                region_code=code,
                full_name=full_name,
                specific_name=specific,
                parent_code=parent,
            )
        )

    db.commit()
    return len(_SIDO_ROWS) + len(_SIGUNGU_ROWS)
