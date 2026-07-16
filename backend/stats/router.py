from __future__ import annotations

from datetime import date
from io import BytesIO

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .db_init import ensure_stats_tables
from .export_service import StatsExportService
from .integration import (
    StatsActor,
    get_db,
    get_stats_actor,
)
from .repository import StatsRepository
from .schemas import (
    CaseEventCreate,
    CaseEventResponse,
    CctvStatsResponse,
    DemographicStatsResponse,
    ExportLogItem,
    ExportRequest,
    OutcomeStatsResponse,
    SearchStatsResponse,
)
from .service import StatsService
from .table_registry import StatsSourceError


router = APIRouter(
    prefix="/api/v1/admin/stats",
    tags=["Statistics"],
)


def get_stats_db(
    db: Session = Depends(get_db),
) -> Session:
    ensure_stats_tables(db)
    return db


def make_service(db: Session) -> StatsService:
    return StatsService(
        db=db,
        repository=StatsRepository(db),
    )


@router.get(
    "/cctv",
    response_model=CctvStatsResponse,
)
def get_cctv_stats(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    region: str | None = Query(default=None),
    db: Session = Depends(get_stats_db),
):
    try:
        return make_service(db).get_cctv(
            from_date,
            to_date,
            region,
        )
    except StatsSourceError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.get(
    "/search",
    response_model=SearchStatsResponse,
)
def get_search_stats(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    search_type: str | None = Query(default=None),
    db: Session = Depends(get_stats_db),
):
    try:
        return make_service(db).get_search(
            from_date,
            to_date,
            search_type,
        )
    except StatsSourceError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.get(
    "/demographic",
    response_model=DemographicStatsResponse,
)
def get_demographic_stats(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    db: Session = Depends(get_stats_db),
):
    try:
        return make_service(db).get_demographic(
            from_date,
            to_date,
        )
    except StatsSourceError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.get(
    "/outcomes",
    response_model=OutcomeStatsResponse,
)
def get_outcome_stats(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    region: str | None = Query(default=None),
    db: Session = Depends(get_stats_db),
):
    return make_service(db).get_outcomes(
        from_date,
        to_date,
        region,
    )


@router.post(
    "/case-events",
    response_model=CaseEventResponse,
    status_code=201,
)
def create_case_event(
    payload: CaseEventCreate,
    request: Request,
    db: Session = Depends(get_stats_db),
):
    actor = get_stats_actor(request)
    return make_service(db).create_case_event(
        payload,
        actor,
    )


@router.get(
    "/case-events",
    response_model=list[CaseEventResponse],
)
def list_case_events(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    event_type: str | None = Query(default=None),
    case_key: str | None = Query(default=None),
    db: Session = Depends(get_stats_db),
):
    return make_service(db).list_events(
        from_date,
        to_date,
        event_type,
        case_key,
    )


@router.post("/export")
def export_stats(
    payload: ExportRequest,
    request: Request,
    db: Session = Depends(get_stats_db),
):
    actor = get_stats_actor(request)
    exporter = StatsExportService(db)

    try:
        filename, content, _ = exporter.build(
            payload,
            actor,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except StatsSourceError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    encoded = content.encode("utf-8")
    return StreamingResponse(
        iter([encoded]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )


@router.get(
    "/exports",
    response_model=list[ExportLogItem],
)
def list_exports(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_stats_db),
):
    repository = StatsRepository(db)
    return repository.list_export_logs(limit)
