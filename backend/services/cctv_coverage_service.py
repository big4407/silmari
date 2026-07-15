"""
CCTV 영상 수집 현황(관리자 콘솔) — 지역별 커버리지 집계.

VideoRepository/RegionRepository만 쓰는 가벼운 서비스다. VideoService는 YOLO·
FashionCLIP·torchreid 같은 무거운 ML 패키지를 모듈 최상단에서 import하는데,
이 화면은 단순 DB 집계만 하면 되는 조회 전용 관리자 페이지라 그 무거운
의존성을 끌고 올 이유가 없다 — 그래서 별도 서비스로 분리한다.
"""
from sqlalchemy.orm import Session

from backend.repositories.region_repository import RegionRepository
from backend.repositories.video_repository import VideoRepository
from backend.schemas.video_schema import (
    CctvRegionCoverageItem,
    CctvRegionCoverageResponse,
    CctvSourceSummary,
)


class CctvCoverageService:
    def __init__(self, db: Session):
        self.db = db
        self.video_repository = VideoRepository(db)
        self.region_repository = RegionRepository(db)

    def get_region_coverage(self) -> CctvRegionCoverageResponse:
        """지역별 CCTV 수집 현황 — 관리자 콘솔 "CCTV 영상 수집 현황" 화면용.

        용량·시간대 커버리지는 Video 테이블에 그 데이터 자체가 없어서(파일
        크기 컬럼 없음, 파일명에 시각 정보 없음) 다루지 않는다.
        """
        coverage_rows = self.video_repository.get_region_coverage()
        region_names = {
            r.region_code: (r.full_name or r.specific_name)
            for r in self.region_repository.list_all_ordered()
        }

        items = [
            CctvRegionCoverageItem(
                region_code=row["region_code"],
                region_name=region_names.get(row["region_code"]),
                cctv_count=row["cctv_count"],
                video_count=row["video_count"],
                status="수집됨",
            )
            for row in coverage_rows
        ]
        items.sort(key=lambda item: item.region_name or item.region_code)

        collected_codes = {row["region_code"] for row in coverage_rows}
        leaf_codes = set(self.region_repository.get_leaf_codes())
        missing_region_count = len(leaf_codes - collected_codes)

        summary = CctvSourceSummary(
            collected_region_count=len(collected_codes),
            video_file_count=sum(row["video_count"] for row in coverage_rows),
            missing_region_count=missing_region_count,
        )

        return CctvRegionCoverageResponse(summary=summary, items=items)
