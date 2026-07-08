"""
[화면] DataViews.jsx, RegionFormModal.jsx
[서비스] region_csv, administrative_dong_import, audit_service
[테이블] region, region_legal_dong, video
"""
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.deps import require_roles
from backend.db.database import get_db
from backend.db.models import AdminAction, Region, User, UserRole, Video
from backend.schemas.data_integrity_schema import RegionClearResult, RegionImportResult
from backend.schemas.region_schema import (
    RegionCreate,
    RegionItem,
    RegionListResponse,
    RegionOption,
    RegionOptionsResponse,
    RegionUpdate,
)
from backend.services.administrative_dong_import import clear_all_region_data
from backend.services.audit_service import record_admin_action
from backend.services.region_csv import (
    administrative_dong_to_csv,
    import_regions_from_csv,
    regions_to_csv,
)

from .tags import TAG_REGIONS

router = APIRouter()


def _region_child_counts(db: Session, codes: list[str]) -> dict[str, int]:
    if not codes:
        return {}
    rows = db.execute(
        select(Region.parent_code, func.count())
        .where(Region.parent_code.in_(codes))
        .group_by(Region.parent_code)
    ).all()
    return {parent: cnt for parent, cnt in rows}


def _region_video_counts(db: Session, codes: list[str]) -> dict[str, int]:
    if not codes:
        return {}
    rows = db.execute(
        select(Video.region_code, func.count())
        .where(Video.region_code.in_(codes))
        .group_by(Video.region_code)
    ).all()
    return {code: cnt for code, cnt in rows}


def _to_region_items(db: Session, regions: list[Region]) -> list[RegionItem]:
    codes = [r.region_code for r in regions]
    child_counts = _region_child_counts(db, codes)
    video_counts = _region_video_counts(db, codes)
    return [
        RegionItem(
            region_code=r.region_code,
            full_name=r.full_name,
            specific_name=r.specific_name,
            parent_code=r.parent_code,
            child_count=child_counts.get(r.region_code, 0),
            video_count=video_counts.get(r.region_code, 0),
            created_at=r.created_at,
        )
        for r in regions
    ]


def _region_refs(db: Session, region_code: str) -> tuple[int, int]:
    child_count = (
        db.scalar(
            select(func.count())
            .select_from(Region)
            .where(Region.parent_code == region_code)
        )
        or 0
    )
    video_count = (
        db.scalar(
            select(func.count())
            .select_from(Video)
            .where(Video.region_code == region_code)
        )
        or 0
    )
    return child_count, video_count


def _validate_parent(
    db: Session,
    *,
    region_code: str | None,
    parent_code: str | None,
) -> None:
    if parent_code is None or parent_code == "":
        return
    if region_code and parent_code == region_code:
        raise HTTPException(status_code=422, detail="자기 자신을 상위 지역으로 지정할 수 없습니다.")
    parent = db.get(Region, parent_code)
    if parent is None:
        raise HTTPException(status_code=404, detail="상위 행정구역을 찾을 수 없습니다.")
    if region_code:
        cursor = parent_code
        while cursor:
            if cursor == region_code:
                raise HTTPException(
                    status_code=422,
                    detail="상위 지역 지정 시 계층 순환이 발생합니다.",
                )
            cursor = db.scalar(
                select(Region.parent_code).where(Region.region_code == cursor)
            )


