"""행정구역 관리 — CSV export/import, administrative_dong.csv 적재 (service 계층).

CSV 파싱·스캔(순수 함수, DB 접근 없음)과 실제 조회/upsert/삭제
(RegionAdminService, self.repository를 통해서만 DB 접근)를 한 파일에 모아둔다 —
전부 "지역 관리"라는 하나의 도메인이라 두 클래스로 나눌 이유가 없었다
(RegionAdminService가 별도 클래스를 얇게 감싸기만 하던 걸 병합).
"""

from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path
from typing import BinaryIO

from sqlalchemy.orm import Session

from backend.db.models import Region, RegionLegalDong
from backend.repositories.region_repository import RegionRepository
from backend.repositories.video_repository import VideoRepository
from backend.schemas.region_schema import (
    AdministrativeDongImportResult,
    RegionClearResult,
    RegionImportResult,
)

_BATCH = 2000

_ADMIN_DONG_HEADERS = frozenset(
    {"시도명", "시군구명", "행정동명", "법정동명", "행정동코드", "법정동코드"}
)

CSV_HEADER = ("region_code", "full_name", "specific_name", "parent_code")
ADMIN_DONG_HEADER = (
    "시도명",
    "시군구명",
    "행정동명",
    "법정동명",
    "행정구역코드",
    "행정동코드",
    "법정동코드",
    "개정일자",
    "연결번호",
)


# ── 순수 함수 (DB 접근 없음) — CSV 파싱 ─────────────────────────────────────
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


