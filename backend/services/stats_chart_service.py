from __future__ import annotations

import io
from typing import Any

import matplotlib

matplotlib.use("Agg")  # 서버 환경에서 이미지 렌더링
import matplotlib.pyplot as plt

from sqlalchemy.orm import Session

from backend.repositories.stats_repository import StatsRepository
from backend.schemas.stats_schema import ExportRequest
from backend.services.stats_service import StatsService


class StatsChartService:
    def __init__(
        self,
        db: Session,
        service: StatsService | None = None,
        repository: StatsRepository | None = None,
    ):
        self.db = db
        self.repository = repository or StatsRepository(db)
        self.service = service or StatsService(db, self.repository)

        # 한글 폰트 설정 (Windows 기준)
        plt.rcParams["font.family"] = "Malgun Gothic"
        plt.rcParams["axes.unicode_minus"] = False

    @staticmethod
    def _png_content(fig) -> bytes:
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", bbox_inches="tight", dpi=150)
        plt.close(fig)
        buffer.seek(0)
        return buffer.getvalue()

    def build_bar_chart(self, request: ExportRequest) -> tuple[str, bytes]:
        if request.from_date > request.to_date:
            raise ValueError("시작일은 종료일보다 늦을 수 없습니다.")

        stat_type = request.stat_type

        if stat_type == "cctv":
            data = self.service.get_cctv(
                request.from_date, request.to_date, request.region
            )

            labels = [item.region for item in data.by_region]
            registered = [item.registered_videos for item in data.by_region]
            indexed = [item.indexed_videos for item in data.by_region]

            fig, ax = plt.subplots(figsize=(10, 6))
            x = range(len(labels))
            width = 0.35

            ax.bar(
                [i - width / 2 for i in x], registered, width=width, label="등록 영상"
            )
            ax.bar(
                [i + width / 2 for i in x], indexed, width=width, label="인덱싱 완료"
            )

            ax.set_title("지역별 CCTV 영상 통계")
            ax.set_xlabel("지역")
            ax.set_ylabel("건수")
            ax.set_xticks(list(x))
            ax.set_xticklabels(labels, rotation=20)
            ax.legend()

        elif stat_type == "search":
            data = self.service.get_search(
                request.from_date, request.to_date, request.search_type
            )

            labels = [item.date.isoformat() for item in data.daily]
            search_counts = [item.search_count for item in data.daily]
            success_counts = [item.successful_count for item in data.daily]

            fig, ax = plt.subplots(figsize=(12, 6))
            x = range(len(labels))
            width = 0.35

            ax.bar(
                [i - width / 2 for i in x],
                search_counts,
                width=width,
                label="검색 건수",
            )
            ax.bar(
                [i + width / 2 for i in x],
                success_counts,
                width=width,
                label="성공 매칭 건수",
            )

            ax.set_title("일별 검색 통계")
            ax.set_xlabel("날짜")
            ax.set_ylabel("건수")
            ax.set_xticks(list(x))
            ax.set_xticklabels(labels, rotation=45, ha="right")
            ax.legend()

        elif stat_type == "demographic":
            data = self.service.get_demographic(request.from_date, request.to_date)

            labels = [item.region for item in data.by_region]
            requests = [item.search_requests for item in data.by_region]
            resolved = [item.resolved_cases for item in data.by_region]

            fig, ax = plt.subplots(figsize=(10, 6))
            x = range(len(labels))
            width = 0.35

            ax.bar([i - width / 2 for i in x], requests, width=width, label="검색 요청")
            ax.bar([i + width / 2 for i in x], resolved, width=width, label="해결")

            ax.set_title("지역별 검색/해결 통계")
            ax.set_xlabel("지역")
            ax.set_ylabel("건수")
            ax.set_xticks(list(x))
            ax.set_xticklabels(labels, rotation=20)
            ax.legend()

        else:
            data = self.service.get_outcomes(
                request.from_date, request.to_date, request.region
            )

            # outcomes는 recent_cases 리스트이므로 상태별 집계로 변환
            status_count: dict[str, int] = {}
            for item in data.recent_cases:
                status_count[item.status] = status_count.get(item.status, 0) + 1

            labels = list(status_count.keys())
            values = list(status_count.values())

            fig, ax = plt.subplots(figsize=(8, 6))
            ax.bar(labels, values)
            ax.set_title("사건 상태별 통계")
            ax.set_xlabel("상태")
            ax.set_ylabel("건수")

        filename = f"{stat_type}_stats_{request.from_date.isoformat()}_{request.to_date.isoformat()}.png"
        return filename, self._png_content(fig)