@router.get(
    "/regions",
    response_model=RegionListResponse,
    summary="행정구역 목록 조회",
    tags=TAG_REGIONS,
)
def list_regions(
    parent_code: str | None = Query(
        default=None,
        description="상위 지역코드. 미지정·빈 문자열이면 최상위(시·도)",
    ),
    q: str | None = Query(default=None, description="코드·지역명 검색"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> RegionListResponse:
    parent = parent_code or None
    if parent == "":
        parent = None

    base = select(Region)
    if q:
        keyword = f"%{q.strip()}%"
        base = base.where(
            or_(
                Region.region_code.like(keyword),
                Region.full_name.like(keyword),
                Region.specific_name.like(keyword),
            )
        )
    elif parent is None:
        base = base.where(Region.parent_code.is_(None))
    else:
        base = base.where(Region.parent_code == parent)

    count_stmt = select(func.count()).select_from(Region)
    if q:
        keyword = f"%{q.strip()}%"
        count_stmt = count_stmt.where(
            or_(
                Region.region_code.like(keyword),
                Region.full_name.like(keyword),
                Region.specific_name.like(keyword),
            )
        )
    elif parent is None:
        count_stmt = count_stmt.where(Region.parent_code.is_(None))
    else:
        count_stmt = count_stmt.where(Region.parent_code == parent)
    total = db.scalar(count_stmt) or 0

    rows = list(
        db.scalars(
            base.order_by(Region.region_code)
            .offset((page - 1) * per_page)
            .limit(per_page)
        ).all()
    )

    return RegionListResponse(
        items=_to_region_items(db, rows),
        total=total,
        page=page,
        size=per_page,
        parent_code=parent,
    )


@router.get(
    "/regions/options",
    response_model=RegionOptionsResponse,
    summary="행정구역 선택 옵션",
    tags=TAG_REGIONS,
)
def list_region_options(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> RegionOptionsResponse:
    rows = list(
        db.scalars(select(Region).order_by(Region.region_code).limit(500)).all()
    )
    items = [
        RegionOption(
            region_code=r.region_code,
            label=r.full_name or r.specific_name or r.region_code,
            parent_code=r.parent_code,
        )
        for r in rows
    ]
    return RegionOptionsResponse(items=items)


@router.get(
    "/regions/export.csv",
    summary="행정구역 CSV보내기",
    tags=TAG_REGIONS,
)
def export_regions_csv(
    request: Request,
    format: str = Query(
        default="region",
        pattern="^(region|administrative_dong)$",
        description="region: 계층 CSV | administrative_dong: 행정동 원본 형식",
    ),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> Response:
    if format == "administrative_dong":
        csv_text = administrative_dong_to_csv(db)
        filename = "administrative_dong.csv"
        export_format = "administrative_dong"
    else:
        csv_text = regions_to_csv(db)
        filename = "regions.csv"
        export_format = "region"

    row_count = max(csv_text.count("\n") - 1, 0)
    record_admin_action(
        db,
        actor_id=admin.id,
        action_type=AdminAction.UPDATE,
        target_type="region",
        target_id="export",
        detail={
            "action": "export",
            "row_count": row_count,
            "format": export_format,
        },
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    body = "\ufeff" + csv_text
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/regions/clear-all",
    response_model=RegionClearResult,
    summary="행정구역 전체 삭제",
    tags=TAG_REGIONS,
)
def clear_regions_all(
    request: Request,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> RegionClearResult:
    result = clear_all_region_data(db)
    record_admin_action(
        db,
        actor_id=admin.id,
        action_type=AdminAction.DELETE,
        target_type="region",
        target_id="clear_all",
        detail={
            "action": "clear_all",
            "region_deleted": result.region_deleted,
            "legal_dong_deleted": result.legal_dong_deleted,
            "video_unlinked": result.video_unlinked,
        },
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return result


@router.post(
    "/regions/import.csv",
    response_model=RegionImportResult,
    summary="행정구역 CSV 가져오기",
    tags=TAG_REGIONS,
)
async def import_regions_csv(
    request: Request,
    file: UploadFile = File(...),
    dry_run: bool = Query(default=False, description="true면 검증만 수행"),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> RegionImportResult:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV 파일만 업로드할 수 있습니다.")

    result = import_regions_from_csv(db, file.file, dry_run=dry_run)
    if result.errors:
        return result

    if not dry_run:
        record_admin_action(
            db,
            actor_id=admin.id,
            action_type=AdminAction.UPDATE,
            target_type="region",
            target_id="import",
            detail={
                "action": "import",
                "filename": file.filename,
                "format": result.format,
                "created": result.created,
                "updated": result.updated,
                "skipped": result.skipped,
                "legal_dong_created": result.legal_dong_created,
                "legal_dong_updated": result.legal_dong_updated,
                "csv_rows": result.csv_rows,
            },
            ip_address=request.client.host if request.client else None,
        )
        db.commit()
    return result


@router.get(
    "/regions/{region_code}",
    response_model=RegionItem,
    summary="행정구역 단건 조회",
    tags=TAG_REGIONS,
)
def get_region(
    region_code: str,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> RegionItem:
    region = db.get(Region, region_code)
    if region is None:
        raise HTTPException(status_code=404, detail="행정구역을 찾을 수 없습니다.")
    return _to_region_items(db, [region])[0]


@router.post(
    "/regions",
    response_model=RegionItem,
    status_code=201,
    summary="행정구역 등록",
    tags=TAG_REGIONS,
)
def create_region(
    payload: RegionCreate,
    request: Request,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> RegionItem:
    code = payload.region_code.strip()
    if db.get(Region, code) is not None:
        raise HTTPException(status_code=409, detail="이미 사용 중인 지역코드입니다.")

    parent = payload.parent_code.strip() if payload.parent_code else None
    _validate_parent(db, region_code=code, parent_code=parent)

    region = Region(
        region_code=code,
        full_name=payload.full_name.strip() if payload.full_name else None,
        specific_name=payload.specific_name.strip() if payload.specific_name else None,
        parent_code=parent,
    )
    db.add(region)
    record_admin_action(
        db,
        actor_id=admin.id,
        action_type=AdminAction.UPDATE,
        target_type="region",
        target_id=code,
        detail={"action": "create", "after": payload.model_dump()},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(region)
    return _to_region_items(db, [region])[0]


@router.patch(
    "/regions/{region_code}",
    response_model=RegionItem,
    summary="행정구역 수정",
    tags=TAG_REGIONS,
)
def update_region(
    region_code: str,
    payload: RegionUpdate,
    request: Request,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> RegionItem:
    region = db.get(Region, region_code)
    if region is None:
        raise HTTPException(status_code=404, detail="행정구역을 찾을 수 없습니다.")

    before = {
        "full_name": region.full_name,
        "specific_name": region.specific_name,
        "parent_code": region.parent_code,
    }
    data = payload.model_dump(exclude_unset=True)

    if "parent_code" in data:
        parent = data["parent_code"].strip() if data["parent_code"] else None
        _validate_parent(db, region_code=region_code, parent_code=parent)
        region.parent_code = parent

    if "full_name" in data:
        region.full_name = data["full_name"].strip() if data["full_name"] else None
    if "specific_name" in data:
        region.specific_name = (
            data["specific_name"].strip() if data["specific_name"] else None
        )

    record_admin_action(
        db,
        actor_id=admin.id,
        action_type=AdminAction.UPDATE,
        target_type="region",
        target_id=region_code,
        detail={
            "action": "update",
            "before": before,
            "after": {
                "full_name": region.full_name,
                "specific_name": region.specific_name,
                "parent_code": region.parent_code,
            },
        },
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(region)
    return _to_region_items(db, [region])[0]


@router.delete(
    "/regions/{region_code}",
    status_code=204,
    summary="행정구역 삭제",
    tags=TAG_REGIONS,
)
def delete_region(
    region_code: str,
    request: Request,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> None:
    region = db.get(Region, region_code)
    if region is None:
        raise HTTPException(status_code=404, detail="행정구역을 찾을 수 없습니다.")

    child_count, video_count = _region_refs(db, region_code)
    if child_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"하위 행정구역 {child_count}건이 있어 삭제할 수 없습니다.",
        )
    if video_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"연결된 영상 {video_count}건이 있어 삭제할 수 없습니다.",
        )

    snapshot = {
        "full_name": region.full_name,
        "specific_name": region.specific_name,
        "parent_code": region.parent_code,
    }
    db.delete(region)
    record_admin_action(
        db,
        actor_id=admin.id,
        action_type=AdminAction.DELETE,
        target_type="region",
        target_id=region_code,
        detail={"action": "delete", "before": snapshot},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
