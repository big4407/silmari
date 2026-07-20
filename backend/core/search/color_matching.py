"""
인상착의 텍스트의 색상과 CCTV 크롭 이미지에서 뽑은 실제 색상을 비교한다.

[왜 FashionCLIP에 색상 블록 이미지를 넣지 않는가]
검토했던 대안(예: "검은 네모 + 파란 네모"로 합성 이미지를 만들어 FashionCLIP에
넣는 방식)은 채택하지 않았다. FashionCLIP은 실제 의류 사진으로 학습된
모델이라, 색상 블록처럼 학습 데이터 분포와 동떨어진 입력을 넣으면 임베딩이
안정적으로 안 나올 가능성이 크다. 대신 이 모듈은 크롭 이미지에서 우세 색상을
직접 뽑아 CIE Lab 색공간에서 거리로 비교하는 고전적인 방식을 쓴다 —
FashionCLIP 유사도를 대체하는 게 아니라 보조/재순위용 신호다.

[흐름]
  1) extract_region_dominant_color(crop_image, region) — 크롭 이미지를
     상의/하의/신발 구간으로 나눠 우세 색상을 Lab으로 뽑는다(K-means).
     인덱싱 시점에 1번만 계산해 video_detail.{top,bottom,shoes}_color에
     저장한다(services/video_service.py).
  2) match_color(text_color_en, image_lab) — taxonomy 색상 이름(영문)과
     비교해 0~1 매칭 점수로 변환한다. 검색 시점에 analysis_detail의
     color_match_rate로 저장한다(services/analysis_service.py).

머리색은 다루지 않는다 — 상의 영역과 겹치지 않으려 제외한 좁은 구간이라
K-means가 노이즈(피부색·저해상도)에 취약해 신뢰도가 낮다.
"""
from __future__ import annotations

import cv2
import numpy as np

# taxonomy 색상 이름(core/search/clothing_query.py의 _COLOR_KO_TO_EN 영문값과
# 동일해야 한다) → 대표 RGB. 실제 CCTV 샘플로 검증하며 조정이 필요한 1차값.
_COLOR_REFERENCE_RGB: dict[str, tuple[int, int, int]] = {
    "white": (255, 255, 255),
    "black": (20, 20, 20),
    "gray": (128, 128, 128),
    "red": (190, 30, 30),
    "blue": (30, 60, 170),
    "green": (40, 120, 60),
    "yellow": (225, 195, 40),
    "brown": (110, 70, 40),
    "beige": (222, 196, 160),
    "pink": (230, 150, 175),
}

# 두 Lab 색이 "완전히 다르다"고 볼 최대 유효 거리(CIE76 deltaE 기준). 대략
# 0~10 거의 동일, 10~30 유사한 색, 30 이상은 다른 색으로 본다 — 이 이상은
# match_color()에서 0점 처리한다. 실측 데이터로 재조정 필요한 1차값이다.
_MAX_EFFECTIVE_DISTANCE = 60.0

# 색상 판별 불가(크롭이 너무 작거나 배경만 있는 등) 시 반환하는 중립 점수 —
# 감점도 가점도 안 하기 위해 0.5로 둔다.
_NEUTRAL_SCORE = 0.5

# 크롭 이미지(사람 전신 기준) 세로 비율 — 어디부터 어디까지가 각 부위인지.
# 서 있는 정면/측면 CCTV 컷 기준의 대략적인 휴리스틱이라, 앉아있거나 잘린
# 구도·군중 속 겹침에서는 부정확할 수 있다. 머리(0~15%)는 다루지 않는다.
_REGION_BOUNDS: dict[str, tuple[float, float]] = {
    "top": (0.15, 0.55),  # 상반신(상의)
    "bottom": (0.55, 0.88),  # 하반신(하의)
    "shoes": (0.90, 1.0),  # 발 — 걸음 중 블러·바지에 가려짐 등으로 상/하의보다 신뢰도 낮음
}


def _rgb_to_lab(rgb: tuple[int, int, int]) -> np.ndarray:
    pixel = np.uint8([[list(rgb)]])  # 1x1 픽셀 이미지로 만들어 cv2 변환 재사용
    lab = cv2.cvtColor(pixel, cv2.COLOR_RGB2LAB)
    return lab[0, 0].astype(np.float32)


_COLOR_REFERENCE_LAB: dict[str, np.ndarray] = {
    name: _rgb_to_lab(rgb) for name, rgb in _COLOR_REFERENCE_RGB.items()
}


def color_distance(lab1: np.ndarray, lab2: np.ndarray) -> float:
    """CIE76 deltaE — 두 Lab 색 사이의 지각적 거리(유클리드). 작을수록 비슷하다."""
    return float(np.linalg.norm(lab1.astype(np.float32) - lab2.astype(np.float32)))


def extract_region_dominant_color(
    crop_image: np.ndarray, region: str
) -> np.ndarray | None:
    """크롭 이미지(BGR, cv2로 읽은 person crop)에서 부위별 우세 색상을 Lab으로 뽑는다.

    region: "top"(상의) | "bottom"(하의) | "shoes"(신발). 머리는 지원하지
    않는다(모듈 docstring 참고 — 신뢰도가 낮아서 제외).
    """
    if region not in _REGION_BOUNDS:
        raise ValueError(
            f"알 수 없는 region: {region!r} (top/bottom/shoes만 가능)"
        )
    if crop_image is None or crop_image.size == 0:
        return None

    height, width = crop_image.shape[:2]
    if height <= 0 or width <= 0:
        return None

    r1, r2 = _REGION_BOUNDS[region]
    ry1, ry2 = int(height * r1), int(height * r2)

    band = crop_image[ry1:ry2, :]
    if band.size == 0:
        return None

    lab_band = cv2.cvtColor(band, cv2.COLOR_BGR2LAB)
    pixels = lab_band.reshape(-1, 3).astype(np.float32)

    # K-means로 우세 색상 클러스터를 뽑는다 — 단순 평균(k=1)은 배경·그림자·
    # 피부색 노이즈에 쉽게 흔들려서, k=3으로 나누고 가장 큰 클러스터를 채택한다.
    k = min(3, len(pixels))
    if k < 1:
        return None
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(
        pixels, k, None, criteria, attempts=3, flags=cv2.KMEANS_PP_CENTERS
    )
    counts = np.bincount(labels.flatten())
    dominant = centers[np.argmax(counts)]
    return dominant


def match_color(clothing_color_en: str | None, image_lab) -> float:
    """텍스트에서 파싱한 색상(영문, taxonomy 이름)과 이미지에서 뽑은 Lab 색을
    비교해 0~1 매칭 점수로 변환한다(1=거의 동일, 0=많이 다름).

    image_lab은 np.ndarray 또는 (DB에서 읽어온) [L, a, b] 형태의 list여도 된다.
    둘 중 하나라도 없으면(색상 정보가 없거나 taxonomy에 없는 색이거나, 크롭에서
    색상 추출이 안 됐거나) 판단을 유보하는 중립값(0.5)을 돌려준다 — 색상
    불일치로 단정 짓지 않기 위함이다.
    """
    if (
        image_lab is None
        or not clothing_color_en
        or clothing_color_en not in _COLOR_REFERENCE_LAB
    ):
        return _NEUTRAL_SCORE

    ref_lab = _COLOR_REFERENCE_LAB[clothing_color_en]
    distance = color_distance(ref_lab, np.asarray(image_lab, dtype=np.float32))
    return max(0.0, 1.0 - (distance / _MAX_EFFECTIVE_DISTANCE))
