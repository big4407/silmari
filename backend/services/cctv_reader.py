"""행정동코드별 로컬 CCTV 영상 파일 목록 — data/CCTV/{region_code}/ 스캔."""
from backend.services.storage import scan_cctv_by_region


def list_cctv_files(region_code: str) -> list[str]:
    return [str(p) for p in scan_cctv_by_region(region_code)]
