"""
관리자 API 패키지 — Swagger 태그별 서브 라우터.

[구조]
  members.py      → Admin · Members
  audit.py        → Admin · Audit
  regions.py      → Admin · Regions
  code_groups.py  → Admin · Code Groups
  retention.py    → Admin · Retention
  integrity.py    → Admin · Data Integrity

[마운트] main.py: app.include_router(admin.router, prefix=API_PREFIX)
"""
from fastapi import APIRouter

from . import audit, code_groups, integrity, members, regions, retention

router = APIRouter(prefix="/admin")
router.include_router(members.router)
router.include_router(audit.router)
router.include_router(regions.router)
router.include_router(code_groups.router)
router.include_router(retention.router)
router.include_router(integrity.router)
