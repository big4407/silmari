"""
재난안전데이터 API 프록시 — 대시보드 재난문자 목록용.

GET /list — safetydata_client.fetch_disaster_alerts()
            missing_only, force_refresh, cache_only 등 쿼리 지원
"""
from fastapi import APIRouter, Query

from backend.services.safetydata_client import fetch_disaster_alerts

router = APIRouter()


@router.get("/list")
async def list_disaster_alerts(
    crt_dt: str = Query(None, description="조회시작일자 YYYYMMDD"),
    end_dt: str = Query(None, description="조회종료일자 YYYYMMDD"),
    rgn_nm: str = Query(None, description="지역명"),
    page_no: int = Query(1, ge=1),
    num_of_rows: int = Query(100, ge=1, le=100),
    keyword: str = Query(None, description="메시지/재해구분 필터"),
    missing_only: bool = Query(False, description="실종 관련 안내문자만"),
    force_refresh: bool = Query(False, description="캐시 무시하고 API 재조회"),
    cache_only: bool = Query(False, description="저장된 캐시만 조회(외부 API 호출 없음)"),
):
    return await fetch_disaster_alerts(
        crt_dt=crt_dt,
        end_dt=end_dt,
        rgn_nm=rgn_nm,
        page_no=page_no,
        num_of_rows=num_of_rows,
        keyword=keyword,
        missing_only=missing_only,
        force_refresh=force_refresh,
        cache_only=cache_only,
    )
