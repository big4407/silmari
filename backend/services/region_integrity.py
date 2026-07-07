"""행정구역·연관 테이블 정합성 검사."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Region, Video
from backend.schemas.data_integrity_schema import IntegrityCheckResult


def _status(count: int, warn_threshold: int = 0) -> str:
    if count == 0:
        return "ok"
    if count <= warn_threshold:
        return "warn"
    return "error"


def _clip(items: list[str], sample_limit: int | None) -> list[str]:
    if sample_limit is None:
        return items
    return items[:sample_limit]


def run_region_integrity_checks(
    db: Session, *, sample_limit: int | None = 8
) -> list[IntegrityCheckResult]:
    checks: list[IntegrityCheckResult] = []

    all_codes = set(db.scalars(select(Region.region_code)).all())

    # 1) parent_code → 없는 상위 지역
    if all_codes:
        orphan_parents = list(
            db.scalars(
                select(Region.region_code).where(
                    Region.parent_code.isnot(None),
                    ~Region.parent_code.in_(all_codes),
                )
            ).all()
        )
    else:
        orphan_parents = list(
            db.scalars(
                select(Region.region_code).where(Region.parent_code.isnot(None))
            ).all()
        )
    checks.append(
        IntegrityCheckResult(
            check_id="region_orphan_parent",
            label="끊긴 상위 참조",
            target="region",
            description="parent_code가 region 테이블에 존재하지 않음",
            status=_status(len(orphan_parents)),
            issue_count=len(orphan_parents),
            samples=_clip(orphan_parents, sample_limit),
        )
    )

    # 2) 자기 자신을 parent로 지정
    self_parents = list(
        db.scalars(
            select(Region.region_code).where(
                Region.parent_code == Region.region_code
            )
        ).all()
    )
    checks.append(
        IntegrityCheckResult(
            check_id="region_self_parent",
            label="자기 참조",
            target="region",
            description="parent_code가 자신의 region_code와 동일",
            status=_status(len(self_parents)),
            issue_count=len(self_parents),
            samples=_clip(self_parents, sample_limit),
        )
    )

    # 3) 계층 순환
    parent_map = {
        code: parent
        for code, parent in db.execute(
            select(Region.region_code, Region.parent_code)
        ).all()
    }
    cyclic: list[str] = []
    for code in parent_map:
        seen: set[str] = set()
        cursor: str | None = code
        while cursor:
            if cursor in seen:
                cyclic.append(code)
                break
            seen.add(cursor)
            cursor = parent_map.get(cursor)
    checks.append(
        IntegrityCheckResult(
            check_id="region_cycle",
            label="계층 순환",
            target="region",
            description="parent_code 체인에 순환 참조 존재",
            status=_status(len(cyclic)),
            issue_count=len(cyclic),
            samples=_clip(cyclic, sample_limit),
        )
    )

    # 4) 명칭 누락
    missing_names = list(
        db.scalars(
            select(Region.region_code).where(
                Region.full_name.is_(None),
                Region.specific_name.is_(None),
            )
        ).all()
    )
    checks.append(
        IntegrityCheckResult(
            check_id="region_missing_name",
            label="명칭 누락",
            target="region",
            description="full_name·specific_name 모두 비어 있음",
            status=_status(len(missing_names), warn_threshold=5),
            issue_count=len(missing_names),
            samples=_clip(missing_names, sample_limit),
        )
    )

    # 5) video → 없는 region_code
    if all_codes:
        orphan_videos = [
            f"video#{vid}:{rcode}"
            for vid, rcode in db.execute(
                select(Video.id, Video.region_code).where(
                    Video.region_code.isnot(None),
                    ~Video.region_code.in_(all_codes),
                )
            ).all()
        ]
    else:
        orphan_videos = [
            f"video#{vid}:{rcode}"
            for vid, rcode in db.execute(
                select(Video.id, Video.region_code).where(
                    Video.region_code.isnot(None)
                )
            ).all()
        ]
    checks.append(
        IntegrityCheckResult(
            check_id="video_orphan_region",
            label="영상 지역 코드",
            target="video",
            description="video.region_code가 region에 없음",
            status=_status(len(orphan_videos)),
            issue_count=len(orphan_videos),
            samples=_clip(orphan_videos, sample_limit),
        )
    )

    return checks


def run_integrity_suite(
    db: Session, *, sample_limit: int | None = 8
) -> tuple[list[IntegrityCheckResult], int]:
    from backend.services.relational_integrity import (
        run_auth_integrity_checks,
        run_search_integrity_checks,
    )

    checks = [
        *run_region_integrity_checks(db, sample_limit=sample_limit),
        *run_auth_integrity_checks(db, sample_limit=sample_limit),
        *run_search_integrity_checks(db, sample_limit=sample_limit),
    ]
    total = sum(c.issue_count for c in checks if c.status != "ok")
    return checks, total


def find_integrity_check(
    db: Session, check_id: str, *, sample_limit: int | None = None
) -> IntegrityCheckResult | None:
    """check_id에 해당하는 검사 1건. sample_limit=None이면 전체 이슈 목록."""
    checks, _ = run_integrity_suite(db, sample_limit=sample_limit)
    for check in checks:
        if check.check_id == check_id:
            return check
    return None
