"""
[화면] DataViews.jsx, IntegrityCheckDetailModal.jsx
[서비스] region_integrity, integrity_audit
[테이블] region, video, admin_history (검사 이력)
"""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.deps import require_roles
from backend.db.database import get_db
from backend.db.models import User, UserRole
from backend.schemas.data_integrity_schema import (
    IntegrityCheckIssuesResponse,
    IntegrityRunResponse,
)
from backend.services.integrity_audit import (
    get_integrity_run_by_id,
    get_previous_integrity_total,
    latest_integrity_run,
    record_integrity_run,
)
from backend.services.region_integrity import find_integrity_check, run_integrity_suite
from backend.utils.timeutils import kst_now

from .tags import TAG_INTEGRITY

router = APIRouter()


@router.post(
    "/data-integrity/run",
    response_model=IntegrityRunResponse,
    summary="데이터 무결성 검사 실행",
    tags=TAG_INTEGRITY,
)
def run_data_integrity(
    request: Request,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> IntegrityRunResponse:
    previous_total = get_previous_integrity_total(db)
    checks, total_issues = run_integrity_suite(db)
    delta_issues = (
        total_issues - previous_total if previous_total is not None else None
    )
    run_id = record_integrity_run(
        db,
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


@router.get(
    "/data-integrity/last",
    response_model=IntegrityRunResponse,
    summary="최근 무결성 검사 결과",
    tags=TAG_INTEGRITY,
)
def get_last_data_integrity(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> IntegrityRunResponse:
    result = latest_integrity_run(db)
    if result is None:
        raise HTTPException(status_code=404, detail="저장된 검사 이력이 없습니다.")
    return result


@router.get(
    "/data-integrity/runs/{run_id}",
    response_model=IntegrityRunResponse,
    summary="무결성 검사 이력 조회",
    tags=TAG_INTEGRITY,
)
def get_data_integrity_run(
    run_id: str,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> IntegrityRunResponse:
    result = get_integrity_run_by_id(db, run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="검사 이력을 찾을 수 없습니다.")
    return result


@router.get(
    "/data-integrity/checks/{check_id}/issues",
    response_model=IntegrityCheckIssuesResponse,
    summary="무결성 검사 이슈 상세",
    tags=TAG_INTEGRITY,
)
def get_data_integrity_check_issues(
    check_id: str,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> IntegrityCheckIssuesResponse:
    check = find_integrity_check(db, check_id, sample_limit=None)
    if check is None:
        raise HTTPException(status_code=404, detail="검사 항목을 찾을 수 없습니다.")
    return IntegrityCheckIssuesResponse(
        check_id=check.check_id,
        label=check.label,
        issue_count=check.issue_count,
        issues=check.samples,
    )


@router.get(
    "/data-integrity/report.csv",
    summary="무결성 검사 CSV 리포트",
    tags=TAG_INTEGRITY,
)
def download_integrity_report_csv(
    source: str = Query(
        default="last",
        pattern="^(last|fresh)$",
        description="last: 저장된 최근 결과 | fresh: 지금 다시 검사",
    ),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> Response:
    if source == "fresh":
        checks, _ = run_integrity_suite(db)
        filename = "integrity_report_fresh.csv"
    else:
        last = latest_integrity_run(db)
        if last is None:
            raise HTTPException(status_code=404, detail="저장된 검사 결과가 없습니다.")
        checks = last.checks
        filename = "integrity_report.csv"
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(
        ["check_id", "label", "target", "status", "issue_count", "description", "samples"]
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
