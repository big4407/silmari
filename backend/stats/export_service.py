from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from .integration import StatsActor
from .repository import StatsRepository
from .schemas import ExportRequest
from .service import StatsService


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
    def _csv_content(
        headers: list[str],
        rows: list[list[Any]],
    ) -> str:
        stream = io.StringIO()
        stream.write("\ufeff")
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)
        return stream.getvalue()

    def build(
        self,
        request: ExportRequest,
        actor: StatsActor,
    ) -> tuple[str, str, int]:
        if request.from_date > request.to_date:
            raise ValueError("시작일은 종료일보다 늦을 수 없습니다.")

        stat_type = request.stat_type

        if stat_type == "cctv":
            data = self.service.get_cctv(
                request.from_date,
                request.to_date,
                request.region,
            )
            headers = ["지역", "등록 영상", "인덱싱 완료", "감지 인원"]
            rows = [
                [
                    item.region,
                    item.registered_videos,
                    item.indexed_videos,
                    item.detected_persons,
                ]
                for item in data.by_region
            ]
        elif stat_type == "search":
            data = self.service.get_search(
                request.from_date,
                request.to_date,
                request.search_type,
            )
            headers = ["날짜", "검색 건수", "성공 매칭 건수"]
            rows = [
                [
                    item.date.isoformat(),
                    item.search_count,
                    item.successful_count,
                ]
                for item in data.daily
            ]
        elif stat_type == "demographic":
            data = self.service.get_demographic(
                request.from_date,
                request.to_date,
            )
            headers = ["지역", "검색 요청", "발견", "해결", "발견율", "해결율"]
            rows = [
                [
                    item.region,
                    item.search_requests,
                    item.found_cases,
                    item.resolved_cases,
                    item.finding_rate,
                    item.resolution_rate,
                ]
                for item in data.by_region
            ]
        else:
            data = self.service.get_outcomes(
                request.from_date,
                request.to_date,
                request.region,
            )
            headers = [
                "사건 키",
                "구분",
                "발생 시각",
                "신고 시각",
                "지역",
                "대상자",
                "역할",
                "기록자",
                "장소",
                "검색 ID",
                "분석 ID",
                "분석 상세 ID",
                "비고",
            ]
            rows = [
                [
                    item.case_key,
                    item.event_type,
                    item.occurred_at.isoformat(),
                    item.reported_at.isoformat() if item.reported_at else "",
                    item.region or "",
                    item.actor_name or "",
                    item.actor_role or "",
                    item.recorded_by_name,
                    item.location_text or "",
                    item.source_search_id or "",
                    item.source_analysis_id or "",
                    item.source_analysis_detail_id or "",
                    item.note or "",
                ]
                for item in data.recent_records
            ]

        filename = (
            f"{stat_type}_stats_"
            f"{request.from_date.isoformat()}_"
            f"{request.to_date.isoformat()}.csv"
        )
        content = self._csv_content(headers, rows)

        try:
            self.repository.create_export_log(
                {
                    "stat_type": stat_type,
                    "from_date": request.from_date,
                    "to_date": request.to_date,
                    "file_format": request.file_format,
                    "file_name": filename,
                    "row_count": len(rows),
                    "requested_by_id": actor.user_id,
                    "requested_by_name": actor.name,
                    "created_at": datetime.now(timezone.utc),
                }
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return filename, content, len(rows)
