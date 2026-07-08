"""
[화면] DataViews.jsx, CodeGroupEditModal.jsx
[서비스] code_group_service.build_code_group_list
[테이블] sys_code_group, sys_code_item
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.deps import require_roles
from backend.db.database import get_db
from backend.db.models import AdminAction, SysCodeGroup, SysCodeItem, User, UserRole
from backend.schemas.region_schema import (
    CodeGroupEntry,
    CodeGroupItem,
    CodeGroupListResponse,
    CodeGroupUpdate,
    CodeItemUpdate,
)
from backend.services.audit_service import record_admin_action
from backend.services.code_group_service import build_code_group_list

from .tags import TAG_CODES

router = APIRouter()


@router.get(
    "/code-groups",
    response_model=CodeGroupListResponse,
    summary="시스템 코드 그룹 조회",
    tags=TAG_CODES,
)
def list_code_groups(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> CodeGroupListResponse:
    return build_code_group_list(db)


@router.patch(
    "/code-groups/{group_key}",
    response_model=CodeGroupItem,
    summary="코드 그룹 메타 수정",
    tags=TAG_CODES,
    include_in_schema=False,
)
def update_code_group(
    group_key: str,
    payload: CodeGroupUpdate,
    request: Request,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> CodeGroupItem:
    group = db.get(SysCodeGroup, group_key)
    if group is None:
        raise HTTPException(status_code=404, detail="코드 그룹을 찾을 수 없습니다.")
    before = {"group_label": group.group_label, "description": group.description}
    data = payload.model_dump(exclude_unset=True)
    if "group_label" in data and data["group_label"]:
        group.group_label = data["group_label"].strip()
    if "description" in data:
        group.description = data["description"].strip() if data["description"] else None
    record_admin_action(
        db,
        actor_id=admin.id,
        action_type=AdminAction.UPDATE,
        target_type="code_group",
        target_id=group_key,
        detail={"before": before, "after": data},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    refreshed = build_code_group_list(db)
    for g in refreshed.groups:
        if g.group == group_key:
            return g
    raise HTTPException(status_code=500, detail="갱신된 그룹을 찾지 못했습니다.")


@router.patch(
    "/code-groups/{group_key}/items/{code}",
    response_model=CodeGroupEntry,
    summary="코드 항목 수정",
    tags=TAG_CODES,
)
def update_code_item(
    group_key: str,
    code: str,
    payload: CodeItemUpdate,
    request: Request,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> CodeGroupEntry:
    item = db.scalar(
        select(SysCodeItem).where(
            SysCodeItem.group_key == group_key,
            SysCodeItem.code == code,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="코드 항목을 찾을 수 없습니다.")
    before = {
        "label": item.label,
        "description": item.description,
        "is_active": item.is_active,
    }
    data = payload.model_dump(exclude_unset=True)
    if "label" in data and data["label"]:
        item.label = data["label"].strip()
    if "description" in data:
        item.description = data["description"].strip() if data["description"] else None
    if "is_active" in data and data["is_active"] is not None:
        item.is_active = data["is_active"]
    record_admin_action(
        db,
        actor_id=admin.id,
        action_type=AdminAction.UPDATE,
        target_type="code_item",
        target_id=f"{group_key}:{code}",
        detail={"before": before, "after": data},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    group_list = build_code_group_list(db)
    for g in group_list.groups:
        if g.group == group_key:
            for entry in g.items:
                if entry.code == code:
                    return entry
    raise HTTPException(status_code=500, detail="갱신된 항목을 찾지 못했습니다.")
