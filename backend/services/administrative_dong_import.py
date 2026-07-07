"""행정동·법정동 CSV(administrative_dong.csv) → region / region_legal_dong 적재."""

from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from backend.db.models import Region, RegionLegalDong, Video
from backend.schemas.data_integrity_schema import (
    AdministrativeDongImportResult,
    RegionClearResult,
    RegionImportResult,
)

_BATCH = 2000

_ADMIN_DONG_HEADERS = frozenset(
    {"시도명", "시군구명", "행정동명", "법정동명", "행정동코드", "법정동코드"}
)

def join_region_names(*parts: str) -> str:
    """행정구역 명칭을 이어 붙일 때 연속 중복 구간은 한 번만 포함."""
    names: list[str] = []
    for part in parts:
        text = (part or "").strip()
        if not text:
            continue
        if names and names[-1] == text:
            continue
        names.append(text)
    return " ".join(names)


def normalize_full_name(full_name: str | None) -> str | None:
    """이미 조합된 full_name에서 연속 중복 토큰 제거."""
    if not full_name:
        return full_name
    return join_region_names(*full_name.split())


_SIDO_SHORT: dict[str, str] = {
    "서울특별시": "서울",
    "부산광역시": "부산",
    "대구광역시": "대구",
    "인천광역시": "인천",
    "광주광역시": "광주",
    "대전광역시": "대전",
    "세종특별자치시": "세종",
    "울산광역시": "울산",
    "경기도": "경기",
    "강원특별자치도": "강원",
    "충청북도": "충북",
    "충청남도": "충남",
    "전북특별자치도": "전북",
    "전라남도": "전남",
    "경상북도": "경북",
    "경상남도": "경남",
    "제주특별자치도": "제주",
}


def is_administrative_dong_format(fieldnames: list[str] | None) -> bool:
    if not fieldnames:
        return False
    names = set(fieldnames)
    return len(_ADMIN_DONG_HEADERS & names) >= 4


def _parse_date(value: str | None) -> date | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _scan_reader(reader: csv.DictReader) -> tuple[
    dict[str, dict],
    dict[str, dict],
    dict[str, dict],
    dict[tuple[str, str], dict],
    int,
]:
    """CSV DictReader 1회 스캔 — 시도·시군구·행정동·법정동 매핑 수집."""
    sido: dict[str, dict] = {}
    sigungu: dict[str, dict] = {}
    admin_dong: dict[str, dict] = {}
    legal_pairs: dict[tuple[str, str], dict] = {}
    row_count = 0

    for row in reader:
        row_count += 1
        sido_name = (row.get("시도명") or "").strip()
        sigungu_name = (row.get("시군구명") or "").strip()
        admin_name = (row.get("행정동명") or "").strip()
        legal_name = (row.get("법정동명") or "").strip()
        admin_code = (row.get("행정동코드") or "").strip()
        legal_code = (row.get("법정동코드") or "").strip()
        area_code = (row.get("행정구역코드") or "").strip() or None
        revised = _parse_date(row.get("개정일자"))
        link_no = (row.get("연결번호") or "").strip() or None

        if len(admin_code) < 5 or not sido_name:
            continue

        sido_code = admin_code[:2]
        sigungu_code = admin_code[:5]

        if sido_code not in sido:
            sido[sido_code] = {
                "region_code": sido_code,
                "full_name": sido_name,
                "specific_name": _SIDO_SHORT.get(sido_name, sido_name),
                "parent_code": None,
            }

        if sigungu_code not in sigungu:
            sigungu[sigungu_code] = {
                "region_code": sigungu_code,
                "full_name": join_region_names(sido_name, sigungu_name),
                "specific_name": sigungu_name,
                "parent_code": sido_code,
            }

        if admin_code not in admin_dong:
            admin_dong[admin_code] = {
                "region_code": admin_code,
                "full_name": join_region_names(sido_name, sigungu_name, admin_name),
                "specific_name": admin_name,
                "parent_code": sigungu_code,
            }

        if legal_code and admin_code:
            key = (legal_code, admin_code)
            legal_pairs[key] = {
                "legal_dong_code": legal_code,
                "admin_dong_code": admin_code,
                "legal_dong_name": legal_name or admin_name,
                "admin_area_code": area_code,
                "revised_at": revised,
                "link_no": link_no,
            }

    return sido, sigungu, admin_dong, legal_pairs, row_count


