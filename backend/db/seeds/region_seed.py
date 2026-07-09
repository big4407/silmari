"""행정구역(region) 기본 시드 — region 테이블이 비어 있을 때 administrative_dong.csv 만 적재."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.services.administrative_dong_import import import_administrative_dong_csv
from backend.repositories.region_repository import RegionRepository

logger = logging.getLogger(__name__)


def seed_regions_if_empty(db: Session) -> int:
    """region 테이블이 비어 있으면 administrative_dong.csv 를 import 한다."""
    if RegionRepository(db).count() > 0:
        return 0

    csv_path = settings.administrative_dong_csv
    result = import_administrative_dong_csv(db, csv_path, replace=False)
    if result.errors:
        logger.warning(
            "행정구역 시드 건너뜀 — %s (관리 UI 또는 CSV import로 적재하세요)",
            "; ".join(result.errors),
        )
        return 0

    seeded = result.sido_count + result.sigungu_count + result.admin_dong_count
    logger.info("행정구역 시드 완료 — %d건 (%s)", seeded, csv_path)
    return seeded
