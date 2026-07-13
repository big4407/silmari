"""
사용자 입력 지역명을 Region 테이블의 지역 데이터와 매칭하는 모듈.

주요 역할:
- 사용자 지역명 정규화
- Region.full_name / Region.specific_name 비교
- 정확 일치, 토큰 포함, 유사도 비교
- matched / ambiguous / not_found 결과 반환
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from rapidfuzz import fuzz

from backend.db.models import Region
from backend.repositories.region_repository import RegionRepository


class RegionResolveStatus(str, Enum):
    """지역명 판정 결과."""

    MATCHED = "matched"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class RegionCandidate:
    """
    지역명 매칭 후보
    """

    region_code: str
    full_name: str
    specific_name: str | None
    normalized_full_name: str
    normalized_specific_name: str
    score: float
    token_scores: tuple[float, ...] = ()


@dataclass(frozen=True)
class RegionResolveResult:
    """지역명 매칭 최종 결과."""

    status: RegionResolveStatus

    region_code: str | None = None
    full_name: str | None = None
    specific_name: str | None = None

    candidates: tuple[RegionCandidate, ...] = ()


class RegionResolver:
    """
    사용자 입력 지역명을 Region 테이블의 실제 지역과 연결한다.

    비교 순서:
    1. full_name 완전 일치
    2. specific_name 완전 일치
    3. 입력 토큰이 full_name에 포함되는지 검사
    4. RapidFuzz를 이용한 유사도 비교
    """

    SIDO_ALIASES: dict[str, str] = {
        "서울특별시": "서울",
        "서울시": "서울",
        "부산광역시": "부산",
        "부산시": "부산",
        "대구광역시": "대구",
        "대구시": "대구",
        "인천광역시": "인천",
        "인천시": "인천",
        "광주광역시": "광주",
        "광주시": "광주",
        "대전광역시": "대전",
        "대전시": "대전",
        "울산광역시": "울산",
        "울산시": "울산",
        "세종특별자치시": "세종",
        "세종시": "세종",
        "경기도": "경기",
        "강원특별자치도": "강원",
        "강원도": "강원",
        "충청북도": "충북",
        "충청남도": "충남",
        "전북특별자치도": "전북",
        "전라북도": "전북",
        "전라남도": "전남",
        "경상북도": "경북",
        "경상남도": "경남",
        "제주특별자치도": "제주",
        "제주도": "제주",
    }

    NOISE_WORDS: tuple[str, ...] = (
        "근처",
        "일대",
        "주변",
        "부근",
        "인근",
        "지역",
        "쪽",
    )

    def __init__(
        self,
        region_repository: RegionRepository,
        *,
        fuzzy_threshold: float = 80.0,
        ambiguity_gap: float = 5.0,
        max_candidates: int = 5,
    ):
        """
        Args:
            region_repository:
                Region 테이블 조회를 담당하는 Repository.

            fuzzy_threshold:
                fuzzy 후보로 인정할 최소 점수.

            ambiguity_gap:
                후보 1위와 2위의 점수 차이가 이 값보다 작으면
                ambiguous로 판정한다.

            max_candidates:
                ambiguous 결과에 포함할 최대 후보 수.
        """

        self.region_repository = region_repository
        self.fuzzy_threshold = fuzzy_threshold
        self.ambiguity_gap = ambiguity_gap
        self.max_candidates = max_candidates

    @classmethod
    def normalize(cls, value: str | None) -> str:
        """
        지역명을 비교 가능한 형태로 정규화한다.

        예:
            대전광역시 동구 -> 대전 동구
            대전시/동구 -> 대전 동구
            전라남도 고흥군 -> 전남 고흥군
            대전 동구 근처 -> 대전 동구
        """

        if not value:
            return ""

        normalized = value.strip()

        # 괄호 기호만 제거하고 내부 문자열은 유지한다.
        normalized = re.sub(r"[()\[\]{}]", " ", normalized)

        # 구분자를 공백으로 변환한다.
        normalized = re.sub(r"[,/|·]", " ", normalized)

        # 문장부호를 제거한다.
        normalized = re.sub(r"[.!?;:]", " ", normalized)

        # 긴 문자열을 먼저 치환한다.
        for original in sorted(cls.SIDO_ALIASES, key=len, reverse=True):
            normalized = normalized.replace(
                original,
                cls.SIDO_ALIASES[original],
            )

        # 검색과 관련 없는 표현을 제거한다.
        for noise_word in cls.NOISE_WORDS:
            normalized = re.sub(
                rf"(?<!\S){re.escape(noise_word)}(?!\S)",
                " ",
                normalized,
            )

        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    @classmethod
    def tokenize(cls, value: str | None) -> tuple[str, ...]:
        """지역명을 정규화한 뒤 공백 단위로 분리한다."""

        normalized = cls.normalize(value)

        if not normalized:
            return ()

        return tuple(normalized.split())

    def resolve(self, user_input: str) -> RegionResolveResult:
        """
        사용자 입력 지역명을 실제 Region 데이터와 매칭한다.

        Returns:
            matched:
                지역이 하나로 확정된 경우

            ambiguous:
                동일하거나 유사한 지역이 여러 개인 경우

            not_found:
                일치하는 지역을 찾지 못한 경우
        """

        normalized_input = self.normalize(user_input)

        if not normalized_input:
            return self._not_found_result()

        regions = self.region_repository.list_all_ordered()

        if not regions:
            return self._not_found_result()

        candidates = [
            self._create_candidate(
                region=region,
                normalized_input=normalized_input,
            )
            for region in regions
            if region.full_name
        ]

        # 1. 전체 지역명 완전 일치
        full_name_matches = [
            candidate
            for candidate in candidates
            if candidate.normalized_full_name == normalized_input
        ]

        if full_name_matches:
            preferred_matches = self._prefer_leaf_candidates(full_name_matches)

            if len(preferred_matches) == 1:
                return self._matched_result(preferred_matches[0])

            return self._ambiguous_result(preferred_matches)

        # 2. specific_name 완전 일치
        specific_name_matches = [
            candidate
            for candidate in candidates
            if candidate.normalized_specific_name
            and candidate.normalized_specific_name == normalized_input
        ]

        if len(specific_name_matches) == 1:
            return self._matched_result(specific_name_matches[0])

        if len(specific_name_matches) > 1:
            return self._ambiguous_result(specific_name_matches)

        # 3. 입력 토큰이 full_name에 모두 포함되는지 확인
        token_matches = self._find_token_matches(
            normalized_input=normalized_input,
            candidates=candidates,
        )

        if len(token_matches) == 1:
            return self._matched_result(token_matches[0])

        if len(token_matches) > 1:
            ranked_matches = self._sort_candidates(token_matches)

            if self._can_select_top_candidate(ranked_matches):
                return self._matched_result(ranked_matches[0])

            return self._ambiguous_result(ranked_matches)

        # 4. fuzzy matching
        fuzzy_matches = [
            candidate
            for candidate in candidates
            if candidate.token_scores
            and min(candidate.token_scores) >= 70.0
            and candidate.score >= self.fuzzy_threshold
        ]

        ranked_fuzzy_matches = self._sort_candidates(fuzzy_matches)

        if not ranked_fuzzy_matches:
            return self._not_found_result()

        if len(ranked_fuzzy_matches) == 1:
            return self._matched_result(ranked_fuzzy_matches[0])

        if self._can_select_top_candidate(ranked_fuzzy_matches):
            return self._matched_result(ranked_fuzzy_matches[0])

        return self._ambiguous_result(ranked_fuzzy_matches)

    def _calculate_token_coverage(
        self,
        *,
        input_tokens: tuple[str, ...],
        candidate_tokens: tuple[str, ...],
    ) -> tuple[float, tuple[float, ...]]:
        """
        입력 지역 토큰 각각이 후보 지역명에 얼마나 잘 대응되는지 계산한다.

        예:
            입력:
                ("서울", "역삼동")

            후보:
                ("서울", "강남구", "역삼1동")

            결과:
                서울   -> 서울     : 100
                역삼동 -> 역삼1동  : 95

                평균 점수: 97.5
                개별 점수: (100.0, 95.0)

        Returns:
            평균 점수와 입력 토큰별 최고 점수.
        """

        if not input_tokens or not candidate_tokens:
            return 0.0, ()

        token_scores: list[float] = []

        for input_token in input_tokens:
            best_score = max(
                self._calculate_token_similarity(
                    input_token=input_token,
                    candidate_token=candidate_token,
                )
                for candidate_token in candidate_tokens
            )

            token_scores.append(best_score)

        average_score = sum(token_scores) / len(token_scores)

        return average_score, tuple(token_scores)

    def _calculate_token_similarity(
        self,
        *,
        input_token: str,
        candidate_token: str,
    ) -> float:
        """
        지역 토큰 두 개의 유사도를 계산한다.

        행정동 번호 차이는 별도로 보정한다.

        예:
            역삼동  <-> 역삼1동 : 95점
            역삼동  <-> 역삼2동 : 95점
            서울    <-> 서울     : 100점
        """

        if input_token == candidate_token:
            return 100.0

        input_base = self._normalize_region_token(input_token)
        candidate_base = self._normalize_region_token(candidate_token)

        if input_base == candidate_base:
            return 95.0

        # 사용자가 행정구역 접미사를 생략한 경우
        # 역삼 ↔ 역삼1동, 강남 ↔ 강남구
        if input_base and candidate_base.startswith(input_base):
            return 90.0

        if candidate_base and input_base.startswith(candidate_base):
            return 90.0

        return float(fuzz.ratio(input_token, candidate_token))

    def _create_candidate(
        self,
        *,
        region: Region,
        normalized_input: str,
    ) -> RegionCandidate:
        """Region ORM 객체를 비교용 후보 객체로 변환한다."""

        normalized_full_name = self.normalize(region.full_name)
        normalized_specific_name = self.normalize(region.specific_name)

        input_tokens = self.tokenize(normalized_input)
        candidate_tokens = self.tokenize(normalized_full_name)

        score, token_scores = self._calculate_token_coverage(
            input_tokens=input_tokens,
            candidate_tokens=candidate_tokens,
        )

        return RegionCandidate(
            region_code=region.region_code,
            full_name=region.full_name,
            specific_name=region.specific_name,
            normalized_full_name=normalized_full_name,
            normalized_specific_name=normalized_specific_name,
            score=score,
            token_scores=token_scores,
        )

    def _find_token_matches(
        self,
        *,
        normalized_input: str,
        candidates: Sequence[RegionCandidate],
    ) -> list[RegionCandidate]:
        """
        입력 토큰이 후보의 전체 지역명에 모두 포함되는지 확인한다.

        예:
            입력:
                고흥읍 등암리

            후보:
                전남 고흥군 고흥읍 등암리
        """

        input_tokens = set(self.tokenize(normalized_input))

        if not input_tokens:
            return []

        matches: list[RegionCandidate] = []

        for candidate in candidates:
            full_name_tokens = set(self.tokenize(candidate.normalized_full_name))

            if input_tokens.issubset(full_name_tokens):
                matches.append(candidate)

        return matches

    @staticmethod
    def _calculate_score(
        *,
        normalized_input: str,
        normalized_candidate: str,
    ) -> float:
        """입력값과 후보 지역명의 문자열 유사도를 계산한다."""

        if not normalized_candidate:
            return 0.0

        return float(
            max(
                fuzz.ratio(normalized_input, normalized_candidate),
                fuzz.WRatio(normalized_input, normalized_candidate),
            )
        )

    @staticmethod
    def _normalize_region_token(token: str) -> str:
        """
        비교용으로 행정구역 접미사와 행정동 번호를 제거한다.

        예:
            역삼1동 -> 역삼
            역삼동  -> 역삼
            강남구  -> 강남
            고흥읍  -> 고흥
        """

        normalized = token.strip()

        # 행정동 숫자 제거
        normalized = re.sub(r"\d+(?=동$)", "", normalized)

        # 행정구역 접미사 제거
        normalized = re.sub(
            r"(특별시|광역시|특별자치시|특별자치도|시|군|구|읍|면|동|리)$",
            "",
            normalized,
        )

        return normalized

    @staticmethod
    def _sort_candidates(
        candidates: Sequence[RegionCandidate],
    ) -> list[RegionCandidate]:
        """유사도 점수 내림차순으로 후보를 정렬한다."""

        return sorted(
            candidates,
            key=lambda candidate: (
                candidate.score,
                -len(candidate.normalized_full_name),
            ),
            reverse=True,
        )

    def _can_select_top_candidate(
        self,
        candidates: Sequence[RegionCandidate],
    ) -> bool:
        """
        후보가 여러 개일 때 1위 후보를 자동 확정할 수 있는지 판단한다.
        """

        if not candidates:
            return False

        if len(candidates) == 1:
            return candidates[0].score >= self.fuzzy_threshold

        first = candidates[0]
        second = candidates[1]

        return (
            first.score >= self.fuzzy_threshold
            and first.score - second.score >= self.ambiguity_gap
        )

    @staticmethod
    def _remove_dong_number(token: str) -> str:
        """
        행정동 이름에 포함된 숫자를 제거한다.

        예:
            역삼1동 -> 역삼동
            역삼2동 -> 역삼동
            신정3동 -> 신정동

        읍·면·리 등의 숫자는 건드리지 않는다.
        """

        return re.sub(r"^(.+?)\d+동$", r"\1동", token)

    @staticmethod
    def _matched_result(
        candidate: RegionCandidate,
    ) -> RegionResolveResult:
        """확정된 후보를 matched 결과로 변환한다."""

        return RegionResolveResult(
            status=RegionResolveStatus.MATCHED,
            region_code=candidate.region_code,
            full_name=candidate.full_name,
            specific_name=candidate.specific_name,
            candidates=(candidate,),
        )

    def _ambiguous_result(
        self,
        candidates: Sequence[RegionCandidate],
    ) -> RegionResolveResult:
        """여러 후보를 ambiguous 결과로 변환한다."""

        ranked_candidates = self._sort_candidates(candidates)

        return RegionResolveResult(
            status=RegionResolveStatus.AMBIGUOUS,
            candidates=tuple(ranked_candidates[: self.max_candidates]),
        )

    @staticmethod
    def _not_found_result() -> RegionResolveResult:
        """일치하는 후보가 없는 결과를 반환한다."""

        return RegionResolveResult(
            status=RegionResolveStatus.NOT_FOUND,
        )

    def _prefer_leaf_candidates(
        self,
        candidates: Sequence[RegionCandidate],
    ) -> list[RegionCandidate]:
        """
        동일하거나 유사한 후보가 여러 개일 경우 최하위 지역을 우선한다.

        다른 Region의 parent_code로 사용되는 코드는 상위 지역이므로 제외한다.
        """
        if len(candidates) <= 1:
            return list(candidates)

        parent_codes = self.region_repository.get_parent_codes()

        leaf_candidates = [
            candidate
            for candidate in candidates
            if candidate.region_code not in parent_codes
        ]

        return leaf_candidates or list(candidates)


if __name__ == "__main__":
    from backend.db.database import SessionLocal
    from backend.repositories.region_repository import RegionRepository

    db = SessionLocal()

    try:
        region_repository = RegionRepository(db)
        region_resolver = RegionResolver(region_repository)

        result = region_resolver.resolve("대전시")

        print(result)

    finally:
        db.close()
