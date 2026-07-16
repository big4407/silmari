"""
관리자 API — 회원 승인·반려·역할 부여.

[RBAC] require_roles(UserRole.ADMIN) — admin 역할만 접근
[핵심] PATCH /admin/users/{id}/approval — pending → approved/rejected/suspended
"""

import csv
import io
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.deps import require_roles
from backend.core.security import utc_now
from backend.db.database import get_db
from backend.db.models import (
    AdminAction,
    AdminHistory,
    ApprovalStatus,
    LoginHistory,
    Region,
    RetentionPolicy,
    User,
    UserRole,
    Video,
)
from backend.schemas.auth_schema import UserResponse
from backend.schemas.user_schema import ApprovalRequest
from backend.schemas.login_history_schema import (
    LoginHistoryItem,
    LoginHistoryListResponse,
)
from backend.utils.timeutils import kst_now
from backend.services.audit_service import AuditService
from backend.schemas.admin_history_schema import (
    AdminHistoryItem,
    AdminHistoryListResponse,
)
from backend.schemas.data_integrity_schema import (
    IntegrityCheckIssuesResponse,
    IntegrityRunResponse,
)
from backend.schemas.region_schema import (
    RegionClearResult,
    RegionCreate,
    RegionImportResult,
    RegionItem,
    RegionListResponse,
    RegionOption,
    RegionOptionsResponse,
    RegionUpdate,
)
from backend.schemas.retention_schema import (
    RetentionDryRunRequest,
    RetentionDryRunResponse,
    RetentionPolicyBulkUpdate,
    RetentionPolicyItem,
    RetentionPolicyListResponse,
)
from backend.services.integrity_service import IntegrityService
from backend.services.retention_service import RetentionService
from backend.services.region_admin_service import RegionAdminService
from backend.services.search_service import SearchService
from backend.schemas.search_schema import AdminSearchListResponse
from backend.services.cctv_coverage_service import CctvCoverageService
from backend.schemas.video_schema import (
    CctvRegionCoverageResponse,
    DailyVideoSummaryResponse,
    VideoIndexRetryRequest,
    VideoIndexRetryResponse,
)

router = APIRouter(prefix="/admin")


