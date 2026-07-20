"""
인상착의(한글 자유 텍스트) → FashionCLIP 검색 쿼리(영문) 변환.

FashionCLIP은 영어로 학습된 모델이라 한글 텍스트를 그대로 넣으면 유사도가
크게 떨어진다. `fashionclip-taxonomy.md`에 정의된 고정 어휘(색상·상의·하의 등)를
사전 매칭해 "a person wearing a {color} {top_type} and {color} {bottom_type}"
형태의 영문 문장으로 조립한다.

taxonomy에 하나도 안 걸리면(신조어·오탈자·복잡한 문장 등) None을 반환한다 —
호출 측(services/analysis_service.py)이 이 경우 LLM 번역(core/llm/
clothing_translator.py)으로 넘기고, 그것도 실패하면 최후 수단으로 원문을
그대로 감싸서 쓴다.
"""
from __future__ import annotations

import re

# ── 색상 (CCTV 권장 10색) ────────────────────────────────────────────────
_COLOR_KO_TO_EN: dict[str, str] = {
    "흰색": "white", "하얀색": "white", "하양": "white", "화이트": "white",
    "검은색": "black", "검정색": "black", "검정": "black", "블랙": "black",
    "회색": "gray", "그레이": "gray",
    "빨간색": "red", "빨강": "red", "레드": "red",
    "파란색": "blue", "파랑": "blue", "블루": "blue",
    "초록색": "green", "초록": "green", "그린": "green",
    "노란색": "yellow", "노랑": "yellow", "옐로우": "yellow",
    "갈색": "brown", "브라운": "brown",
    "베이지색": "beige", "베이지": "beige",
    "분홍색": "pink", "핑크": "pink",
}

# ── 상의 종류 (CCTV 권장 범위 + 실사용 빈도 높은 표현) ─────────────────
_TOP_KO_TO_EN: dict[str, str] = {
    "티셔츠": "t-shirt", "티": "t-shirt",
    "셔츠": "shirt",
    "후드티": "hoodie", "후드": "hoodie",
    "맨투맨": "sweatshirt", "스웨트셔츠": "sweatshirt",
    "스웨터": "sweater", "니트": "sweater",
    "재킷": "jacket", "자켓": "jacket",
    "코트": "coat",
    "패딩": "padded jacket", "패딩점퍼": "padded jacket",
    "조끼": "vest",
    "민소매": "sleeveless top", "나시": "sleeveless top",
    "제복": "uniform", "유니폼": "uniform", "정장": "suit",
}

# ── 하의 종류 (CCTV 권장 범위) ──────────────────────────────────────────
_BOTTOM_KO_TO_EN: dict[str, str] = {
    "청바지": "jeans",
    "바지": "pants",
    "트레이닝바지": "sweatpants", "츄리닝": "sweatpants", "조거팬츠": "joggers",
    "레깅스": "leggings",
    "반바지": "shorts",
    "치마": "skirt", "스커트": "skirt",
}

# ── 신발 종류 — color_matching.py의 shoes 영역과 짝을 맞춘다 ────────────
_SHOES_KO_TO_EN: dict[str, str] = {
    "운동화": "sneakers", "스니커즈": "sneakers",
    "구두": "dress shoes",
    "부츠": "boots", "워커": "boots",
    "슬리퍼": "slippers", "샌들": "sandals",
    "슬립온": "slip-on shoes",
    "신발": "shoes",
}

# ── 액세서리 (선택 정보 — 있으면 문장에 덧붙임) ─────────────────────────
_ACCESSORY_KO_TO_EN: dict[str, str] = {
    "모자": "hat", "야구모자": "cap", "캡모자": "cap", "비니": "beanie",
    "백팩": "backpack", "가방": "bag", "숄더백": "shoulder bag",
    "안경": "glasses", "선글라스": "sunglasses",
}


def _find_first_match(text: str, table: dict[str, str]) -> str | None:
    """긴 키워드부터 먼저 매칭해 부분 문자열 오매칭을 줄인다."""
    for ko in sorted(table, key=len, reverse=True):
        if ko in text:
            return table[ko]
    return None


