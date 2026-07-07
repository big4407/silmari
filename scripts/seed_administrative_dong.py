#!/usr/bin/env python
"""행정동 CSV → region / region_legal_dong 시드.

사용 예:
  python scripts/seed_administrative_dong.py
  python scripts/seed_administrative_dong.py --csv "D:/path/administrative_dong.csv"
  python scripts/seed_administrative_dong.py --replace
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.config import settings  # noqa: E402
from backend.db.database import Base, SessionLocal, engine  # noqa: E402
from backend.services.administrative_dong_import import (  # noqa: E402
    import_administrative_dong_csv,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="행정동 CSV 시드")
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="CSV 경로 (기본: data/raw/administrative_dong.csv)",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="기존 region 데이터 삭제 후 재적재",
    )
    parser.add_argument(
        "--copy-from",
        type=Path,
        default=None,
        help="지정 경로 CSV를 data/raw/ 로 복사 후 import",
    )
    args = parser.parse_args()

    target = settings.administrative_dong_csv
    target.parent.mkdir(parents=True, exist_ok=True)

    if args.copy_from:
        if not args.copy_from.is_file():
            print(f"원본 CSV 없음: {args.copy_from}", file=sys.stderr)
            return 1
        print(f"복사: {args.copy_from} → {target}")
        shutil.copy2(args.copy_from, target)

    csv_path = args.csv or target
    if not csv_path.is_file():
        print(f"CSV 없음: {csv_path}", file=sys.stderr)
        return 1

    print(f"DB: {settings.database_url.split('@')[-1]}")
    print(f"CSV: {csv_path}")

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        result = import_administrative_dong_csv(
            db, csv_path, replace=args.replace
        )

    if result.errors:
        for err in result.errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    print(
        f"done: csv_rows={result.csv_rows:,} "
        f"sido={result.sido_count} sigungu={result.sigungu_count} "
        f"admin_dong={result.admin_dong_count} legal_mapping={result.legal_dong_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
