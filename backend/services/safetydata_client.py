"""
재난안전데이터 API 클라이언트 + 로컬 캐시.

[캐시] backend/data/alerts_cache/ — TTL 15분, force_refresh/cache_only 지원
[필터] missing_only 시 실종 관련 안내문자만 반환
[호출] routes/disaster_alerts.py → Dashboard.jsx
"""
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx

from backend.core.config import settings, BACKEND_DIR

_CACHE: dict = {}
CACHE_TTL_SEC = 900
CACHE_DIR = BACKEND_DIR / "data" / "alerts_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _map_alert(raw: dict) -> dict:
    return {
        "id": str(raw.get("SN") or raw.get("sn") or ""),
        "msg_cn": raw.get("MSG_CN") or raw.get("msg_cn") or "",
        "rcptn_rgn_nm": (raw.get("RCPTN_RGN_NM") or raw.get("rcptn_rgn_nm") or "").strip(),
        "crt_dt": raw.get("CRT_DT") or raw.get("crt_dt") or "",
        "emrg_step_nm": raw.get("EMRG_STEP_NM") or raw.get("emrg_step_nm") or "",
        "dst_se_nm": raw.get("DST_SE_NM") or raw.get("dst_se_nm") or "",
        "reg_ymd": raw.get("REG_YMD") or raw.get("reg_ymd") or "",
    }


def _parse_item_ymd(item: dict) -> Optional[str]:
    raw = item.get("crt_dt") or item.get("reg_ymd") or ""
    digits = re.sub(r"\D", "", str(raw))
    return digits[:8] if len(digits) >= 8 else None


MISSING_PERSON_KEYWORDS = (
    "실종",
    "실종자",
    "실종아",
    "실종경보",
    "실종장소",
    "실종신고",
)


def _is_missing_person_alert(item: dict) -> bool:
    text = f"{item.get('msg_cn', '')} {item.get('dst_se_nm', '')}"
    return any(kw in text for kw in MISSING_PERSON_KEYWORDS)


def _api_error_message(data: dict) -> Optional[str]:
    header = data.get("header") or {}
    result_code = str(header.get("resultCode") or "").strip()
    if not result_code or result_code in ("00", "0", "NORMAL"):
        return None

    msg = header.get("resultMsg") or header.get("errorMsg") or "API 오류"
    if result_code == "22":
        return (
            "재난안전데이터 API 일일 호출 한도(1,000회)를 모두 사용했습니다. "
            "검색 1회는 문자 여러 건을 가져오기 위해 API를 여러 번 호출합니다(문자 1건 ≠ 1회). "
            "자정 이후 한도가 초기화되면 검색 버튼을 다시 눌러주세요."
        )
    if result_code in ("30", "31"):
        return "재난안전데이터 API 인증키가 유효하지 않습니다. SAFETYDATA_SERVICE_KEY를 확인해 주세요."
    return f"재난안전데이터 API 오류 ({result_code}): {msg}"


def _estimate_max_pages(start_ymd: str, end_ymd: str, missing_only: bool = False) -> int:
    """과거 기간 검색 시 종료일 이후 데이터를 건너뛰려면 더 많은 페이지가 필요."""
    today = datetime.now()
    end_date = datetime.strptime(end_ymd, "%Y%m%d")
    start_date = datetime.strptime(start_ymd, "%Y%m%d")
    page_size = 1000

    if end_date.date() >= today.date():
        return 10 if missing_only else 15

    days_after_end = max((today - end_date).days, 0)
    range_days = max((end_date - start_date).days, 1)
    skip_records = days_after_end * 30
    range_records = range_days * 5
    pages = (skip_records + range_records) // page_size + 15
    return min(max(pages, 20), 120)


def _cache_file_path(cache_key: str) -> Path:
    safe = re.sub(r"[^\w|=-]", "_", cache_key)
    return CACHE_DIR / f"{safe}.json"


def _load_file_cache(cache_key: str) -> Optional[dict]:
    path = _cache_file_path(cache_key)
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_file_cache(cache_key: str, data: dict) -> None:
    path = _cache_file_path(cache_key)
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "data": data}, f, ensure_ascii=False)
    except OSError:
        pass


def _cache_key(
    start_ymd: str,
    end_ymd: str,
    rgn_nm: Optional[str],
    missing_only: bool,
    keyword: Optional[str],
) -> str:
    return f"{start_ymd}|{end_ymd}|{rgn_nm or ''}|{missing_only}|{keyword or ''}"


