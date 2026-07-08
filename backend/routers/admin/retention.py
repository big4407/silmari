"""
[화면] DataViews.jsx, RetentionDryRunModal.jsx
[서비스] retention_service
[테이블] retention_policy
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from backend.deps import require_roles
from backend.db.database import get_db
from backend.db.models import AdminAction, RetentionPolicy, User, UserRole
from backend.schemas.retention_schema import (
    RetentionDryRunRequest,
    RetentionDryRunResponse,
    RetentionPolicyBulkUpdate,
    RetentionPolicyItem,
    RetentionPolicyListResponse,
)
from backend.services.audit_service import record_admin_action
from backend.services.retention_service import dry_run_retention, list_retention_policies

from .tags import TAG_RETENTION

router = APIRouter()


@router.get(
    "/retention-policies",
    response_model=RetentionPolicyListResponse,
    summary="데이터 보존 정책 조회",
    tags=TAG_RETENTION,
)
def get_retention_policies(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> RetentionPolicyListResponse:
    items = [RetentionPolicyItem.model_validate(row) for row in list_retention_policies(db)]
    return RetentionPolicyListResponse(items=items)


@router.post(
    "/retention-policies/dry-run",
    response_model=RetentionDryRunResponse,
    summary="보존 정책 시뮬레이션",
    tags=TAG_RETENTION,
)
def retention_policies_dry_run(
    payload: RetentionDryRunRequest | None = None,
    policy_id: int | None = Query(
        default=None, description="특정 정책만 미리보기. 생략 시 전체"
    ),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> RetentionDryRunResponse:
    overrides = None
    if payload and payload.policies:
        overrides = [p.model_dump(exclude_unset=True) for p in payload.policies]
    items = dry_run_retention(db, policy_id=policy_id, overrides=overrides)
    if policy_id is not None and not items:
        raise HTTPException(status_code=404, detail="보존 정책을 찾을 수 없습니다.")
    total = sum(i.expired_count for i in items if i.is_active)
    return RetentionDryRunResponse(items=items, total_affected=total)


@router.patch(
    "/retention-policies",
    response_model=RetentionPolicyListResponse,
    summary="보존 정책 일괄 수정",
    tags=TAG_RETENTION,
)
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
                raise HTTPException(status_code=422, detail="만료 처리 값이 올바르지 않습니다.")
            policy.expiry_action = data["expiry_action"]
        if "is_active" in data and data["is_active"] is not None:
            policy.is_active = data["is_active"]
        if "notes" in data:
            policy.notes = data["notes"].strip() if data["notes"] else None
        changes.append({"id": patch.id, "before": before, "after": data})

    record_admin_action(
        db,
        actor_id=admin.id,
        action_type=AdminAction.UPDATE,
        target_type="retention_policy",
        target_id="bulk",
        detail={"changes": changes},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    items = [RetentionPolicyItem.model_validate(row) for row in list_retention_policies(db)]
    return RetentionPolicyListResponse(items=items)