def _scan_csv(csv_path: Path) -> tuple[
    dict[str, dict],
    dict[str, dict],
    dict[str, dict],
    dict[tuple[str, str], dict],
    int,
]:
    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        return _scan_reader(csv.DictReader(fh))


def _upsert_regions(
    db: Session,
    region_rows: list[dict],
    *,
    dry_run: bool,
) -> tuple[int, int]:
    region_rows.sort(key=lambda x: (len(x["region_code"]), x["region_code"]))
    created = updated = 0

    if dry_run:
        for item in region_rows:
            if db.get(Region, item["region_code"]):
                updated += 1
            else:
                created += 1
        return created, updated

    for item in region_rows:
        existing = db.get(Region, item["region_code"])
        if existing:
            existing.full_name = item["full_name"]
            existing.specific_name = item["specific_name"]
            existing.parent_code = item["parent_code"]
            updated += 1
        else:
            db.add(Region(**item))
            created += 1

    db.flush()
    return created, updated


def _upsert_legal_dongs(
    db: Session,
    legal_rows: list[dict],
    *,
    dry_run: bool,
) -> tuple[int, int]:
    created = updated = 0
    if not legal_rows:
        return created, updated

    legal_codes = {r["legal_dong_code"] for r in legal_rows}
    admin_codes = {r["admin_dong_code"] for r in legal_rows}
    existing_keys: set[tuple[str, str]] = set()
    if db.scalar(select(func.count()).select_from(RegionLegalDong)):
        existing_keys = set(
            db.execute(
                select(
                    RegionLegalDong.legal_dong_code,
                    RegionLegalDong.admin_dong_code,
                ).where(
                    RegionLegalDong.legal_dong_code.in_(legal_codes),
                    RegionLegalDong.admin_dong_code.in_(admin_codes),
                )
            ).all()
        )

    if dry_run:
        for item in legal_rows:
            key = (item["legal_dong_code"], item["admin_dong_code"])
            if key in existing_keys:
                updated += 1
            else:
                created += 1
        return created, updated

    existing_map: dict[tuple[str, str], RegionLegalDong] = {}
    if existing_keys:
        rows = db.scalars(
            select(RegionLegalDong).where(
                RegionLegalDong.legal_dong_code.in_(legal_codes),
                RegionLegalDong.admin_dong_code.in_(admin_codes),
            )
        ).all()
        existing_map = {
            (row.legal_dong_code, row.admin_dong_code): row for row in rows
        }

    new_rows: list[dict] = []
    for item in legal_rows:
        key = (item["legal_dong_code"], item["admin_dong_code"])
        existing = existing_map.get(key)
        if existing:
            existing.legal_dong_name = item["legal_dong_name"]
            existing.admin_area_code = item["admin_area_code"]
            existing.revised_at = item["revised_at"]
            existing.link_no = item["link_no"]
            updated += 1
        else:
            new_rows.append(item)

    for i in range(0, len(new_rows), _BATCH):
        db.bulk_insert_mappings(RegionLegalDong, new_rows[i : i + _BATCH])
    created = len(new_rows)
    db.flush()
    return created, updated


def import_administrative_dong_from_upload(
    db: Session,
    file: BinaryIO,
    *,
    dry_run: bool = False,
) -> RegionImportResult:
    """업로드된 administrative_dong.csv — region·region_legal_dong upsert."""
    result = RegionImportResult(format="administrative_dong")
    raw = file.read()
    text = io.StringIO(raw.decode("utf-8-sig"))
    reader = csv.DictReader(text)

    if not is_administrative_dong_format(reader.fieldnames):
        result.errors.append("administrative_dong.csv 형식이 아닙니다.")
        return result

    sido, sigungu, admin_dong, legal_pairs, row_count = _scan_reader(reader)
    result.csv_rows = row_count

    region_rows = list(sido.values()) + list(sigungu.values()) + list(admin_dong.values())
    legal_rows = list(legal_pairs.values())

    created, updated = _upsert_regions(db, region_rows, dry_run=dry_run)
    result.created = created
    result.updated = updated

    legal_created, legal_updated = _upsert_legal_dongs(
        db, legal_rows, dry_run=dry_run
    )
    result.legal_dong_created = legal_created
    result.legal_dong_updated = legal_updated
    return result


