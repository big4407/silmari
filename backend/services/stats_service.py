"""
관리자 통계 비즈니스 로직 — CCTV·검색·인구통계·발견해결결과.

[흐름] routers/stats.py → StatsService → StatsRepository(Video/Search/
Analysis/AnalysisDetail) + MissingPersonCaseRepository(발견/해결 결과)
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.repositories.missing_person_case_repository import (
    MissingPersonCaseRepository,
)
from backend.repositories.stats_repository import StatsRepository
from backend.schemas.stats_schema import (
    CctvRegionItem,
    CctvStatsResponse,
    CctvSummary,
    DailySearchItem,
    DemographicStatsResponse,
    DistributionItem,
    ExportLogItem,
    MissingPersonCaseSummaryItem,
    OutcomeRegionItem,
    OutcomeStatsResponse,
    OutcomeSummary,
    PeriodResponse,
    RegionDemographicItem,
    SearchStatsResponse,
    SearchSummary,
    SearchTypeItem,
)

UNCLASSIFIED_REGION = "미분류"

# 검색 1건이 "성공적으로 매칭됐다"고 볼 코사인 유사도 최소값. 데이터가 쌓이면
# 재조정 필요(services/analysis_service.py의 DEFAULT_MIN_SIMILARITY와는 다른
# 목적 — 그쪽은 후보를 걸러내는 값이고, 이건 통계에서 "성공"으로 셀지 판단하는 값).
MATCH_THRESHOLD = 0.75

# analysis_detail.matching_rate가 0~1 범위라 화면에는 %로 보여준다.
SIMILARITY_MULTIPLIER = 100.0


class StatsService:
    def __init__(
        self,
        db: Session,
        repository: StatsRepository | None = None,
        case_repository: MissingPersonCaseRepository | None = None,
    ):
        self.db = db
        self.repository = repository or StatsRepository(db)
        self.case_repository = case_repository or MissingPersonCaseRepository(db)

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
        resolved_by_region = self.case_repository.get_resolved_counts_by_region(
            start_at, end_at
        )

        by_region = []
        for row in raw["regions"]:
            region = str(row["region"])
            searches = int(row["search_requests"] or 0)
            resolved = resolved_by_region.get(region, 0)
            by_region.append(
                RegionDemographicItem(
                    region=region,
                    search_requests=searches,
                    resolved_cases=resolved,
                    resolution_rate=self.rate(resolved, searches),
                )
            )

        return DemographicStatsResponse(
            period=period,
            gender_distribution=self._distribution(raw["gender"]),
            age_distribution=self._distribution(raw["age"]),
            by_region=by_region,
        )

    # ── 발견/해결 결과(실종자 관리 케이스 기준) ────────────────────────────
    def get_outcomes(
        self, from_date: date | None, to_date: date | None, region: str | None
    ) -> OutcomeStatsResponse:
        period, start_at, end_at = self.resolve_period(from_date, to_date)

        summary_raw = self.case_repository.get_outcome_summary(start_at, end_at)
        summary = OutcomeSummary(
            total_cases=summary_raw["total_cases"],
            resolved_cases=summary_raw["resolved_cases"],
            pending_cases=summary_raw["pending_cases"],
            resolution_rate=self.rate(
                summary_raw["resolved_cases"], summary_raw["total_cases"]
            ),
            average_resolution_hours=summary_raw["average_resolution_hours"],
        )

        region_rows = self.case_repository.get_outcome_by_region(start_at, end_at)
        if region:
            region_rows = [row for row in region_rows if row["region"] == region]
        by_region = [
            OutcomeRegionItem(
                region=str(row["region"]),
                total_cases=int(row["total_cases"] or 0),
                resolved_cases=int(row["resolved_cases"] or 0),
                resolution_rate=self.rate(
                    int(row["resolved_cases"] or 0), int(row["total_cases"] or 0)
                ),
            )
            for row in region_rows
        ]

        cases, _ = self.case_repository.find_all(page=1, per_page=200)
        recent_cases = [
            MissingPersonCaseSummaryItem(
                id=c.id,
                sn=c.sn,
                missing_name=c.missing_name,
                gender=c.gender.value if c.gender else None,
                age=c.age,
                missing_location=c.missing_location,
                status=c.status.value,
                assigned_investigator_name=(
                    c.assigned_investigator.full_name or c.assigned_investigator.username
                    if c.assigned_investigator
                    else None
                ),
                assigned_at=c.assigned_at,
                resolved_at=c.resolved_at,
                created_at=c.created_at,
            )
            for c in cases
            if start_at <= c.created_at < end_at
            and (not region or (c.missing_location or UNCLASSIFIED_REGION) == region)
        ]

        return OutcomeStatsResponse(
            period=period,
            summary=summary,
            by_region=by_region,
            recent_cases=recent_cases,
        )

    def list_exports(self, limit: int = 50) -> list[ExportLogItem]:
        # ORM 속성명(from_dt/to_dt)과 API 응답 필드명(from_date/to_date)이
        # 다르므로 여기서 명시적으로 매핑한다 — ORM 쪽은 MariaDB 예약어
        # (TO_DATE) 충돌 회피용 이름, API 쪽은 프론트가 이미 쓰고 있는
        # 기존 계약(GET /stats/exports 응답의 from_date/to_date)을 유지.
        logs = self.repository.list_export_logs(limit)
        return [
            ExportLogItem(
                id=log.id,
                stat_type=log.stat_type,
                from_date=log.from_dt,
                to_date=log.to_dt,
                file_format=log.file_format,
                file_name=log.file_name,
                row_count=log.row_count,
                requested_by_name=log.requested_by_name,
                created_at=log.created_at,
            )
            for log in logs
        ]