def extract_primary_color_en(clothing_ko: str | None) -> str | None:
    """한글 인상착의 텍스트에서 색상 하나만 뽑아 taxonomy 영문명으로 돌려준다.

    build_clothes_en_from_taxonomy와 마찬가지로 문장 전체에서 색상을 하나만
    찾는다(상/하의 구분 없음). extract_colors_by_garment()가 구간을 못 나눠서
    실패했을 때의 폴백으로 쓰인다.
    """
    if not clothing_ko or not clothing_ko.strip():
        return None
    return _find_first_match(clothing_ko.strip(), _COLOR_KO_TO_EN)


def extract_colors_by_garment(clothing_ko: str | None) -> dict[str, str | None]:
    """한글 인상착의 텍스트에서 상의·하의·신발 색상을 각각 따로 뽑는다.

    "빨간 셔츠, 검정 바지, 흰 운동화"처럼 콤마 등으로 구간이 나뉜 문장이면,
    그 구간 안에서만 색상을 찾아 부위에 정확히 연결한다. "빨간 셔츠 입고
    검정 바지 입은 사람"처럼 구분자가 없어 구간을 못 나누면 어느 색이
    어느 부위인지 판단할 수 없으므로, 문장 전체에서 찾은 색 하나를
    상/하의에만 동일하게 채운다(둘 중 하나만 실제로 맞아도 인정 — 최후
    수단). 신발은 이 폴백에서 제외한다 — 목격 진술에서 신발 색은 상/하의보다
    훨씬 덜 언급되고 크롭 추출 신뢰도도 낮아서(color_matching.py 참고),
    실제로 "신발" 관련 키워드가 문장에 있을 때만 값을 채운다.

    반환: {"top": 영문 색상명 또는 None, "bottom": ..., "shoes": ...}
    """
    result: dict[str, str | None] = {"top": None, "bottom": None, "shoes": None}
    if not clothing_ko or not clothing_ko.strip():
        return result

    text = clothing_ko.strip()
    segments = re.split(r"[,;]|(?:\s그리고\s)|(?:\s하고\s)", text)

    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        color = _find_first_match(seg, _COLOR_KO_TO_EN)
        if color is None:
            continue
        if result["top"] is None and _find_first_match(seg, _TOP_KO_TO_EN):
            result["top"] = color
        if result["bottom"] is None and _find_first_match(seg, _BOTTOM_KO_TO_EN):
            result["bottom"] = color
        if result["shoes"] is None and _find_first_match(seg, _SHOES_KO_TO_EN):
            result["shoes"] = color

    if result["top"] is None and result["bottom"] is None:
        # 구간을 나눠서 상/하의를 하나도 못 찾은 경우(구분자 없는 문장 등) —
        # 문장 전체 기준 색 하나를 최후 수단으로 상/하의 양쪽에 동일하게
        # 채운다. 신발은 위에서 이미 못 찾았으면 그대로 None으로 둔다.
        fallback = extract_primary_color_en(text)
        result["top"] = fallback
        result["bottom"] = fallback

    return result


def build_clothes_en_from_taxonomy(clothing_ko: str | None) -> str | None:
    """한글 인상착의 텍스트를 taxonomy 사전 매칭만으로 FashionCLIP 영문 쿼리로 변환한다.

    taxonomy 사전에 걸리는 색상·상의·하의·액세서리를 조합해 문장을 만든다.
    아무것도 안 걸리면 None을 반환한다 — 호출 측이 LLM 번역으로 넘길 신호.
    """
    if not clothing_ko or not clothing_ko.strip():
        return None

    text = clothing_ko.strip()

    top_color = _find_first_match(text, _COLOR_KO_TO_EN)
    top_type = _find_first_match(text, _TOP_KO_TO_EN)
    bottom_type = _find_first_match(text, _BOTTOM_KO_TO_EN)
    accessory = _find_first_match(text, _ACCESSORY_KO_TO_EN)

    # 색상이 하의 바로 앞에도 있을 수 있어, 상의/하의에 같은 색상을 공유하지
    # 않도록 간단히 전체 텍스트에서 한 번만 찾는다(1차 버전 — 상/하의 색상을
    # 따로 구분하려면 콤마/공백 기준으로 문장을 분리하는 개선이 필요함).
    parts: list[str] = []
    if top_type:
        parts.append(f"a person wearing a {top_color + ' ' if top_color else ''}{top_type}")
    if bottom_type:
        joiner = "and" if parts else "a person wearing"
        parts.append(f"{joiner} {bottom_type}")
    if accessory:
        joiner = "and" if parts else "a person wearing"
        parts.append(f"{joiner} {accessory}")

    if parts:
        return " ".join(parts)

    return None