@router.get("/users", response_model=list[UserResponse])
def list_users(
    approval_status: ApprovalStatus | None = Query(default=None),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[User]:
    stmt = select(User).order_by(User.created_at.desc())
    if approval_status is not None:
        stmt = stmt.where(User.approval_status == approval_status)
    return list(db.scalars(stmt).all())


@router.patch("/users/{user_id}/approval", response_model=UserResponse)
def update_approval(
    user_id: str,
    payload: ApprovalRequest,
    request: Request,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    if target.id == admin.id and payload.status != ApprovalStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail="본인 계정은 이 API로 정지하거나 반려할 수 없습니다.",
        )

    # 변경 전 상태 (감사 로그 detail 의 before)
    before = {
        "role": target.role.value if target.role else None,
        "approval_status": target.approval_status.value,
    }
    was_approved = target.approval_status == ApprovalStatus.APPROVED

    if payload.status == ApprovalStatus.APPROVED:
        # [안전장치] 승인된 적 없는 계정(role 없음)을 정지 해제하는 경우,
        # 승인으로 바로 넘기지 않고 '승인 대기'로 되돌린다. 검토 없이 승인되는 것을 방지.
        never_approved = target.role is None and payload.role is None
        if never_approved and before["approval_status"] in ("2", "3"):
            # 정지·반려 상태 + 승인 이력 없음 → 대기로 복귀
            target.approval_status = ApprovalStatus.PENDING
            target.approved_at = None
            target.approved_by_id = None
            target.rejection_reason = None
            action = AdminAction.REACTIVATE
            reason = "승인 이력이 없어 승인 대기 상태로 되돌림"
        else:
            assigned_role = payload.role or target.requested_role
            target.role = assigned_role
            target.approval_status = ApprovalStatus.APPROVED
            target.approved_at = utc_now()
            target.approved_by_id = admin.id
            target.rejection_reason = None
            # 반려·정지에서 다시 승인이면 재승인(REACTIVATE), 신규 대기 승인이면 APPROVE
            action = (
                AdminAction.APPROVE
                if before["approval_status"] == "0"
                else AdminAction.REACTIVATE
            )
            reason = None
    elif payload.status == ApprovalStatus.REJECTED:
        target.role = None
        target.approval_status = ApprovalStatus.REJECTED
        target.approved_at = None
        target.approved_by_id = admin.id
        target.rejection_reason = (
            payload.rejection_reason or "관리자 검토 결과 가입 신청이 반려되었습니다."
        )
        action = AdminAction.REJECT
        reason = target.rejection_reason
    elif payload.status == ApprovalStatus.SUSPENDED:
        target.approval_status = ApprovalStatus.SUSPENDED
        target.approved_by_id = admin.id
        target.rejection_reason = (
            payload.rejection_reason or "관리자에 의해 계정 사용이 정지되었습니다."
        )
        action = AdminAction.SUSPEND
        reason = target.rejection_reason
    else:
        raise HTTPException(
            status_code=422, detail="pending 상태로 되돌리는 작업은 지원하지 않습니다."
        )

    db.add(target)

    # 감사 로그 기록 (같은 트랜잭션에 묶어 커밋)
    AuditService(db).record_admin_action(
        actor_id=admin.id,
        action_type=action,
        target_type="user",
        target_id=target.id,
        detail={
            "target_username": target.username,
            "target_name": target.full_name,
            "before": before,
            "after": {
                "role": target.role.value if target.role else None,
                "approval_status": target.approval_status.value,
            },
            "reason": reason,
        },
        ip_address=request.client.host if request.client else None,
    )

    db.commit()
    db.refresh(target)
    return target


@router.get("/login-history", response_model=LoginHistoryListResponse)
def list_login_history(
    username: str | None = Query(default=None, description="아이디 부분 검색"),
    success: bool | None = Query(default=None, description="성공/실패 필터"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> LoginHistoryListResponse:
    """로그인 이력(감사 로그) 조회 — 최신순, 필터·페이지네이션."""
    # user 와 LEFT JOIN 해서 full_name 도 함께 (없는 계정 시도면 None)
    base = select(LoginHistory, User.full_name).join(
        User, LoginHistory.user_id == User.id, isouter=True
    )

    conds = []
    if username:
        conds.append(LoginHistory.username.like(f"%{username}%"))
    if success is not None:
        conds.append(LoginHistory.success == success)
    if start_date is not None:
        conds.append(LoginHistory.created_at >= datetime.combine(start_date, time.min))
    if end_date is not None:
        conds.append(LoginHistory.created_at <= datetime.combine(end_date, time.max))
    for c in conds:
        base = base.where(c)

    # 총 건수
    count_stmt = select(func.count()).select_from(LoginHistory)
    for c in conds:
        count_stmt = count_stmt.where(c)
    total = db.scalar(count_stmt) or 0

    # 페이지 데이터
    rows = db.execute(
        base.order_by(LoginHistory.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()

    items = []
    for lh, full_name in rows:
        item = LoginHistoryItem.model_validate(lh)
        item.full_name = full_name  # JOIN 으로 얻은 값 주입 (스키마 기본값 None 이라 검증 통과 후 할당)
        items.append(item)

    # 오늘(KST) 요약
    today_start = datetime.combine(kst_now().date(), time.min)
    today_base = (
        select(func.count())
        .select_from(LoginHistory)
        .where(LoginHistory.created_at >= today_start)
    )
    today_success = db.scalar(today_base.where(LoginHistory.success == True)) or 0  # noqa: E712
    today_failed = db.scalar(today_base.where(LoginHistory.success == False)) or 0  # noqa: E712

    return LoginHistoryListResponse(
        items=items,
        total=total,
        page=page,
        size=per_page,
        today_success=today_success,
        today_failed=today_failed,
    )


@router.get("/admin-history", response_model=AdminHistoryListResponse)
def list_admin_history(
    action_type: AdminAction | None = Query(default=None, description="행동 유형 필터"),
    approval_only: bool = Query(default=False, description="승인·권한 변경만(1~4)"),
    actor: str | None = Query(default=None, description="행위자 이름·아이디 부분 검색"),
    target_type: str | None = Query(
        default=None, description="대상 유형 필터 (user, region 등)"
    ),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> AdminHistoryListResponse:
    """관리자 행동 이력(감사 로그) 조회 — 최신순, 필터·페이지네이션.

    approval_only=True 면 승인·권한 변경(APPROVE~REACTIVATE)만 → 승인 이력 뷰용.
    """
    base = select(AdminHistory, User.full_name).join(
        User, AdminHistory.actor_id == User.id, isouter=True
    )

    conds = []
    if action_type is not None:
        conds.append(AdminHistory.action_type == action_type)
    if approval_only:
        conds.append(
            AdminHistory.action_type.in_(
                [
                    AdminAction.APPROVE,
                    AdminAction.REJECT,
                    AdminAction.SUSPEND,
                    AdminAction.REACTIVATE,
                ]
            )
        )
    if actor:
        conds.append(
            or_(
                User.full_name.like(f"%{actor}%"),
                User.username.like(f"%{actor}%"),
            )
        )
    if target_type:
        conds.append(AdminHistory.target_type == target_type)
    if start_date is not None:
        conds.append(AdminHistory.created_at >= datetime.combine(start_date, time.min))
    if end_date is not None:
        conds.append(AdminHistory.created_at <= datetime.combine(end_date, time.max))
    for c in conds:
        base = base.where(c)

    count_stmt = select(func.count()).select_from(AdminHistory)
    # actor 검색은 User 조인이 필요하므로 count 에도 반영
    if actor:
        count_stmt = count_stmt.join(
            User, AdminHistory.actor_id == User.id, isouter=True
        )
    for c in conds:
        count_stmt = count_stmt.where(c)
    total = db.scalar(count_stmt) or 0

    rows = db.execute(
        base.order_by(AdminHistory.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()

    items = []
    for ah, actor_name in rows:
        item = AdminHistoryItem.model_validate(ah)
        item.actor_name = actor_name
        items.append(item)

    return AdminHistoryListResponse(items=items, total=total, page=page, size=per_page)


@router.get("/search-requests", response_model=AdminSearchListResponse)
def list_search_requests(
    keyword: str | None = Query(default=None, description="이름·인상착의·지역 부분 검색"),
    search_type: str | None = Query(default=None, description="1:안내문자, 2:챗봇, 3:자동"),
    requester_user_id: str | None = Query(default=None, description="요청자 user.id"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> AdminSearchListResponse:
    """검색 요청 이력(관리자용) — 전체 사용자 대상, 최신순, 필터·오늘 요약 포함."""
    return SearchService(db).list_for_admin(
        page=page,
        size=per_page,
        keyword=keyword,
        search_type=search_type,
        requester_user_id=requester_user_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/cctv-coverage", response_model=CctvRegionCoverageResponse)
def get_cctv_coverage(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> CctvRegionCoverageResponse:
    """CCTV 영상 수집 현황(관리자용) — 지역별 CCTV 대수·영상 파일 수."""
    return CctvCoverageService(db).get_region_coverage()


@router.get("/video-daily-summary", response_model=DailyVideoSummaryResponse)
def get_video_daily_summary(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> DailyVideoSummaryResponse:
    """촬영일자별 영상 현황(관리자용) — Video 테이블 groupby 기반."""
    return CctvCoverageService(db).get_daily_summary(page=page, per_page=per_page)


@router.post("/video-index-jobs/retry", response_model=VideoIndexRetryResponse)
def retry_video_index_job(
    payload: VideoIndexRetryRequest,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> VideoIndexRetryResponse:
    """특정 날짜의 영상을 다시 인덱싱한다("인덱싱 재시도" 버튼).

    YOLO·FashionCLIP 처리라 시간이 걸릴 수 있다 — 지금은 요청-응답 안에서
    동기로 끝까지 돈다(검색 생성과 같은 1차 결정). 영상이 많아지면 비동기
    전환을 검토해야 한다. 결과는 별도로 저장되지 않는 1회성 응답이다 —
    다시 조회하고 싶으면 /video-daily-summary를 새로고침한다.
    """
    from backend.services.video_service import VideoService

    result = VideoService(db).run_indexing_job(payload.target_date)
    return VideoIndexRetryResponse(target_date=payload.target_date, **result)


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


@router.get("/regions", response_model=RegionListResponse)
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
    """행정구역 목록 — parent_code 기준 계층 조회 또는 검색."""
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


@router.get("/regions/options", response_model=RegionOptionsResponse)
def list_region_options(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> RegionOptionsResponse:
    """상위 지역 선택용 — 전체 행정구역 플랫 목록(최대 500)."""
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


@router.get("/regions/export.csv")
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
    """행정구역 CSV보내기."""
    region_svc = RegionAdminService(db)
    if format == "administrative_dong":
        csv_text = region_svc.administrative_dong_to_csv()
        filename = "administrative_dong.csv"
        export_format = "administrative_dong"
    else:
        csv_text = region_svc.regions_to_csv()
        filename = "regions.csv"
        export_format = "region"

    row_count = max(csv_text.count("\n") - 1, 0)
    AuditService(db).record_admin_action(
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


@router.post("/regions/clear-all", response_model=RegionClearResult)
def clear_regions_all(
    request: Request,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> RegionClearResult:
    """행정구역·법정동 매핑 전체 삭제 (video.region_code 는 연결 해제)."""
    result = RegionAdminService(db).clear_all()
    AuditService(db).record_admin_action(
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


@router.post("/regions/import.csv", response_model=RegionImportResult)
async def import_regions_csv(
    request: Request,
    file: UploadFile = File(...),
    dry_run: bool = Query(default=False, description="true면 검증만 수행"),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> RegionImportResult:
    """행정구역 CSV 가져오기 (upsert)."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV 파일만 업로드할 수 있습니다.")

    result = RegionAdminService(db).import_from_csv(file.file, dry_run=dry_run)
    if result.errors:
        return result

    if not dry_run:
        AuditService(db).record_admin_action(
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


@router.get("/regions/{region_code}", response_model=RegionItem)
def get_region(
    region_code: str,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> RegionItem:
    region = db.get(Region, region_code)
    if region is None:
        raise HTTPException(status_code=404, detail="행정구역을 찾을 수 없습니다.")
    return _to_region_items(db, [region])[0]


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
        raise HTTPException(
            status_code=422, detail="자기 자신을 상위 지역으로 지정할 수 없습니다."
        )
    parent = db.get(Region, parent_code)
    if parent is None:
        raise HTTPException(status_code=404, detail="상위 행정구역을 찾을 수 없습니다.")
    # 순환 참조 방지: parent 체인을 따라 올라가며 region_code 와 충돌 없는지 확인
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


@router.post("/regions", response_model=RegionItem, status_code=201)
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
    AuditService(db).record_admin_action(
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


@router.patch("/regions/{region_code}", response_model=RegionItem)
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

    AuditService(db).record_admin_action(
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


@router.delete("/regions/{region_code}", status_code=204)
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
    AuditService(db).record_admin_action(
        actor_id=admin.id,
        action_type=AdminAction.DELETE,
        target_type="region",
        target_id=region_code,
        detail={"action": "delete", "before": snapshot},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()


@router.get("/retention-policies", response_model=RetentionPolicyListResponse)
def get_retention_policies(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> RetentionPolicyListResponse:
    retention_svc = RetentionService(db)
    items = [
        RetentionPolicyItem.model_validate(row) for row in retention_svc.list_policies()
    ]
    return RetentionPolicyListResponse(items=items)


@router.post("/retention-policies/dry-run", response_model=RetentionDryRunResponse)
def retention_policies_dry_run(
    payload: RetentionDryRunRequest | None = None,
    policy_id: int | None = Query(
        default=None, description="특정 정책만 미리보기. 생략 시 전체"
    ),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> RetentionDryRunResponse:
    """보존 기간 초과 데이터 드라이런 — 삭제·익명화 대상 건수·샘플."""
    overrides = None
    if payload and payload.policies:
        overrides = [p.model_dump(exclude_unset=True) for p in payload.policies]
    items = RetentionService(db).dry_run(policy_id=policy_id, overrides=overrides)
    if policy_id is not None and not items:
        raise HTTPException(status_code=404, detail="보존 정책을 찾을 수 없습니다.")
    total = sum(i.expired_count for i in items if i.is_active)
    return RetentionDryRunResponse(items=items, total_affected=total)


@router.patch("/retention-policies", response_model=RetentionPolicyListResponse)
def update_retention_policies(
    payload: RetentionPolicyBulkUpdate,
    request: Request,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> RetentionPolicyListResponse:
    changes: list[dict] = []
    for patch in payload.policies:
        policy = db.get(RetentionPolicy, patch.id)
        if policy is None:
            raise HTTPException(
                status_code=404,
                detail=f"보존 정책 id={patch.id} 를 찾을 수 없습니다.",
            )
        before = {
            "retention_days": policy.retention_days,
            "expiry_action": policy.expiry_action,
            "is_active": policy.is_active,
            "notes": policy.notes,
        }
        data = patch.model_dump(exclude_unset=True)
        data.pop("id", None)
        if "retention_days" in data and data["retention_days"] is not None:
            policy.retention_days = data["retention_days"]
        if "expiry_action" in data and data["expiry_action"]:
            if data["expiry_action"] not in ("delete", "archive", "anonymize"):
                raise HTTPException(
                    status_code=422, detail="만료 처리 값이 올바르지 않습니다."
                )
            policy.expiry_action = data["expiry_action"]
        if "is_active" in data and data["is_active"] is not None:
            policy.is_active = data["is_active"]
        if "notes" in data:
            policy.notes = data["notes"].strip() if data["notes"] else None
        changes.append({"id": patch.id, "before": before, "after": data})

    AuditService(db).record_admin_action(
        actor_id=admin.id,
        action_type=AdminAction.UPDATE,
        target_type="retention_policy",
        target_id="bulk",
        detail={"changes": changes},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    retention_svc = RetentionService(db)
    items = [
        RetentionPolicyItem.model_validate(row) for row in retention_svc.list_policies()
    ]
    return RetentionPolicyListResponse(items=items)


@router.post("/data-integrity/run", response_model=IntegrityRunResponse)
def run_data_integrity(
    request: Request,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> IntegrityRunResponse:
    """행정구역·영상·인증·검색 체인 정합성 검사 실행."""
    integrity_svc = IntegrityService(db)
    previous_total = integrity_svc.get_previous_total()
    checks, total_issues = integrity_svc.run_suite()
    delta_issues = total_issues - previous_total if previous_total is not None else None
    run_id = integrity_svc.record_run(
        actor_id=admin.id,
        checks=checks,
        total_issues=total_issues,
        delta_issues=delta_issues,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return IntegrityRunResponse(
        ran_at=kst_now(),
        total_issues=total_issues,
        checks=checks,
        delta_issues=delta_issues,
        run_id=run_id,
    )


@router.get("/data-integrity/last", response_model=IntegrityRunResponse)
def get_last_data_integrity(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> IntegrityRunResponse:
    """가장 최근 정합성 검사 결과 (감사 로그에서 복원)."""
    result = IntegrityService(db).latest_run()
    if result is None:
        raise HTTPException(status_code=404, detail="저장된 검사 이력이 없습니다.")
    return result


@router.get("/data-integrity/runs/{run_id}", response_model=IntegrityRunResponse)
def get_data_integrity_run(
    run_id: str,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> IntegrityRunResponse:
    """감사 로그 ID로 정합성 검사 결과 복원."""
    result = IntegrityService(db).get_run_by_id(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="검사 이력을 찾을 수 없습니다.")
    return result


@router.get(
    "/data-integrity/checks/{check_id}/issues",
    response_model=IntegrityCheckIssuesResponse,
)
def get_data_integrity_check_issues(
    check_id: str,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> IntegrityCheckIssuesResponse:
    """검사 항목별 전체 이슈 목록 (샘플 제한 없음)."""
    check = IntegrityService(db).find_check(check_id, sample_limit=None)
    if check is None:
        raise HTTPException(status_code=404, detail="검사 항목을 찾을 수 없습니다.")
    return IntegrityCheckIssuesResponse(
        check_id=check.check_id,
        label=check.label,
        issue_count=check.issue_count,
        issues=check.samples,
    )


@router.get("/data-integrity/report.csv")
def download_integrity_report_csv(
    source: str = Query(
        default="last",
        pattern="^(last|fresh)$",
        description="last: 저장된 최근 결과 | fresh: 지금 다시 검사",
    ),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> Response:
    """정합성 검사 결과 CSV보내기."""
    if source == "fresh":
        checks, _total = IntegrityService(db).run_suite()
        filename = "integrity_report_fresh.csv"
    else:
        last = IntegrityService(db).latest_run()
        if last is None:
            raise HTTPException(status_code=404, detail="저장된 검사 결과가 없습니다.")
        checks = last.checks
        filename = "integrity_report.csv"
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(
        [
            "check_id",
            "label",
            "target",
            "status",
            "issue_count",
            "description",
            "samples",
        ]
    )
    for c in checks:
        writer.writerow(
            [
                c.check_id,
                c.label,
                c.target,
                c.status,
                c.issue_count,
                c.description,
                "; ".join(c.samples),
            ]
        )
    body = "\ufeff" + buf.getvalue()
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )