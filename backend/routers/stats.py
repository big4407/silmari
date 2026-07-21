"""
관리자 통계 API — CCTV·검색·인구통계·발견해결결과.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import User, UserRole
from backend.deps import require_roles
from backend.schemas.stats_schema import (
    CctvStatsResponse,
    DemographicStatsResponse,
    ExportLogItem,
    ExportRequest,
    OutcomeStatsResponse,
    SearchStatsResponse,
)
from backend.services.stats_export_service import StatsExportService
from backend.services.stats_service import StatsService

router = APIRouter(prefix="/admin/stats", tags=["Statistics"])


@router.get("/cctv", response_model=CctvStatsResponse)
def get_cctv_stats(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    region: str | None = Query(default=None),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return StatsService(db).get_cctv(from_date, to_date, region)


@router.get("/search", response_model=SearchStatsResponse)
def get_search_stats(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    search_type: str | None = Query(default=None),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return StatsService(db).get_search(from_date, to_date, search_type)


@router.get("/demographic", response_model=DemographicStatsResponse)
def get_demographic_stats(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return StatsService(db).get_demographic(from_date, to_date)


@router.get("/outcomes", response_model=OutcomeStatsResponse)
def get_outcome_stats(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    region: str | None = Query(default=None),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return StatsService(db).get_outcomes(from_date, to_date, region)


@router.post("/export")
def export_stats(
    payload: ExportRequest,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    filename, content, _ = StatsExportService(db).build(
        payload,
        actor_id=admin.id,
        actor_name=admin.full_name or admin.username,
    )

    encoded = content.encode("utf-8")
    return StreamingResponse(
        iter([encoded]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/exports", response_model=list[ExportLogItem])
def list_exports(
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return StatsService(db).list_exports(limit)