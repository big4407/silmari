"""
통계 CSV 내보내기.

CctvCoverageService가 VideoService 옆에 별도로 있는 것과 같은 구성 —
StatsService(집계 조회)를 그대로 조합해서 CSV로 포맷팅만 담당한다.
"""
from __future__ import annotations

import csv
import io
from typing import Any

from sqlalchemy.orm import Session

from backend.repositories.stats_repository import StatsRepository
from backend.schemas.stats_schema import ExportRequest
from backend.services.stats_service import StatsService
from backend.utils.timeutils import kst_now


class StatsExportService:
    def __init__(
        self,
        db: Session,
        service: StatsService | None = None,
        repository: StatsRepository | None = None,
    ):
        self.db = db
        self.repository = repository or StatsRepository(db)
        self.service = service or StatsService(db, self.repository)

    @staticmethod
    def _csv_content(headers: list[str], rows: list[list[Any]]) -> str:
        stream = io.StringIO()
        stream.write("\ufeff")
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)
        return stream.getvalue()

    def build(
        self, request: ExportRequest, *, actor_id: str | None, actor_name: str
    ) -> tuple[str, str, int]:
        if request.from_date > request.to_date:
            raise ValueError("시작일은 종료일보다 늦을 수 없습니다.")

        stat_type = request.stat_type

        if stat_type == "cctv":
            data = self.service.get_cctv(request.from_date, request.to_date, request.region)
            headers = ["지역", "등록 영상", "인덱싱 완료", "감지 인원"]
            rows = [
                [item.region, item.registered_videos, item.indexed_videos, item.detected_persons]
                for item in data.by_region
            ]
        elif stat_type == "search":
            data = self.service.get_search(
                request.from_date, request.to_date, request.search_type
            )
            headers = ["날짜", "검색 건수", "성공 매칭 건수"]
            rows = [
                [item.date.isoformat(), item.search_count, item.successful_count]
                for item in data.daily
            ]
        elif stat_type == "demographic":
            data = self.service.get_demographic(request.from_date, request.to_date)
            headers = ["지역", "검색 요청", "해결", "해결율"]
            rows = [
                [
                    item.region,
                    item.search_requests,
                    item.resolved_cases,
                    item.resolution_rate,
                ]
                for item in data.by_region
            ]
        else:
            data = self.service.get_outcomes(
                request.from_date, request.to_date, request.region
            )
            headers = [
                "SN", "이름", "성별", "나이", "지역", "상태",
                "담당자", "담당 시각", "완료 시각", "생성 시각",
            ]
            rows = [
                [
                    item.sn,
                    item.missing_name or "",
                    item.gender or "",
                    item.age or "",
                    item.missing_location or "",
                    item.status,
                    item.assigned_investigator_name or "",
                    item.assigned_at.isoformat() if item.assigned_at else "",
                    item.resolved_at.isoformat() if item.resolved_at else "",
                    item.created_at.isoformat(),
                ]
                for item in data.recent_cases
            ]

        filename = (
            f"{stat_type}_stats_{request.from_date.isoformat()}_{request.to_date.isoformat()}.csv"
        )
        content = self._csv_content(headers, rows)

        try:
            self.repository.create_export_log(
                {
                    "stat_type": stat_type,
                    "from_dt": request.from_date,
                    "to_dt": request.to_date,
                    "file_format": request.file_format,
                    "file_name": filename,
                    "row_count": len(rows),
                    "requested_by_id": actor_id,
                    "requested_by_name": actor_name,
                    "created_at": kst_now(),
                }
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return filename, content, len(rows)