async def fetch_disaster_alerts(
    crt_dt: Optional[str] = None,
    end_dt: Optional[str] = None,
    rgn_nm: Optional[str] = None,
    page_no: int = 1,
    num_of_rows: int = 100,
    keyword: Optional[str] = None,
    missing_only: bool = False,
    force_refresh: bool = False,
    cache_only: bool = False,
) -> dict:
    if not settings.SAFETYDATA_SERVICE_KEY or not settings.SAFETYDATA_API_URL:
        return {"items": [], "total_count": 0, "error": "API 키 또는 URL이 설정되지 않았습니다."}

    end_ymd = end_dt.strip() if end_dt else datetime.now().strftime("%Y%m%d")
    start_ymd = crt_dt.strip() if crt_dt else (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")

    cache_key = _cache_key(start_ymd, end_ymd, rgn_nm, missing_only, keyword)

    if not force_refresh:
        file_cached = _load_file_cache(cache_key)
        if file_cached and file_cached.get("data"):
            age_h = (time.time() - file_cached.get("ts", 0)) / 3600
            warning = None
            if age_h > 1:
                warning = f"저장된 조회 결과를 표시합니다 ({int(age_h)}시간 전 데이터)."
            return {**file_cached["data"], "warning": warning, "from_cache": True}

    if cache_only:
        return {
            "items": [],
            "total_count": 0,
            "error": None,
            "hint": "아래 검색 버튼을 눌러 실종 안내문자를 조회하세요.",
        }

    cached = _CACHE.get(cache_key)
    if cached and time.time() - cached["ts"] < CACHE_TTL_SEC:
        return cached["data"]

    collected = []
    seen_ids: set = set()
    max_pages = _estimate_max_pages(start_ymd, end_ymd, missing_only)
    page_size = 1000
    api_calls = 0

    try:
        timeout = httpx.Timeout(120.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            for page in range(1, max_pages + 1):
                params = {
                    "serviceKey": settings.SAFETYDATA_SERVICE_KEY,
                    "returnType": "json",
                    "numOfRows": page_size,
                    "pageNo": page,
                    "crtDt": start_ymd,
                }
                if rgn_nm and rgn_nm != "전국":
                    params["rgnNm"] = rgn_nm

                res = await client.get(settings.SAFETYDATA_API_URL, params=params)
                api_calls += 1
                res.raise_for_status()
                data = res.json()

                api_error = _api_error_message(data)
                if api_error:
                    file_cached = _load_file_cache(cache_key)
                    if file_cached and file_cached.get("data"):
                        return {
                            **file_cached["data"],
                            "warning": "API 한도 초과 — 이전에 저장된 조회 결과를 표시합니다.",
                            "from_cache": True,
                        }
                    return {"items": [], "total_count": 0, "error": api_error}

                total_count = int(data.get("totalCount") or 0)
                body = data.get("body") or []
                if isinstance(body, dict):
                    body = body.get("items") or body.get("item") or []
                if isinstance(body, dict):
                    body = [body]

                if not body:
                    break

                page_dates = []
                for raw in body:
                    m = _map_alert(raw)
                    if not m["msg_cn"]:
                        continue
                    if m["id"] and m["id"] in seen_ids:
                        continue

                    d = _parse_item_ymd(m)
                    if d:
                        page_dates.append(d)
                        if d > end_ymd:
                            continue
                        if d < start_ymd:
                            continue

                    if m["id"]:
                        seen_ids.add(m["id"])

                    if missing_only and not _is_missing_person_alert(m):
                        continue
                    if keyword and keyword not in m["msg_cn"] and keyword not in m["dst_se_nm"]:
                        continue

                    collected.append(m)

                if page_dates and all(d < start_ymd for d in page_dates):
                    break

                if total_count and len(seen_ids) >= total_count:
                    break

                if not missing_only and len(collected) >= num_of_rows:
                    break

    except Exception as e:
        return {"items": [], "total_count": 0, "error": str(e)}

    collected.sort(key=lambda x: _parse_item_ymd(x) or "", reverse=True)
    result = {
        "items": collected,
        "total_count": len(collected),
        "error": None,
        "api_calls_used": api_calls,
    }
    _CACHE[cache_key] = {"ts": time.time(), "data": result}
    _save_file_cache(cache_key, result)
    return result
