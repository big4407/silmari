"""
관리자 콘솔 대시보드 KPI 요약.

[흐름] routers/admin.py → AdminDashboardService → 각 도메인 테이블 직접 집계
가벼운 집계 전용이라 CctvCoverageService처럼 별도 서비스로 뺐다(무거운
도메인 서비스를 안 거치고 카운트 쿼리만 실행).
"""
from __future__ import annotations

from datetime import datetime, time, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.db.models import (
    ApprovalStatus,
    LlmCall,
    MissingPersonCase,
    MissingPersonCaseStatus,
    Search,
    User,
)


class AdminDashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_summary(self) -> dict:
        now = datetime.now()
        today_start = datetime.combine(now.date(), time.min)
        last_24h = now - timedelta(hours=24)

        pending_approvals = (
            self.db.query(func.count())
            .select_from(User)
            .filter(User.approval_status == ApprovalStatus.PENDING)
            .scalar()
            or 0
        )

        in_progress_cases = (
            self.db.query(func.count())
            .select_from(MissingPersonCase)
            .filter(MissingPersonCase.status == MissingPersonCaseStatus.IN_PROGRESS)
            .scalar()
            or 0
        )

        today_searches = (
            self.db.query(func.count())
            .select_from(Search)
            .filter(Search.searched_at >= today_start)
            .scalar()
            or 0
        )

        llm_total_24h = (
            self.db.query(func.count())
            .select_from(LlmCall)
            .filter(LlmCall.created_at >= last_24h)
            .scalar()
            or 0
        )
        llm_failed_24h = (
            self.db.query(func.count())
            .select_from(LlmCall)
            .filter(LlmCall.created_at >= last_24h, LlmCall.status == "0")
            .scalar()
            or 0
        )
        llm_error_rate_24h = (
            round(llm_failed_24h / llm_total_24h * 100, 1) if llm_total_24h else 0.0
        )

        return {
            "pending_approvals": pending_approvals,
            "in_progress_cases": in_progress_cases,
            "today_searches": today_searches,
            "llm_error_rate_24h": llm_error_rate_24h,
        }
