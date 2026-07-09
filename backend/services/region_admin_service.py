"""행정구역 관리 — CSV export/import (service 계층)."""

from __future__ import annotations

import csv
import io
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Region, RegionLegalDong
from backend.schemas.data_integrity_schema import RegionClearResult, RegionImportResult
from backend.services.administrative_dong_import import (
    clear_all_region_data,
    import_administrative_dong_from_upload,
    is_administrative_dong_format,
    normalize_full_name,
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


def _region_chain(
    regions: dict[str, Region], admin_code: str
) -> tuple[Region | None, Region | None, Region | None]:
    admin = regions.get(admin_code)
    if admin is None:
        return None, None, None
    sigungu = regions.get(admin.parent_code) if admin.parent_code else None
    sido = (
        regions.get(sigungu.parent_code)
        if sigungu and sigungu.parent_code
        else None
    )
    return sido, sigungu, admin


class RegionAdminService:
    def __init__(self, db: Session):
        self.db = db

    def clear_all(self) -> RegionClearResult:
        return clear_all_region_data(self.db)

    def regions_to_csv(self) -> str:
        rows = list(
            self.db.scalars(select(Region).order_by(Region.region_code)).all()
        )
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
        regions = {
            r.region_code: r
            for r in self.db.scalars(select(Region).order_by(Region.region_code)).all()
        }
        legal_rows = list(
            self.db.scalars(
                select(RegionLegalDong).order_by(
                    RegionLegalDong.admin_dong_code, RegionLegalDong.legal_dong_code
                )
            ).all()
        )

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
            return import_administrative_dong_from_upload(
                self.db, io.BytesIO(raw), dry_run=dry_run
            )

        normalized_fields = {f.strip().lower(): f for f in reader.fieldnames if f}
        missing = [h for h in CSV_HEADER if h not in normalized_fields]
        if missing:
            return RegionImportResult(
                errors=[f"필수 컬럼 누락: {', '.join(missing)}"]
            )

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
                (row.get(normalized_fields["specific_name"]) or "").strip() or None
            )

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
                if self.db.get(Region, parent) is None:
                    result.errors.append(
                        f"{item['region_code']}: 상위 지역 {parent} 없음"
                    )

        if result.errors:
            return result

        pending.sort(key=lambda x: (len(x["region_code"]), x["region_code"]))

        if dry_run:
            for item in pending:
                if self.db.get(Region, item["region_code"]):
                    result.updated += 1
                else:
                    result.created += 1
            return result

        for item in pending:
            existing = self.db.get(Region, item["region_code"])
            if existing:
                existing.full_name = item["full_name"]
                existing.specific_name = item["specific_name"]
                existing.parent_code = item["parent_code"]
                result.updated += 1
            else:
                self.db.add(Region(**item))
                result.created += 1

        self.db.flush()
        return result
