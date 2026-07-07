import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text

from backend.db.database import SessionLocal
from backend.services.administrative_dong_import import repair_region_full_names

CODES = ("11", "11000", "1100000000", "11110", "1111000000", "1111051500")

db = SessionLocal()
try:
    updated = repair_region_full_names(db)
    print(f"updated: {updated}")
    rows = db.execute(
        text(
            "SELECT region_code, full_name, specific_name FROM region "
            "WHERE region_code IN :codes ORDER BY region_code"
        ),
        {"codes": CODES},
    ).fetchall()
    for row in rows:
        print(row)
finally:
    db.close()
