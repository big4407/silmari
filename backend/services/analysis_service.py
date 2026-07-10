"""
검색 요청(Search) 하나를 실제로 실행해 매칭 후보(AnalysisDetail)를 만든다.

흐름:
  1) clothing(한글) → clothes_en (core/search/clothing_query.build_clothes_en)
  2) missing_location(한글) → region_code 후보 (RegionRepository LIKE 매칭)
  3) region_code + start_date~end_date → 대상 video_id 목록 (VideoRepository)
  4) VideoService.search_embeddings_multi() → Chroma 코사인 유사도 검색
  5) 유사도 threshold를 넘는 후보만 AnalysisDetail로 저장

동기 실행(1차 결정 — 검색 시점엔 이미 인덱싱된 임베딩만 조회하므로 가벼움).
나중에 검색 대상이 많아지면 BackgroundTasks로 전환 검토.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.core.search.clothing_query import build_clothes_en
from backend.db.models import Analysis, AnalysisStatus
from backend.repositories.analysis_repository import AnalysisRepository
from backend.repositories.region_repository import RegionRepository
from backend.repositories.video_repository import VideoRepository
from backend.schemas.search_schema import SearchDetail

# 코사인 거리 기준 최소 유사도(= 1 - distance). 데이터가 쌓이면 재조정 필요.
DEFAULT_MIN_SIMILARITY = 0.2
DEFAULT_N_RESULTS = 20


class AnalysisService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = AnalysisRepository(db)
        self.region_repository = RegionRepository(db)
        self.video_repository = VideoRepository(db)
        self._video_service = None

    @property
    def video_service(self):
        if self._video_service is None:
            from backend.services.video_service import VideoService

            self._video_service = VideoService(self.db)
        return self._video_service

    def resolve_region_codes(self, location_text: str | None) -> list[str]:
        """자유 텍스트 지역명을 region_code 목록으로 변환한다.

        매칭이 없으면 빈 리스트를 반환하고(=지역 필터 없이 검색), 여러 개
        걸리면 전부 후보로 사용한다.
        """
        if not location_text or not location_text.strip():
            return []
        return self.region_repository.find_codes_by_keyword(location_text.strip())

    def resolve_video_ids(
        self, region_codes: list[str], start_date, end_date
    ) -> list[int] | None:
        """지역·기간 조건에 맞는 video.id 목록. 조건이 하나도 없으면 None(=전체 대상)."""
        if not region_codes and not start_date and not end_date:
            return None
        return self.video_repository.find_ids(
            region_codes=region_codes, start_date=start_date, end_date=end_date
        )

    def run_analysis(self, search: SearchDetail) -> Analysis:
        analysis = self.repository.create(user_id=search.user_id, search_id=search.id)

        clothes_en = build_clothes_en(search.clothing)
        if not clothes_en:
            # 인상착의 정보가 전혀 없으면 매칭을 시도할 수 없다 — 빈 결과로 완료 처리.
            return self.repository.set_status(analysis, AnalysisStatus.COMPLETED)

        region_codes = self.resolve_region_codes(search.missing_location)
        video_ids = self.resolve_video_ids(
            region_codes, search.start_date, search.end_date
        )
        if video_ids is not None and not video_ids:
            # 조건에 맞는 영상 자체가 없음 — 매칭 없음으로 완료.
            return self.repository.set_status(analysis, AnalysisStatus.COMPLETED)

        raw = self.video_service.search_embeddings_multi(
            clothes_en, video_ids=video_ids, n_results=DEFAULT_N_RESULTS
        )
        candidates = self._to_analysis_details(raw)

        if candidates:
            self.repository.add_details(analysis.id, candidates)

        return self.repository.set_status(analysis, AnalysisStatus.COMPLETED)

    @staticmethod
    def _to_analysis_details(raw: dict) -> list[dict]:
        """Chroma query() 결과를 AnalysisDetail 저장용 dict 리스트로 변환.

        raw 구조: {"metadatas": [[...]], "distances": [[...]]} (batch 1건 기준
        바깥 리스트는 항상 길이 1).
        """
        metadatas = (raw.get("metadatas") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]

        details = []
        for metadata, distance in zip(metadatas, distances):
            similarity = 1 - distance
            if similarity < DEFAULT_MIN_SIMILARITY:
                continue
            details.append(
                {
                    "video_id": metadata["video_id"],
                    "video_timestamp": metadata["video_timestamp"],
                    "crop_id": metadata["crop_id"],
                    "position": metadata["position"],
                    "crop_img_path": metadata.get("image_path"),
                    "matching_rate": round(similarity, 4),
                }
            )
        return details
