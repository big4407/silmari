"""
실종자 관리 케이스(MissingPersonCase) 리포지토리.
"""
from __future__ import annotations

from datetime import datetime
from statistics import mean

from sqlalchemy import case, func
from sqlalchemy.orm import Session, selectinload

from backend.db.models import MissingPersonCase, MissingPersonCaseStatus


class MissingPersonCaseRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, case_id: int) -> MissingPersonCase | None:
        return (
            self.db.query(MissingPersonCase)
            .options(selectinload(MissingPersonCase.assigned_investigator))
            .filter(MissingPersonCase.id == case_id)
            .first()
        )

    def get_by_sn(self, sn: str) -> MissingPersonCase | None:
        return self.db.query(MissingPersonCase).filter(MissingPersonCase.sn == sn).first()

    def get_status_by_sns(self, sns: list[str]) -> dict[str, str]:
        """sn 목록에 대해 케이스 상태만 가져온다 — 안내문자 목록에 상태 배지를
        붙일 때(Dashboard 실종자 검색탭, 관리자 안내문자 목록) 쓴다."""
        if not sns:
            return {}
        rows = (
            self.db.query(MissingPersonCase.sn, MissingPersonCase.status)
            .filter(MissingPersonCase.sn.in_(sns))
            .all()
        )
        return {sn: status.value for sn, status in rows}

    def exists_by_sn(self, sn: str) -> bool:
        return (
            self.db.query(MissingPersonCase.id)
            .filter(MissingPersonCase.sn == sn)
            .first()
            is not None
        )

    def next_chatbot_sn(self) -> str:
        """"C"+6자리 증가값 — 이미 있는 챗봇 케이스 sn 중 가장 큰 번호 다음값."""
        latest = (
            self.db.query(MissingPersonCase.sn)
            .filter(MissingPersonCase.sn.like("C%"))
            .order_by(MissingPersonCase.sn.desc())
            .first()
        )
        next_seq = 1
        if latest and latest[0][1:].isdigit():
            next_seq = int(latest[0][1:]) + 1
        return f"C{next_seq:06d}"

    def create(self, values: dict) -> MissingPersonCase:
        case = MissingPersonCase(**values)
        self.db.add(case)
        self.db.flush()
        return case

    def find_all(
        self,
        page: int,
        per_page: int,
        *,
        status: str | None = None,
        assigned_investigator_id: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[MissingPersonCase], int]:
        query = self.db.query(MissingPersonCase).options(
            selectinload(MissingPersonCase.assigned_investigator)
        )

        if status:
            query = query.filter(MissingPersonCase.status == status)
        if assigned_investigator_id:
            query = query.filter(
                MissingPersonCase.assigned_investigator_id == assigned_investigator_id
            )
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                (MissingPersonCase.missing_name.like(like))
                | (MissingPersonCase.missing_location.like(like))
                | (MissingPersonCase.sn.like(like))
            )

        total = query.count()
        items = (
            query.order_by(MissingPersonCase.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    # ── 통계용 집계 ──────────────────────────────────────────────────────
    def get_outcome_summary(self, start_at: datetime, end_at: datetime) -> dict:
        period = (
            MissingPersonCase.created_at >= start_at,
            MissingPersonCase.created_at < end_at,
        )

        total = (
            self.db.query(func.count())
            .select_from(MissingPersonCase)
            .filter(*period)
            .scalar()
            or 0
        )
        resolved = (
            self.db.query(func.count())
            .select_from(MissingPersonCase)
            .filter(*period, MissingPersonCase.status == MissingPersonCaseStatus.RESOLVED.value)
            .scalar()
            or 0
        )

        resolved_pairs = (
            self.db.query(MissingPersonCase.assigned_at, MissingPersonCase.resolved_at)
            .filter(
                *period,
                MissingPersonCase.status == MissingPersonCaseStatus.RESOLVED.value,
                MissingPersonCase.assigned_at.isnot(None),
                MissingPersonCase.resolved_at.isnot(None),
            )
            .all()
        )
        hours = [
            (resolved_at - assigned_at).total_seconds() / 3600
            for assigned_at, resolved_at in resolved_pairs
        ]

        return {
            "total_cases": total,
            "resolved_cases": resolved,
            "pending_cases": total - resolved,
            "average_resolution_hours": round(mean(hours), 1) if hours else None,
        }

    def get_outcome_by_region(self, start_at: datetime, end_at: datetime) -> list[dict]:
        period = (
            MissingPersonCase.created_at >= start_at,
            MissingPersonCase.created_at < end_at,
        )
        region_col = func.coalesce(MissingPersonCase.missing_location, "미분류")
        resolved_expr = func.sum(
            case(
                (MissingPersonCase.status == MissingPersonCaseStatus.RESOLVED.value, 1),
                else_=0,
            )
        )

        rows = (
            self.db.query(
                region_col.label("region"),
                func.count().label("total_cases"),
                func.coalesce(resolved_expr, 0).label("resolved_cases"),
            )
            .filter(*period)
            .group_by(region_col)
            .order_by(func.count().desc())
            .all()
        )
        return [dict(row._mapping) for row in rows]

    def get_resolved_counts_by_region(self, start_at: datetime, end_at: datetime) -> dict:
        """성별·연령·지역별 통계 화면(demographic)의 "완료" 건수 — 지역별."""
        region_col = func.coalesce(MissingPersonCase.missing_location, "미분류")
        rows = (
            self.db.query(region_col.label("region"), func.count().label("count"))
            .filter(
                MissingPersonCase.created_at >= start_at,
                MissingPersonCase.created_at < end_at,
                MissingPersonCase.status == MissingPersonCaseStatus.RESOLVED.value,
            )
            .group_by(region_col)
            .all()
        )
        return {row.region: row.count for row in rows}