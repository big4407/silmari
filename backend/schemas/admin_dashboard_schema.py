"""관리자 콘솔 대시보드 KPI 요약 스키마."""
from __future__ import annotations

from pydantic import BaseModel


class AdminDashboardSummary(BaseModel):
    pending_approvals: int = 0
    in_progress_cases: int = 0
    today_searches: int = 0
    llm_error_rate_24h: float = 0.0
