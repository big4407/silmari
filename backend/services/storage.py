import os
import shutil
import uuid
from pathlib import Path

from backend.utils.config import UPLOAD_DIR, CCTV_DATA_DIR, RESULTS_DIR


def ensure_dirs():
    for d in [UPLOAD_DIR, CCTV_DATA_DIR, RESULTS_DIR]:
        os.makedirs(d, exist_ok=True)


def save_upload(file_obj, filename: str) -> tuple[str, str]:
    ensure_dirs()
    file_id = str(uuid.uuid4())
    dest = os.path.join(UPLOAD_DIR, f"{file_id}_{filename}")
    with open(dest, "wb") as f:
        shutil.copyfileobj(file_obj, f)
    return file_id, dest


def remove_file(path: str):
    if path and os.path.exists(path):
        os.remove(path)


def scan_cctv_by_region(region_code: str) -> list[Path]:
    """행정동코드별 CCTV 영상 파일 스캔"""
    base = Path(CCTV_DATA_DIR) / region_code
    if not base.exists():
        return []
    return sorted(base.rglob("*.mp4"))