def _clear_region_data(db: Session) -> None:
    db.execute(delete(RegionLegalDong))
    while True:
        parent_codes = set(
            db.scalars(
                select(Region.parent_code).where(Region.parent_code.isnot(None))
            ).all()
        )
        leaf_codes = [
            code
            for code in db.scalars(select(Region.region_code)).all()
            if code not in parent_codes
        ]
        if not leaf_codes:
            break
        db.execute(delete(Region).where(Region.region_code.in_(leaf_codes)))
    db.flush()


def clear_all_region_data(db: Session) -> RegionClearResult:
    """region·region_legal_dong 전체 삭제 (video.region_code 는 NULL 처리)."""
    result = RegionClearResult(
        region_deleted=db.scalar(select(func.count()).select_from(Region)) or 0,
        legal_dong_deleted=db.scalar(select(func.count()).select_from(RegionLegalDong))
        or 0,
    )
    unlink = db.execute(
        update(Video).where(Video.region_code.isnot(None)).values(region_code=None)
    )
    result.video_unlinked = unlink.rowcount or 0
    _clear_region_data(db)
    return result


def import_administrative_dong_csv(
    db: Session,
    csv_path: Path | str,
    *,
    replace: bool = False,
    commit: bool = True,
) -> AdministrativeDongImportResult:
    """administrative_dong.csv 를 region·region_legal_dong 테이블에 적재."""
    path = Path(csv_path)
    result = AdministrativeDongImportResult()

    if not path.is_file():
        result.errors.append(f"CSV 파일 없음: {path}")
        return result

    existing = db.scalar(select(func.count()).select_from(Region)) or 0
    if existing > 0 and not replace:
        result.errors.append(
            f"region 테이블에 {existing}건 존재 — 덮어쓰려면 replace=True"
        )
        return result

    if replace and existing > 0:
        video_refs = db.scalar(
            select(func.count()).select_from(Video).where(Video.region_code.isnot(None))
        ) or 0
        if video_refs > 0:
            result.errors.append(
                f"video.region_code 참조 {video_refs}건 — region 전체 삭제 불가"
            )
            return result
        _clear_region_data(db)

    sido, sigungu, admin_dong, legal_pairs, row_count = _scan_csv(path)
    result.csv_rows = row_count

    region_rows = list(sido.values()) + list(sigungu.values()) + list(admin_dong.values())
    for i in range(0, len(region_rows), _BATCH):
        db.bulk_insert_mappings(Region, region_rows[i : i + _BATCH])

    legal_rows = list(legal_pairs.values())
    for i in range(0, len(legal_rows), _BATCH):
        db.bulk_insert_mappings(RegionLegalDong, legal_rows[i : i + _BATCH])

    if commit:
        db.commit()

    result.sido_count = len(sido)
    result.sigungu_count = len(sigungu)
    result.admin_dong_count = len(admin_dong)
    result.legal_dong_count = len(legal_pairs)
    return result


def repair_region_full_names(
    db: Session,
    csv_path: Path | str | None = None,
    *,
    commit: bool = True,
) -> int:
    """administrative_dong.csv 기준으로 region.full_name 재계산·갱신."""
    from backend.core.config import settings

    path = Path(csv_path) if csv_path else settings.administrative_dong_csv
    if not path.is_file():
        return 0

    sido, sigungu, admin_dong, _, _ = _scan_csv(path)
    region_rows = list(sido.values()) + list(sigungu.values()) + list(admin_dong.values())
    updated = 0
    for item in region_rows:
        existing = db.get(Region, item["region_code"])
        if existing is None:
            continue
        if existing.full_name != item["full_name"]:
            existing.full_name = item["full_name"]
            updated += 1

    if commit:
        db.commit()
    else:
        db.flush()
    return updated
