"""
관리자 통계 비즈니스 로직 — CCTV·검색·인구통계·발견해결결과.

[흐름] routers/stats.py → StatsService → StatsRepository (Video/Search/
Analysis/AnalysisDetail/CaseEvent ORM 모델 직접 조회)
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from statistics import mean
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.db.models import CaseEvent, CaseEventType
from backend.repositories.stats_repository import StatsRepository
from backend.schemas.stats_schema import (
    CaseEventCreate,
    CaseEventResponse,
    CctvRegionItem,
    CctvStatsResponse,
    CctvSummary,
    DailySearchItem,
    DemographicStatsResponse,
    DistributionItem,
    OutcomeRegionItem,
    OutcomeStatsResponse,
    OutcomeSummary,
    PeriodResponse,
    RegionDemographicItem,
    SearchStatsResponse,
    SearchSummary,
    SearchTypeItem,
)
from backend.utils.timeutils import kst_now

UNCLASSIFIED_REGION = "미분류"

# 검색 1건이 "성공적으로 매칭됐다"고 볼 코사인 유사도 최소값. 데이터가 쌓이면
# 재조정 필요(services/analysis_service.py의 DEFAULT_MIN_SIMILARITY와는 다른
# 목적 — 그쪽은 후보를 걸러내는 값이고, 이건 통계에서 "성공"으로 셀지 판단하는 값).
MATCH_THRESHOLD = 0.75

# analysis_detail.matching_rate가 0~1 범위라 화면에는 %로 보여준다.
SIMILARITY_MULTIPLIER = 100.0


class StatsService:
    def __init__(self, db: Session, repository: StatsRepository | None = None):
        self.db = db
        self.repository = repository or StatsRepository(db)

    @staticmethod
    def resolve_period(
        from_date: date | None, to_date: date | None
    ) -> tuple[PeriodResponse, datetime, datetime]:
        resolved_to = to_date or date.today()
        resolved_from = from_date or resolved_to - timedelta(days=89)

        if resolved_from > resolved_to:
            raise HTTPException(
                status_code=400, detail="시작일은 종료일보다 늦을 수 없습니다."
            )

        start_at = datetime.combine(resolved_from, time.min)
        end_at = datetime.combine(resolved_to + timedelta(days=1), time.min)

        return (
            PeriodResponse(from_date=resolved_from, to_date=resolved_to),
            start_at,
            end_at,
        )

    @staticmethod
    def rate(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round(numerator / denominator * 100, 1)

    @staticmethod
    def elapsed_hours(start: datetime | None, end: datetime | None) -> float | None:
        if start is None or end is None:
            return None

        if start.tzinfo is None and end.tzinfo is not None:
            start = start.replace(tzinfo=end.tzinfo)
        elif start.tzinfo is not None and end.tzinfo is None:
            end = end.replace(tzinfo=start.tzinfo)

        seconds = (end - start).total_seconds()
        if seconds < 0:
            return None
        return round(seconds / 3600, 1)

    # ── CCTV ─────────────────────────────────────────────────────────────
    def get_cctv(
        self, from_date: date | None, to_date: date | None, region: str | None
    ) -> CctvStatsResponse:
        period, start_at, end_at = self.resolve_period(from_date, to_date)
        raw = self.repository.get_cctv_stats(start_at, end_at, region)
        return CctvStatsResponse(
            period=period,
            summary=CctvSummary(**raw["summary"]),
            by_region=[CctvRegionItem(**row) for row in raw["by_region"]],
        )

    # ── 검색 ─────────────────────────────────────────────────────────────
    def get_search(
        self, from_date: date | None, to_date: date | None, search_type: str | None
    ) -> SearchStatsResponse:
        period, start_at, end_at = self.resolve_period(from_date, to_date)
        raw = self.repository.get_search_stats(
            start_at, end_at, search_type, MATCH_THRESHOLD
        )
        summary_raw = raw["summary"]
        total = int(summary_raw["total_searches"] or 0)
        successful = int(summary_raw["successful_matches"] or 0)

        by_type = []
        for row in raw["by_type"]:
            count = int(row["count"] or 0)
            success = int(row["successful_matches"] or 0)
            by_type.append(
                SearchTypeItem(
                    search_type=str(row["search_type"]),
                    count=count,
                    successful_matches=success,
                    success_rate=self.rate(success, count),
                )
            )

        return SearchStatsResponse(
            period=period,
            summary=SearchSummary(
                total_searches=total,
                successful_matches=successful,
                average_similarity_percent=round(
                    float(summary_raw["average_similarity"] or 0)
                    * SIMILARITY_MULTIPLIER,
                    1,
                ),
                average_processing_seconds=round(
                    float(summary_raw["average_processing_ms"] or 0) / 1000, 2
                ),
            ),
            by_type=by_type,
            daily=[DailySearchItem(**row) for row in raw["daily"]],
        )

    # ── 성별·연령·지역별 ─────────────────────────────────────────────────
    @staticmethod
    def _distribution(rows: list[dict[str, Any]]) -> list[DistributionItem]:
        total = sum(int(row["count"] or 0) for row in rows)
        return [
            DistributionItem(
                label=str(row["label"]),
                count=int(row["count"] or 0),
                ratio=StatsService.rate(int(row["count"] or 0), total),
            )
            for row in rows
        ]

    def get_demographic(
        self, from_date: date | None, to_date: date | None
    ) -> DemographicStatsResponse:
        period, start_at, end_at = self.resolve_period(from_date, to_date)
        raw = self.repository.get_demographic_stats(start_at, end_at)
        outcome = self._build_outcome_aggregates(
            self.repository.list_case_events(start_at, end_at, limit=10000)
        )

        by_region = []
        for row in raw["regions"]:
            region = str(row["region"])
            found = outcome["region_found"].get(region, 0)
            resolved = outcome["region_resolved"].get(region, 0)
            searches = int(row["search_requests"] or 0)
            by_region.append(
                RegionDemographicItem(
                    region=region,
                    search_requests=searches,
                    found_cases=found,
                    resolved_cases=resolved,
                    finding_rate=self.rate(found, searches),
                    resolution_rate=self.rate(resolved, searches),
                )
            )

        return DemographicStatsResponse(
            period=period,
            gender_distribution=self._distribution(raw["gender"]),
            age_distribution=self._distribution(raw["age"]),
            by_region=by_region,
        )

    # ── 발견/해결 결과 기록 ──────────────────────────────────────────────
    def create_case_event(
        self, payload: CaseEventCreate, *, actor_id: str | None, actor_name: str
    ) -> CaseEventResponse:
        snapshot = None
        if payload.source_search_id is not None:
            snapshot = self.repository.get_search_snapshot(payload.source_search_id)
            if snapshot is None:
                raise HTTPException(status_code=404, detail="연결된 검색 기록을 찾을 수 없습니다.")

        case_key = payload.case_key
        if not case_key and snapshot:
            case_key = str(snapshot.get("case_key") or f"SEARCH-{snapshot['search_id']}")
        if not case_key:
            raise HTTPException(status_code=400, detail="사건 식별값을 만들 수 없습니다.")

        if self.repository.find_case_event(case_key, payload.event_type):
            raise HTTPException(
                status_code=409,
                detail=f"{case_key} 사건의 {payload.event_type} 기록이 이미 존재합니다.",
            )

        if payload.event_type == CaseEventType.RESOLVED.value:
            found = self.repository.find_case_event(case_key, CaseEventType.FOUND.value)
            if found is None:
                raise HTTPException(
                    status_code=409,
                    detail="발견(FOUND) 기록이 먼저 등록되어야 해결(RESOLVED) 기록을 추가할 수 있습니다.",
                )
            if payload.occurred_at < found.occurred_at:
                raise HTTPException(
                    status_code=400, detail="해결 시각은 발견 시각보다 이를 수 없습니다."
                )

        reported_at = payload.reported_at or (snapshot or {}).get("reported_at")
        region = payload.region or (snapshot or {}).get("region")

        values = {
            "case_key": case_key,
            "event_type": payload.event_type,
            "occurred_at": payload.occurred_at,
            "reported_at_snapshot": reported_at,
            "region_snapshot": region,
            "actor_id": payload.actor_id,
            "actor_name": payload.actor_name,
            "actor_role": payload.actor_role,
            "recorded_by_id": actor_id,
            "recorded_by_name": actor_name,
            "location_text": payload.location_text,
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "source_search_id": payload.source_search_id,
            "source_analysis_id": payload.source_analysis_id,
            "source_analysis_detail_id": payload.source_analysis_detail_id,
            "note": payload.note,
            "created_at": kst_now(),
        }

        try:
            event = self.repository.create_case_event(values)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return self._event_response(event)

    @staticmethod
    def _event_response(event: CaseEvent) -> CaseEventResponse:
        return CaseEventResponse(
            id=event.id,
            case_key=event.case_key,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            reported_at=event.reported_at_snapshot,
            region=event.region_snapshot,
            actor_name=event.actor_name,
            actor_role=event.actor_role,
            recorded_by_name=event.recorded_by_name,
            location_text=event.location_text,
            source_search_id=event.source_search_id,
            source_analysis_id=event.source_analysis_id,
            source_analysis_detail_id=event.source_analysis_detail_id,
            note=event.note,
            created_at=event.created_at,
        )

    @staticmethod
    def _build_outcome_aggregates(events: list[CaseEvent]) -> dict[str, Any]:
        found_by_case: dict[str, CaseEvent] = {}
        resolved_by_case: dict[str, CaseEvent] = {}

        for event in sorted(events, key=lambda item: item.occurred_at):
            case_key = str(event.case_key)
            if event.event_type == CaseEventType.FOUND.value:
                found_by_case.setdefault(case_key, event)
            elif event.event_type == CaseEventType.RESOLVED.value:
                resolved_by_case.setdefault(case_key, event)

        region_found: dict[str, int] = defaultdict(int)
        region_resolved: dict[str, int] = defaultdict(int)

        for event in found_by_case.values():
            region_found[event.region_snapshot or UNCLASSIFIED_REGION] += 1
        for event in resolved_by_case.values():
            region_resolved[event.region_snapshot or UNCLASSIFIED_REGION] += 1

        return {
            "found_by_case": found_by_case,
            "resolved_by_case": resolved_by_case,
            "region_found": region_found,
            "region_resolved": region_resolved,
        }

    def get_outcomes(
        self, from_date: date | None, to_date: date | None, region: str | None
    ) -> OutcomeStatsResponse:
        period, start_at, end_at = self.resolve_period(from_date, to_date)
        events = self.repository.list_case_events(start_at, end_at, limit=10000)
        if region:
            events = [
                e for e in events if (e.region_snapshot or UNCLASSIFIED_REGION) == region
            ]

        agg = self._build_outcome_aggregates(events)
        found_by_case = agg["found_by_case"]
        resolved_by_case = agg["resolved_by_case"]

        find_hours = [
            value
            for event in found_by_case.values()
            if (value := self.elapsed_hours(event.reported_at_snapshot, event.occurred_at))
            is not None
        ]
        resolve_hours = [
            value
            for event in resolved_by_case.values()
            if (value := self.elapsed_hours(event.reported_at_snapshot, event.occurred_at))
            is not None
        ]

        regions = sorted(set(agg["region_found"]) | set(agg["region_resolved"]))
        by_region = [
            OutcomeRegionItem(
                region=region_name,
                found_cases=agg["region_found"].get(region_name, 0),
                resolved_cases=agg["region_resolved"].get(region_name, 0),
                resolution_rate=self.rate(
                    agg["region_resolved"].get(region_name, 0),
                    agg["region_found"].get(region_name, 0),
                ),
            )
            for region_name in regions
        ]

        return OutcomeStatsResponse(
            period=period,
            summary=OutcomeSummary(
                found_cases=len(found_by_case),
                resolved_cases=len(resolved_by_case),
                resolution_after_found_rate=self.rate(
                    len(resolved_by_case), len(found_by_case)
                ),
                average_hours_to_find=round(mean(find_hours), 1) if find_hours else None,
                average_hours_to_resolve=(
                    round(mean(resolve_hours), 1) if resolve_hours else None
                ),
            ),
            by_region=by_region,
            recent_records=[self._event_response(e) for e in events[:100]],
        )

    def list_events(
        self,
        from_date: date | None,
        to_date: date | None,
        event_type: str | None,
        case_key: str | None,
    ) -> list[CaseEventResponse]:
        _, start_at, end_at = self.resolve_period(from_date, to_date)
        events = self.repository.list_case_events(
            start_at, end_at, event_type=event_type, case_key=case_key
        )
        return [self._event_response(e) for e in events]

    def list_exports(self, limit: int = 50):
        return self.repository.list_export_logs(limit)