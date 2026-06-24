from backend.services.storage import scan_cctv_by_region


def list_cctv_files(region_code: str) -> list[str]:
    return [str(p) for p in scan_cctv_by_region(region_code)]
