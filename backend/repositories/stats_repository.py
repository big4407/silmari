"""
관리자 통계 조회용 리포지토리.

기존 ORM 모델(Video, VideoDetail, Search, Analysis, AnalysisDetail, CaseEvent,
StatsExportLog)을 직접 쿼리한다. 집계 결과(요약·지역별·유형별·일별 등)는
video_repository.get_daily_summary()와 같은 기존 패턴대로 dict로 반환하고,
CaseEvent/StatsExportLog처럼 실제 엔티티가 있는 건 ORM 객체를 그대로 반환한다.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, and_, case, cast, distinct, func, select
from sqlalchemy.orm import Session

from backend.db.models import (
    Analysis,
    AnalysisDetail,
    CaseEvent,
    Search,
    StatsExportLog,
    Video,
    VideoDetail,
)

UNCLASSIFIED_REGION = "미분류"
UNSPECIFIED_VALUE = "미입력"


def _period(column, start_at: datetime, end_at: datetime):
    return and_(column >= start_at, column < end_at)


class StatsRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── CCTV 통계 ────────────────────────────────────────────────────────
    def get_cctv_stats(
        self, start_at: datetime, end_at: datetime, region: str | None
    ) -> dict:
        conditions = [_period(Video.created_at, start_at, end_at)]
        if region:
            conditions.append(Video.region_code == region)

        join = Video.__table__.outerjoin(
            VideoDetail.__table__, VideoDetail.video_id == Video.id
        )

        summary_stmt = (
            select(
                func.count(distinct(Video.id)).label("registered_videos"),
                func.count(distinct(VideoDetail.video_id)).label("indexed_videos"),
                func.count(distinct(Video.region_code)).label("covered_regions"),
            )
            .select_from(join)
            .where(*conditions)
        )
        summary = dict(self.db.execute(summary_stmt).one()._mapping)

        person_stmt = (
            select(func.count().label("detected_persons"))
            .select_from(VideoDetail.__table__.join(Video.__table__, VideoDetail.video_id == Video.id))
            .where(*conditions)
        )
        summary["detected_persons"] = (
            self.db.execute(person_stmt).scalar_one_or_none() or 0
        )

        region_col = func.coalesce(Video.region_code, UNCLASSIFIED_REGION)
        region_stmt = (
            select(
                region_col.label("region"),
                func.count(distinct(Video.id)).label("registered_videos"),
                func.count(distinct(VideoDetail.video_id)).label("indexed_videos"),
                func.count(VideoDetail.video_id).label("detected_persons"),
            )
            .select_from(join)
            .where(*conditions)
            .group_by(region_col)
            .order_by(func.count(distinct(Video.id)).desc())
        )
        by_region = [dict(row._mapping) for row in self.db.execute(region_stmt).all()]

        return {"summary": summary, "by_region": by_region}

    # ── 검색 통계 ────────────────────────────────────────────────────────
    def _search_level_subquery(
        self, start_at: datetime, end_at: datetime, search_type_filter: str | None
    ):
        conditions = [_period(Search.searched_at, start_at, end_at)]
        if search_type_filter:
            conditions.append(Search.search_type == search_type_filter)

        search_date = func.date(Search.searched_at)
        join = Search.__table__.outerjoin(
            Analysis.__table__, Analysis.search_id == Search.id
        ).outerjoin(
            AnalysisDetail.__table__, AnalysisDetail.analysis_id == Analysis.id
        )

        return (
            select(
                Search.id.label("search_id"),
                func.coalesce(cast(Search.search_type, String), "UNKNOWN").label(
                    "search_type"
                ),
                search_date.label("search_date"),
                func.max(AnalysisDetail.matching_rate).label("top_similarity"),
            )
            .select_from(join)
            .where(*conditions)
            .group_by(
                Search.id,
                func.coalesce(cast(Search.search_type, String), "UNKNOWN"),
                search_date,
            )
            .subquery()
        )

    def get_search_stats(
        self, start_at: datetime, end_at: datetime, search_type_filter: str | None,
        match_threshold: float,
    ) -> dict:
        q = self._search_level_subquery(start_at, end_at, search_type_filter)
        success_expr = case((q.c.top_similarity >= match_threshold, 1), else_=0)

        summary_stmt = select(
            func.count(q.c.search_id).label("total_searches"),
            func.coalesce(func.sum(success_expr), 0).label("successful_matches"),
            func.coalesce(func.avg(q.c.top_similarity), 0.0).label("average_similarity"),
        )
        summary = dict(self.db.execute(summary_stmt).one()._mapping)
        summary["average_processing_ms"] = 0.0  # analysis에 처리시간 컬럼이 없음

        type_stmt = (
            select(
                q.c.search_type,
                func.count(q.c.search_id).label("count"),
                func.coalesce(func.sum(success_expr), 0).label("successful_matches"),
            )
            .group_by(q.c.search_type)
            .order_by(func.count(q.c.search_id).desc())
        )
        by_type = [dict(row._mapping) for row in self.db.execute(type_stmt).all()]

        daily_stmt = (
            select(
                q.c.search_date.label("date"),
                func.count(q.c.search_id).label("search_count"),
                func.coalesce(func.sum(success_expr), 0).label("successful_count"),
            )
            .group_by(q.c.search_date)
            .order_by(q.c.search_date.asc())
        )
        daily = [dict(row._mapping) for row in self.db.execute(daily_stmt).all()]

        return {"summary": summary, "by_type": by_type, "daily": daily}

    # ── 성별·연령·지역별 통계 ───────────────────────────────────────────
    def get_demographic_stats(self, start_at: datetime, end_at: datetime) -> dict:
        period = _period(Search.searched_at, start_at, end_at)

        gender_col = func.coalesce(cast(Search.gender, String), UNSPECIFIED_VALUE)
        gender_stmt = (
            select(gender_col.label("label"), func.count().label("count"))
            .where(period)
            .group_by(gender_col)
            .order_by(func.count().desc())
        )

        age_group = case(
            (Search.age.is_(None), UNSPECIFIED_VALUE),
            (Search.age < 10, "10세 미만"),
            (Search.age < 20, "10대"),
            (Search.age < 30, "20대"),
            (Search.age < 40, "30대"),
            (Search.age < 50, "40대"),
            (Search.age < 60, "50대"),
            (Search.age < 70, "60대"),
            else_="70세 이상",
        )
        age_stmt = (
            select(age_group.label("label"), func.count().label("count"))
            .where(period)
            .group_by(age_group)
            .order_by(func.count().desc())
        )

        region_col = func.coalesce(Search.missing_location, UNCLASSIFIED_REGION)
        region_stmt = (
            select(region_col.label("region"), func.count().label("search_requests"))
            .where(period)
            .group_by(region_col)
            .order_by(func.count().desc())
        )

        return {
            "gender": [dict(row._mapping) for row in self.db.execute(gender_stmt).all()],
            "age": [dict(row._mapping) for row in self.db.execute(age_stmt).all()],
            "regions": [dict(row._mapping) for row in self.db.execute(region_stmt).all()],
        }

    def get_search_snapshot(self, search_id: int) -> dict | None:
        stmt = select(
            Search.id.label("search_id"),
            Search.searched_at.label("reported_at"),
            Search.missing_location.label("region"),
        ).where(Search.id == search_id)
        row = self.db.execute(stmt).first()
        if row is None:
            return None
        snapshot = dict(row._mapping)
        snapshot["case_key"] = f"SEARCH-{snapshot['search_id']}"  # search에 별도 사건 식별 컬럼 없음
        return snapshot

    # ── 사건 진행(발견/해결) 기록 ────────────────────────────────────────
    def find_case_event(self, case_key: str, event_type: str) -> CaseEvent | None:
        return (
            self.db.query(CaseEvent)
            .filter(CaseEvent.case_key == case_key, CaseEvent.event_type == event_type)
            .order_by(CaseEvent.occurred_at.asc())
            .first()
        )

    def create_case_event(self, values: dict) -> CaseEvent:
        event = CaseEvent(**values)
        self.db.add(event)
        self.db.flush()
        return event

    def list_case_events(
        self,
        start_at: datetime,
        end_at: datetime,
        *,
        event_type: str | None = None,
        case_key: str | None = None,
        limit: int = 200,
    ) -> list[CaseEvent]:
        query = self.db.query(CaseEvent).filter(
            CaseEvent.occurred_at >= start_at, CaseEvent.occurred_at < end_at
        )
        if event_type:
            query = query.filter(CaseEvent.event_type == event_type)
        if case_key:
            query = query.filter(CaseEvent.case_key == case_key)
        return query.order_by(CaseEvent.occurred_at.desc()).limit(limit).all()

    # ── 내보내기 이력 ────────────────────────────────────────────────────
    def create_export_log(self, values: dict) -> StatsExportLog:
        log = StatsExportLog(**values)
        self.db.add(log)
        self.db.flush()
        return log

    def list_export_logs(self, limit: int = 50) -> list[StatsExportLog]:
        return (
            self.db.query(StatsExportLog)
            .order_by(StatsExportLog.created_at.desc())
            .limit(limit)
            .all()
        )