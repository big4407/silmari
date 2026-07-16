from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Date, and_, case, cast, distinct, func, insert, literal, select
from sqlalchemy.orm import Session

from .config import SOURCE_MAP, StatsSourceMap
from .models import stats_case_event, stats_export_log
from .table_registry import StatsTableRegistry

UNCLASSIFIED_REGION = "미분류"
UNSPECIFIED_VALUE = "미입력"


def _row_dict(row: Any) -> dict[str, Any]:
    return dict(row._mapping)


class StatsRepository:
    def __init__(
        self,
        db: Session,
        source_map: StatsSourceMap = SOURCE_MAP,
    ):
        self.db = db
        self.map = source_map
        self.tables = StatsTableRegistry(db)

    @staticmethod
    def _period(col, start_at: datetime, end_at: datetime):
        return and_(col >= start_at, col < end_at)

    def get_cctv_stats(
        self,
        start_at: datetime,
        end_at: datetime,
        region: str | None,
    ) -> dict[str, Any]:
        m = self.map
        video = self.tables.table(m.video_table)
        detail = self.tables.table(m.video_detail_table)

        v_id = self.tables.column(video, m.video_id)
        v_created = self.tables.column(video, m.video_created_at)
        v_status = self.tables.column(video, m.video_status)
        v_region = self.tables.column(video, m.video_region)

        d_video_id = self.tables.column(detail, m.video_detail_video_id)
        d_track = self.tables.column(detail, m.video_detail_track_id, required=False)

        conditions = [self._period(v_created, start_at, end_at)]
        if region:
            conditions.append(v_region == region)

        summary_stmt = (
            select(
                func.count(distinct(v_id)).label("registered_videos"),
                func.count(
                    distinct(
                        case(
                            (v_status == m.video_completed_value, v_id),
                            else_=None,
                        )
                    )
                ).label("indexed_videos"),
                func.count(distinct(v_region)).label("covered_regions"),
            )
            .select_from(video)
            .where(*conditions)
        )
        summary = _row_dict(self.db.execute(summary_stmt).one())

        person_expression = (
            func.count(distinct(d_track)) if d_track is not None else func.count()
        )
        person_stmt = (
            select(person_expression.label("detected_persons"))
            .select_from(detail.join(video, d_video_id == v_id))
            .where(*conditions)
        )
        summary["detected_persons"] = self.db.execute(person_stmt).scalar_one_or_none() or 0

        region_person_expression = (
            func.count(distinct(d_track))
            if d_track is not None
            else func.count(d_video_id)
        )
        region_stmt = (
            select(
                func.coalesce(v_region, UNCLASSIFIED_REGION).label("region"),
                func.count(distinct(v_id)).label("registered_videos"),
                func.count(
                    distinct(
                        case(
                            (v_status == m.video_completed_value, v_id),
                            else_=None,
                        )
                    )
                ).label("indexed_videos"),
                region_person_expression.label("detected_persons"),
            )
            .select_from(video.outerjoin(detail, d_video_id == v_id))
            .where(*conditions)
            .group_by(func.coalesce(v_region, UNCLASSIFIED_REGION))
            .order_by(func.count(distinct(v_id)).desc())
        )
        by_region = [_row_dict(row) for row in self.db.execute(region_stmt).all()]

        return {"summary": summary, "by_region": by_region}

    def _search_level_subquery(
        self,
        start_at: datetime,
        end_at: datetime,
        search_type_filter: str | None,
    ):
        m = self.map
        search = self.tables.table(m.search_table)
        analysis = self.tables.table(m.analysis_table)
        detail = self.tables.table(m.analysis_detail_table)

        s_id = self.tables.column(search, m.search_id)
        s_created = self.tables.column(search, m.search_created_at)
        s_type = self.tables.column(search, m.search_type)

        a_id = self.tables.column(analysis, m.analysis_id)
        a_search_id = self.tables.column(analysis, m.analysis_search_id)
        a_processing = self.tables.column(
            analysis,
            m.analysis_processing_ms,
            required=False,
        )

        d_analysis_id = self.tables.column(detail, m.analysis_detail_analysis_id)
        d_similarity = self.tables.column(detail, m.analysis_detail_similarity)

        conditions = [self._period(s_created, start_at, end_at)]
        if search_type_filter:
            conditions.append(s_type == search_type_filter)

        processing_expression = func.max(a_processing) if a_processing is not None else literal(0.0)

        return (
            select(
                s_id.label("search_id"),
                func.coalesce(s_type, "UNKNOWN").label("search_type"),
                cast(s_created, Date).label("search_date"),
                func.max(d_similarity).label("top_similarity"),
                processing_expression.label("processing_ms"),
            )
            .select_from(
                search.outerjoin(analysis, a_search_id == s_id).outerjoin(
                    detail,
                    d_analysis_id == a_id,
                )
            )
            .where(*conditions)
            .group_by(
                s_id,
                func.coalesce(s_type, "UNKNOWN"),
                cast(s_created, Date),
            )
            .subquery()
        )

    def get_search_stats(
        self,
        start_at: datetime,
        end_at: datetime,
        search_type_filter: str | None,
    ) -> dict[str, Any]:
        q = self._search_level_subquery(start_at, end_at, search_type_filter)
        threshold = self.map.match_threshold

        success_expr = case((q.c.top_similarity >= threshold, 1), else_=0)

        summary_stmt = select(
            func.count(q.c.search_id).label("total_searches"),
            func.coalesce(func.sum(success_expr), 0).label("successful_matches"),
            func.coalesce(func.avg(q.c.top_similarity), 0.0).label("average_similarity"),
            func.coalesce(func.avg(q.c.processing_ms), 0.0).label("average_processing_ms"),
        )
        summary = _row_dict(self.db.execute(summary_stmt).one())

        type_stmt = (
            select(
                q.c.search_type,
                func.count(q.c.search_id).label("count"),
                func.coalesce(func.sum(success_expr), 0).label("successful_matches"),
            )
            .group_by(q.c.search_type)
            .order_by(func.count(q.c.search_id).desc())
        )
        by_type = [_row_dict(row) for row in self.db.execute(type_stmt).all()]

        daily_stmt = (
            select(
                q.c.search_date.label("date"),
                func.count(q.c.search_id).label("search_count"),
                func.coalesce(func.sum(success_expr), 0).label("successful_count"),
            )
            .group_by(q.c.search_date)
            .order_by(q.c.search_date.asc())
        )
        daily = [_row_dict(row) for row in self.db.execute(daily_stmt).all()]

        return {"summary": summary, "by_type": by_type, "daily": daily}

    def get_demographic_stats(
        self,
        start_at: datetime,
        end_at: datetime,
    ) -> dict[str, Any]:
        m = self.map
        search = self.tables.table(m.search_table)

        s_created = self.tables.column(search, m.search_created_at)
        s_gender = self.tables.column(search, m.search_gender)
        s_age = self.tables.column(search, m.search_age)
        s_region = self.tables.column(search, m.search_region)
        period = self._period(s_created, start_at, end_at)

        gender_stmt = (
            select(
                func.coalesce(s_gender, UNSPECIFIED_VALUE).label("label"),
                func.count().label("count"),
            )
            .select_from(search)
            .where(period)
            .group_by(func.coalesce(s_gender, UNSPECIFIED_VALUE))
            .order_by(func.count().desc())
        )

        age_group = case(
            (s_age.is_(None), UNSPECIFIED_VALUE),
            (s_age < 10, "10세 미만"),
            (s_age < 20, "10대"),
            (s_age < 30, "20대"),
            (s_age < 40, "30대"),
            (s_age < 50, "40대"),
            (s_age < 60, "50대"),
            (s_age < 70, "60대"),
            else_="70세 이상",
        )

        age_stmt = (
            select(age_group.label("label"), func.count().label("count"))
            .select_from(search)
            .where(period)
            .group_by(age_group)
            .order_by(func.count().desc())
        )

        region_stmt = (
            select(
                func.coalesce(s_region, UNCLASSIFIED_REGION).label("region"),
                func.count().label("search_requests"),
            )
            .select_from(search)
            .where(period)
            .group_by(func.coalesce(s_region, UNCLASSIFIED_REGION))
            .order_by(func.count().desc())
        )

        return {
            "gender": [_row_dict(row) for row in self.db.execute(gender_stmt).all()],
            "age": [_row_dict(row) for row in self.db.execute(age_stmt).all()],
            "regions": [_row_dict(row) for row in self.db.execute(region_stmt).all()],
        }

    def get_search_snapshot(
        self,
        search_id: int,
    ) -> dict[str, Any] | None:
        m = self.map
        search = self.tables.table(m.search_table)

        s_id = self.tables.column(search, m.search_id)
        s_created = self.tables.column(search, m.search_created_at)
        s_region = self.tables.column(search, m.search_region)
        s_case_key = self.tables.column(search, m.search_case_key, required=False)

        columns = [
            s_id.label("search_id"),
            s_created.label("reported_at"),
            s_region.label("region"),
        ]
        if s_case_key is not None:
            columns.append(s_case_key.label("case_key"))

        stmt = select(*columns).select_from(search).where(s_id == search_id)
        row = self.db.execute(stmt).first()
        return _row_dict(row) if row else None

    def find_case_event(
        self,
        case_key: str,
        event_type: str,
    ) -> dict[str, Any] | None:
        stmt = (
            select(stats_case_event)
            .where(
                stats_case_event.c.case_key == case_key,
                stats_case_event.c.event_type == event_type,
            )
            .order_by(stats_case_event.c.occurred_at.asc())
            .limit(1)
        )
        row = self.db.execute(stmt).first()
        return _row_dict(row) if row else None

    def create_case_event(
        self,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        stmt = insert(stats_case_event).values(**values).returning(stats_case_event)
        row = self.db.execute(stmt).one()
        return _row_dict(row)

    def list_case_events(
        self,
        start_at: datetime,
        end_at: datetime,
        *,
        event_type: str | None = None,
        case_key: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        conditions = [
            stats_case_event.c.occurred_at >= start_at,
            stats_case_event.c.occurred_at < end_at,
        ]
        if event_type:
            conditions.append(stats_case_event.c.event_type == event_type)
        if case_key:
            conditions.append(stats_case_event.c.case_key == case_key)

        stmt = (
            select(stats_case_event)
            .where(*conditions)
            .order_by(stats_case_event.c.occurred_at.desc())
            .limit(limit)
        )
        return [_row_dict(row) for row in self.db.execute(stmt).all()]

    def create_export_log(
        self,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        stmt = insert(stats_export_log).values(**values).returning(stats_export_log)
        row = self.db.execute(stmt).one()
        return _row_dict(row)

    def list_export_logs(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(stats_export_log)
            .order_by(stats_export_log.c.created_at.desc())
            .limit(limit)
        )
        return [_row_dict(row) for row in self.db.execute(stmt).all()]
