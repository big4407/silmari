"""
검색 요청(Search) 하나를 실제로 실행해 매칭 후보(AnalysisDetail)를 만든다.

흐름:
  1) clothing(한글) → clothes_en
     ① taxonomy 사전 매칭(core/search/clothing_query) — 대부분 여기서 끝남
     ② ①이 실패하면 LLM 번역(core/llm/clothing_translator)으로 fallback
     ③ ②도 실패하면 원문을 그대로 감싸서 최소한의 검색이라도 시도(최후 수단)
  2) missing_location(한글) → region_code 후보 (RegionRepository LIKE 매칭)
  3) region_code + start_date~end_date → 대상 video_id 목록 (VideoRepository)
  4) VideoService.search_embeddings_multi() → Chroma 코사인 유사도 검색
  5) 유사도 threshold를 넘는 후보만 AnalysisDetail로 저장

동기 실행(1차 결정 — 검색 시점엔 이미 인덱싱된 임베딩만 조회하므로 가벼움).
나중에 검색 대상이 많아지면 BackgroundTasks로 전환 검토.
"""

from __future__ import annotations

import time

from langchain_community.callbacks import get_openai_callback
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.llm.clothing_translator import (
    CLOTHING_TRANSLATE_MODEL,
    translate_clothing_with_llm,
)
from backend.core.search.clothing_query import (
    build_clothes_en_from_taxonomy,
    extract_colors_by_garment,
)
from backend.core.search.color_matching import match_color
from backend.db.models import Analysis, AnalysisStatus, LlmCallType
from backend.repositories.analysis_repository import AnalysisRepository
from backend.repositories.region_repository import RegionRepository
from backend.repositories.video_repository import VideoRepository
from backend.schemas.search_schema import SearchDetail
from backend.services.llm_call_service import LlmCallService

# 코사인 거리 기준 최소 유사도(= 1 - distance). 데이터가 쌓이면 재조정 필요.
DEFAULT_MIN_SIMILARITY = 0.2


class AnalysisService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = AnalysisRepository(db)
        self.region_repository = RegionRepository(db)
        self.video_repository = VideoRepository(db)
        self.llm_call_service = LlmCallService(db)
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

    def resolve_clothes_en(self, clothing_ko: str | None, *, user_id: str | None = None) -> str:
        """한글 인상착의를 FashionCLIP 영문 쿼리로 변환한다.

        taxonomy 사전 매칭이 우선이고(빠르고 비용 없음), 실패할 때만 LLM 번역을
        쓴다. LLM 호출은 챗봇·안내문자 파싱과 동일하게 get_openai_callback()으로
        감싸서 llm_call 테이블에 기록한다(call_type="1" = 인상착의 한영변환).
        """
        if not clothing_ko or not clothing_ko.strip():
            return ""

        clothes_en = build_clothes_en_from_taxonomy(clothing_ko)
        if clothes_en:
            return clothes_en

        start = time.perf_counter()
        call_status = "1"
        error_msg = None
        translated = None
        callback = None

        try:
            with get_openai_callback() as cb:
                callback = cb
                translated = translate_clothing_with_llm(clothing_ko)
        except Exception as e:
            call_status = "0"
            error_msg = str(e)[:255]
        finally:
            self.llm_call_service.record_call(
                call_type=LlmCallType.CLOTHING_TRANSLATE,
                model_name=CLOTHING_TRANSLATE_MODEL,
                prompt=clothing_ko,
                response=translated,
                start_time=start,
                callback=callback,
                status=call_status,
                error_msg=error_msg,
                user_id=user_id,
            )

        if translated:
            return translated

        # taxonomy도, LLM도 실패한 경우의 최후 수단 — 원문을 그대로 감싸서
        # 최소한의 검색이라도 시도한다.
        return f"a person wearing {clothing_ko.strip()}"

    def run_analysis(self, search: SearchDetail) -> Analysis:
        analysis = self.repository.create(user_id=search.user_id, search_id=search.id)

        clothes_en = self.resolve_clothes_en(search.clothing, user_id=search.user_id)
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
            clothes_en, video_ids=video_ids, n_results=settings.search_result_limit
        )
        garment_colors = extract_colors_by_garment(search.clothing)
        candidates = self._to_analysis_details(
            raw, garment_colors, self.video_repository
        )

        if candidates:
            self.repository.add_details(analysis.id, candidates)

        return self.repository.set_status(analysis, AnalysisStatus.COMPLETED)

    @staticmethod
    def _to_analysis_details(
        raw: dict, garment_colors: dict[str, str | None], video_repository: VideoRepository
    ) -> list[dict]:
        """Chroma query() 결과를 AnalysisDetail 저장용 dict 리스트로 변환.

        raw 구조: {"metadatas": [[...]], "distances": [[...]]} (batch 1건 기준
        바깥 리스트는 항상 길이 1).

        color_match_rate: 인상착의 텍스트에서 상의·하의·신발별로 뽑은 색상
        (garment_colors — core/search/clothing_query.extract_colors_by_garment)을
        그 crop의 실제 부위별 색(video_detail에 인덱싱 시점에 저장돼 있음,
        core/search/color_matching.py)과 각각 비교한다. 텍스트에 언급된
        부위만 평균에 반영한다(여러 부위가 언급됐으면 평균, 하나만 언급됐으면
        그 하나만 — 언급 안 된 부위 때문에 점수가 부당하게 깎이지 않게). 아무
        색상도 없거나 해당 video_detail을 못 찾으면 None(비교 불가)으로 둔다.
        """
        metadatas = (raw.get("metadatas") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]

        video_ids = {m["video_id"] for m in metadatas}
        detail_lookup = {
            (d.video_id, d.video_timestamp, d.crop_id): d
            for d in video_repository.find_details_by_video_ids(list(video_ids))
        }

        # (텍스트 색상 dict 키) → (video_detail의 해당 부위 색 컬럼명)
        garment_to_column = {
            "top": "top_color",
            "bottom": "bottom_color",
            "shoes": "shoes_color",
        }
        has_any_color = any(garment_colors.get(g) for g in garment_to_column)

        details = []
        for metadata, distance in zip(metadatas, distances):
            similarity = 1 - distance
            if similarity < DEFAULT_MIN_SIMILARITY:
                continue

            color_match_rate = None
            if has_any_color:
                video_detail = detail_lookup.get(
                    (
                        metadata["video_id"],
                        metadata["video_timestamp"],
                        metadata["crop_id"],
                    )
                )
                if video_detail is not None:
                    scores = [
                        match_color(
                            garment_colors[garment],
                            getattr(video_detail, column),
                        )
                        for garment, column in garment_to_column.items()
                        if garment_colors.get(garment)
                    ]
                    if scores:
                        color_match_rate = round(sum(scores) / len(scores), 4)

            details.append(
                {
                    "video_id": metadata["video_id"],
                    "video_timestamp": metadata["video_timestamp"],
                    "crop_id": metadata["crop_id"],
                    "position": metadata["position"],
                    "crop_img_path": metadata.get("image_path"),
                    "matching_rate": round(similarity, 4),
                    "color_match_rate": color_match_rate,
                }
            )
        return details