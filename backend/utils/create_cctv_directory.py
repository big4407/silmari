"""
Region 테이블 기준으로 data/CCTV 폴더 구조를 미리 만든다.

만들어지는 구조: {cctv_data_dir}/{region_code}/{YYYYMMDD}/{cctv_serial_no}/
  - region_code: Region 테이블의 최하위(읍/면/동) 지역만 대상으로 한다 — 시/도,
    시/군/구 같은 상위 계층은 실제 CCTV가 위치하는 단위가 아니므로 제외한다.
    (판별 로직은 RegionRepository.get_leaf_codes() — region_admin_service.py의
    region 정리 로직과 동일한 리프 판별을 공유한다.)
  - YYYYMMDD: --start-date ~ --end-date(둘 다 포함) 범위의 모든 날짜.
  - cctv_serial_no: 지역마다 고정 개수(--cctv-count, 기본 3)를 CCTV001, CCTV002 ...
    형식으로 생성한다. CCTV 장비를 관리하는 마스터 테이블이 아직 없어서 1차로는
    지역당 동일 개수로 채워 넣는다 — 나중에 그런 테이블이 생기면 이 스크립트도
    거기서 실제 대수를 읽어오도록 바꿔야 한다.

사용 예:
  python -m backend.utils.create_cctv_directory --start-date 2026-07-01 --end-date 2026-07-07
  python -m backend.utils.create_cctv_directory --start-date 2026-07-01 --end-date 2026-07-01 --cctv-count 5
  python -m backend.utils.create_cctv_directory --start-date 2026-07-01 --end-date 2026-07-01 --region-code 1114052000
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

from backend.core.config import settings
from backend.db.database import SessionLocal
from backend.repositories.region_repository import RegionRepository


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _daterange(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def create_cctv_directories(
    start_date: date,
    end_date: date,
    cctv_count: int = 3,
    region_codes: list[str] | None = None,
) -> int:
    """{cctv_data_dir}/{region_code}/{YYYYMMDD}/{cctv_serial_no}/ 구조를 만든다.

    region_codes를 안 주면 Region 테이블의 최하위 지역 전체를 대상으로 한다.
    이미 있는 폴더는 건드리지 않는다(mkdir exist_ok=True).
    반환값: 새로 만든(또는 이미 있던) 폴더 개수.
    """
    base_dir = Path(settings.cctv_data_dir)

    if region_codes:
        codes = region_codes
    else:
        with SessionLocal() as db:
            codes = RegionRepository(db).get_leaf_codes()

    if not codes:
        print(
            "[CCTV 폴더 생성] 대상 지역이 없습니다 — Region 테이블이 비어있는지 확인하세요."
        )
        return 0

    created = 0
    for region_code in codes:
        for day in _daterange(start_date, end_date):
            day_str = day.strftime("%Y%m%d")
            for i in range(1, cctv_count + 1):
                cctv_serial_no = f"CCTV{i:03d}"
                folder_path = base_dir / region_code / day_str / cctv_serial_no
                folder_path.mkdir(parents=True, exist_ok=True)
                created += 1

    days = (end_date - start_date).days + 1
    print(
        f"[CCTV 폴더 생성 완료] 지역 {len(codes)}개 x 기간 {days}일 x "
        f"CCTV {cctv_count}대 = 폴더 {created}개 (base: {base_dir})"
    )
    return created


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Region 테이블 기준으로 data/CCTV 폴더 구조(지역/날짜/CCTV)를 생성한다."
    )
    parser.add_argument(
        "--start-date", required=True, type=_parse_date, help="YYYY-MM-DD"
    )
    parser.add_argument(
        "--end-date", required=True, type=_parse_date, help="YYYY-MM-DD"
    )
    parser.add_argument(
        "--cctv-count",
        type=int,
        default=3,
        help="지역마다 생성할 CCTV 폴더 개수 (기본 3 — CCTV 장비 마스터 테이블이 "
        "아직 없어 지역마다 동일한 임의 고정값을 씀)",
    )
    parser.add_argument(
        "--region-code",
        action="append",
        dest="region_codes",
        help="특정 region_code만 대상으로 하려면 반복 지정 (안 주면 Region 테이블의 "
        "최하위 지역 전체)",
    )
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    if args.end_date < args.start_date:
        raise SystemExit("--end-date는 --start-date 이후(또는 같은 날)여야 합니다.")

    create_cctv_directories(
        start_date=args.start_date,
        end_date=args.end_date,
        cctv_count=args.cctv_count,
        region_codes=args.region_codes,
    )
