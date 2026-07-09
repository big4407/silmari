"""
인상착의(한글 자유 텍스트) → FashionCLIP 검색 쿼리(영문) 변환.

FashionCLIP은 영어로 학습된 모델이라 한글 텍스트를 그대로 넣으면 유사도가
크게 떨어진다. `fashionclip-taxonomy.md`에 정의된 고정 어휘(색상·상의·하의 등)를
사전 매칭해 "a person wearing a {color} {top_type} and {color} {bottom_type}"
형태의 영문 문장으로 조립한다.

사전에 안 걸리는 표현은 이후 LLM fallback으로 확장 가능(TODO) — 1차는
CCTV 초기 권장 범위(taxonomy 11번 섹션) 어휘만으로 규칙 기반 매칭한다.
"""
from __future__ import annotations

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


def build_clothes_en(clothing_ko: str | None) -> str:
    """한글 인상착의 텍스트를 FashionCLIP 영문 검색 쿼리로 변환한다.

    taxonomy 사전에 걸리는 색상·상의·하의·액세서리를 조합해 문장을 만든다.
    아무것도 안 걸리면(신조어·오탈자 등) 원문을 그대로 감싸서 최소한의
    검색이라도 되게 한다 — 완전히 비어있을 때만 빈 문자열을 반환한다.
    """
    if not clothing_ko or not clothing_ko.strip():
        return ""

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

    # taxonomy에 하나도 안 걸린 경우 — 원문을 최소한으로나마 활용
    return f"a person wearing {text}"