def _scan_reader(
    reader: csv.DictReader,
) -> tuple[
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


def _scan_csv(
    csv_path: Path,
) -> tuple[
    dict[str, dict],
    dict[str, dict],
    dict[str, dict],
    dict[tuple[str, str], dict],
    int,
]:
    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        return _scan_reader(csv.DictReader(fh))


def _region_chain(
    regions: dict[str, Region], admin_code: str
) -> tuple[Region | None, Region | None, Region | None]:
    admin = regions.get(admin_code)
    if admin is None:
        return None, None, None
    sigungu = regions.get(admin.parent_code) if admin.parent_code else None
    sido = regions.get(sigungu.parent_code) if sigungu and sigungu.parent_code else None
    return sido, sigungu, admin


# ── DB 접근 (RegionAdminService, self.repository 를 통해서만) ──────────────
class RegionAdminService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = RegionRepository(db)
        self.video_repository = VideoRepository(db)

    # ── 조회/내보내기 ──────────────────────────────────────────────────
    def regions_to_csv(self) -> str:
        rows = self.repository.list_all_ordered()
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(CSV_HEADER)
        for r in rows:
            writer.writerow(
                [
                    r.region_code,
                    r.full_name or "",
                    r.specific_name or "",
                    r.parent_code or "",
                ]
            )
        return buf.getvalue()

    def administrative_dong_to_csv(self) -> str:
        regions = {r.region_code: r for r in self.repository.list_all_ordered()}
        legal_rows = self.repository.list_all_legal_dongs_ordered()

        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(ADMIN_DONG_HEADER)

        if legal_rows:
            for row in legal_rows:
                sido, sigungu, admin = _region_chain(regions, row.admin_dong_code)
                writer.writerow(
                    [
                        (sido.full_name if sido else ""),
                        (sigungu.specific_name if sigungu else ""),
                        (admin.specific_name if admin else ""),
                        row.legal_dong_name,
                        row.admin_area_code or "",
                        row.admin_dong_code,
                        row.legal_dong_code,
                        row.revised_at.isoformat() if row.revised_at else "",
                        row.link_no or "",
                    ]
                )
        else:
            for code, admin in regions.items():
                if len(code) != 10:
                    continue
                sido, sigungu, _ = _region_chain(regions, code)
                writer.writerow(
                    [
                        (sido.full_name if sido else ""),
                        (sigungu.specific_name if sigungu else ""),
                        admin.specific_name or "",
                        admin.specific_name or "",
                        "",
                        code,
                        code,
                        "",
                        "",
                    ]
                )

        return buf.getvalue()

    # ── CSV import (region 포맷 / administrative_dong 포맷 공용 진입점) ──
    def import_from_csv(
        self,
        file: BinaryIO,
        *,
        dry_run: bool = False,
    ) -> RegionImportResult:
        raw = file.read()
        text = io.StringIO(raw.decode("utf-8-sig"))
        reader = csv.DictReader(text)

        if not reader.fieldnames:
            return RegionImportResult(errors=["CSV 헤더가 없습니다."])

        if is_administrative_dong_format(reader.fieldnames):
            return self.import_administrative_dong_from_upload(
                io.BytesIO(raw), dry_run=dry_run
            )

        normalized_fields = {f.strip().lower(): f for f in reader.fieldnames if f}
        missing = [h for h in CSV_HEADER if h not in normalized_fields]
        if missing:
            return RegionImportResult(errors=[f"필수 컬럼 누락: {', '.join(missing)}"])

        result = RegionImportResult(format="region")
        pending: list[dict] = []

        text.seek(0)
        reader = csv.DictReader(text)
        for line_no, row in enumerate(reader, start=2):
            code = (row.get(normalized_fields["region_code"]) or "").strip()
            if not code:
                result.skipped += 1
                continue

            parent = (row.get(normalized_fields["parent_code"]) or "").strip() or None
            full_name = normalize_full_name(
                (row.get(normalized_fields["full_name"]) or "").strip() or None
            )
            specific = (
                row.get(normalized_fields["specific_name"]) or ""
            ).strip() or None

            if not full_name and not specific:
                result.errors.append(f"{line_no}행: 명칭이 비어 있습니다 ({code})")
                continue

            pending.append(
                {
                    "region_code": code,
                    "full_name": full_name,
                    "specific_name": specific,
                    "parent_code": parent,
                }
            )

        codes_in_file = {p["region_code"] for p in pending}
        for item in pending:
            parent = item["parent_code"]
            if parent and parent not in codes_in_file:
                if self.repository.get(parent) is None:
                    result.errors.append(
                        f"{item['region_code']}: 상위 지역 {parent} 없음"
                    )

        if result.errors:
            return result

        pending.sort(key=lambda x: (len(x["region_code"]), x["region_code"]))

        if dry_run:
            for item in pending:
                if self.repository.get(item["region_code"]):
                    result.updated += 1
                else:
                    result.created += 1
            return result

        for item in pending:
            existing = self.repository.get(item["region_code"])
            if existing:
                self.repository.update_fields(
                    existing,
                    full_name=item["full_name"],
                    specific_name=item["specific_name"],
                    parent_code=item["parent_code"],
                )
                result.updated += 1
            else:
                self.repository.add(Region(**item))
                result.created += 1

        self.repository.flush()
        return result

    # ── administrative_dong.csv 전용 적재 ────────────────────────────────
    def upsert_regions(
        self, region_rows: list[dict], *, dry_run: bool
    ) -> tuple[int, int]:
        region_rows = sorted(
            region_rows, key=lambda x: (len(x["region_code"]), x["region_code"])
        )
        created = updated = 0

        if dry_run:
            for item in region_rows:
                if self.repository.get(item["region_code"]):
                    updated += 1
                else:
                    created += 1
            return created, updated

        for item in region_rows:
            existing = self.repository.get(item["region_code"])
            if existing:
                self.repository.update_fields(
                    existing,
                    full_name=item["full_name"],
                    specific_name=item["specific_name"],
                    parent_code=item["parent_code"],
                )
                updated += 1
            else:
                self.repository.add(Region(**item))
                created += 1

        self.repository.flush()
        return created, updated

    def upsert_legal_dongs(
        self, legal_rows: list[dict], *, dry_run: bool
    ) -> tuple[int, int]:
        created = updated = 0
        if not legal_rows:
            return created, updated

        legal_codes = {r["legal_dong_code"] for r in legal_rows}
        admin_codes = {r["admin_dong_code"] for r in legal_rows}
        existing_keys = self.repository.find_existing_legal_dong_keys(
            legal_codes, admin_codes
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
            existing_map = self.repository.find_existing_legal_dongs(
                legal_codes, admin_codes
            )

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

        self.repository.bulk_insert_legal_dongs(new_rows, batch_size=_BATCH)
        created = len(new_rows)
        self.repository.flush()
        return created, updated

    def import_administrative_dong_from_upload(
        self,
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

        region_rows = (
            list(sido.values()) + list(sigungu.values()) + list(admin_dong.values())
        )
        legal_rows = list(legal_pairs.values())

        created, updated = self.upsert_regions(region_rows, dry_run=dry_run)
        result.created = created
        result.updated = updated

        legal_created, legal_updated = self.upsert_legal_dongs(
            legal_rows, dry_run=dry_run
        )
        result.legal_dong_created = legal_created
        result.legal_dong_updated = legal_updated
        return result

    def clear_all(self) -> RegionClearResult:
        """region·region_legal_dong 전체 삭제 (video.region_code 는 NULL 처리)."""
        result = RegionClearResult(
            region_deleted=self.repository.count(),
            legal_dong_deleted=self.repository.count_legal_dongs(),
        )
        result.video_unlinked = self.video_repository.unlink_all_region_codes()
        self.repository.delete_all_legal_dongs()
        self.repository.delete_all_leaf_first()
        self.repository.flush()
        return result

    def import_administrative_dong_csv(
        self,
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

        existing = self.repository.count()
        if existing > 0 and not replace:
            result.errors.append(
                f"region 테이블에 {existing}건 존재 — 덮어쓰려면 replace=True"
            )
            return result

        if replace and existing > 0:
            video_refs = self.video_repository.count_with_region_code()
            if video_refs > 0:
                result.errors.append(
                    f"video.region_code 참조 {video_refs}건 — region 전체 삭제 불가"
                )
                return result
            self.repository.delete_all_legal_dongs()
            self.repository.delete_all_leaf_first()

        sido, sigungu, admin_dong, legal_pairs, row_count = _scan_csv(path)
        result.csv_rows = row_count

        region_rows = (
            list(sido.values()) + list(sigungu.values()) + list(admin_dong.values())
        )
        self.repository.bulk_insert(region_rows, batch_size=_BATCH)

        legal_rows = list(legal_pairs.values())
        self.repository.bulk_insert_legal_dongs(legal_rows, batch_size=_BATCH)

        if commit:
            self.db.commit()

        result.sido_count = len(sido)
        result.sigungu_count = len(sigungu)
        result.admin_dong_count = len(admin_dong)
        result.legal_dong_count = len(legal_pairs)
        return result

    def repair_region_full_names(
        self,
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
        region_rows = (
            list(sido.values()) + list(sigungu.values()) + list(admin_dong.values())
        )
        updated = 0
        for item in region_rows:
            existing = self.repository.get(item["region_code"])
            if existing is None:
                continue
            if existing.full_name != item["full_name"]:
                existing.full_name = item["full_name"]
                updated += 1

        if commit:
            self.db.commit()
        else:
            self.repository.flush()
        return updated
