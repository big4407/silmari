from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.db.models import Region, RegionLegalDong


class RegionRepository:
    def __init__(self, db: Session):
        self.db = db

    def flush(self) -> None:
        self.db.flush()

    # ── Region 조회 ─────────────────────────────────────────────────────
    def count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Region)) or 0

    def find_codes_by_keyword(self, keyword: str) -> list[str]:
        """지역명 자유 텍스트로 region_code 를 찾는다(부분 일치).

        full_name/specific_name 둘 중 하나라도 걸리면 후보로 포함한다.
        여러 개 걸리면 전부 반환(호출 측이 $in 필터로 사용).
        """
        rows = (
            self.db.query(Region.region_code)
            .filter(
                (Region.full_name.like(f"%{keyword}%"))
                | (Region.specific_name.like(f"%{keyword}%"))
            )
            .all()
        )
        return [row[0] for row in rows]

    def get(self, region_code: str) -> Region | None:
        return self.db.get(Region, region_code)

    def list_all_ordered(self) -> list[Region]:
        return list(self.db.scalars(select(Region).order_by(Region.region_code)).all())

    def get_all_codes(self) -> list[str]:
        return list(self.db.scalars(select(Region.region_code)).all())

    def get_parent_codes(self) -> set[str]:
        """다른 지역의 parent_code 로 참조되는 코드 집합(=리프가 아닌 지역들)."""
        return set(
            self.db.scalars(
                select(Region.parent_code).where(Region.parent_code.isnot(None))
            ).all()
        )

    def get_leaf_codes(self) -> list[str]:
        """실제 CCTV가 위치하는 최하위(읍/면/동) region_code만 골라낸다.

        다른 지역의 parent_code로 참조되는 코드(시/도, 시/군/구)는 상위 계층이므로
        제외한다.
        """
        parent_codes = self.get_parent_codes()
        return [code for code in self.get_all_codes() if code not in parent_codes]

    # ── Region 변경 ─────────────────────────────────────────────────────
    def add(self, region: Region) -> Region:
        self.db.add(region)
        return region

    def update_fields(
        self, region: Region, *, full_name, specific_name, parent_code
    ) -> Region:
        region.full_name = full_name
        region.specific_name = specific_name
        region.parent_code = parent_code
        return region

    def bulk_insert(self, rows: list[dict], batch_size: int = 2000) -> None:
        for i in range(0, len(rows), batch_size):
            self.db.bulk_insert_mappings(Region, rows[i : i + batch_size])

    def delete_by_codes(self, codes: list[str]) -> None:
        if not codes:
            return
        self.db.execute(delete(Region).where(Region.region_code.in_(codes)))

    def delete_all_leaf_first(self) -> None:
        """상위-하위 self-FK 제약을 어기지 않도록 리프부터 반복 삭제한다."""
        while True:
            leaf_codes = self.get_leaf_codes()
            if not leaf_codes:
                break
            self.delete_by_codes(leaf_codes)

    # ── RegionLegalDong 조회 ────────────────────────────────────────────
    def count_legal_dongs(self) -> int:
        return self.db.scalar(select(func.count()).select_from(RegionLegalDong)) or 0

    def list_all_legal_dongs_ordered(self) -> list[RegionLegalDong]:
        return list(
            self.db.scalars(
                select(RegionLegalDong).order_by(
                    RegionLegalDong.admin_dong_code, RegionLegalDong.legal_dong_code
                )
            ).all()
        )

    def find_existing_legal_dong_keys(
        self, legal_codes: set[str], admin_codes: set[str]
    ) -> set[tuple[str, str]]:
        if not self.count_legal_dongs():
            return set()
        return set(
            self.db.execute(
                select(
                    RegionLegalDong.legal_dong_code,
                    RegionLegalDong.admin_dong_code,
                ).where(
                    RegionLegalDong.legal_dong_code.in_(legal_codes),
                    RegionLegalDong.admin_dong_code.in_(admin_codes),
                )
            ).all()
        )

    def find_existing_legal_dongs(
        self, legal_codes: set[str], admin_codes: set[str]
    ) -> dict[tuple[str, str], RegionLegalDong]:
        rows = self.db.scalars(
            select(RegionLegalDong).where(
                RegionLegalDong.legal_dong_code.in_(legal_codes),
                RegionLegalDong.admin_dong_code.in_(admin_codes),
            )
        ).all()
        return {(row.legal_dong_code, row.admin_dong_code): row for row in rows}

    # ── RegionLegalDong 변경 ────────────────────────────────────────────
    def bulk_insert_legal_dongs(self, rows: list[dict], batch_size: int = 2000) -> None:
        for i in range(0, len(rows), batch_size):
            self.db.bulk_insert_mappings(RegionLegalDong, rows[i : i + batch_size])

    def delete_all_legal_dongs(self) -> None:
        self.db.execute(delete(RegionLegalDong))

    # ── 하위지역코드 반환────────────────────────────────────────────────

    def get_video_search_region_codes(
        self,
        *,
        region_code: str,
    ) -> list[str]:
        """
        영상 검색에 사용할 지역 코드 목록을 반환한다.

        현재 지역과 부모 지역의 full_name이 같으면,
        해당 full_name으로 시작하는 모든 최하위 지역 코드를 반환한다.

        그렇지 않으면 입력된 region_code만 반환한다.
        """

        region = self.db.scalar(
            select(Region).where(
                Region.region_code == region_code,
            )
        )

        if region is None:
            return [region_code]

        if region.parent_code is None:
            return [region.region_code]

        parent = self.db.scalar(
            select(Region).where(
                Region.region_code == region.parent_code,
            )
        )

        should_expand = parent is not None and parent.full_name == region.full_name

        if not should_expand:
            return [region.region_code]

        stmt = select(Region.region_code).where(
            Region.full_name.startswith(parent.full_name),
            func.char_length(Region.region_code) == 10,
        )

        region_codes = list(self.db.scalars(stmt).all())
        
        return region_codes or [region.region_code]
