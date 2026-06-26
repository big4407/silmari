import re

from backend.schemas.alert_schema import AlertInfo


def parse_alert_text(text: str) -> AlertInfo:
    """안전안내문자에서 인상착의 파싱. (추후 LangChain LLM으로 교체)"""
    result = {
        "name": None,
        "age": None,
        "gender": None,
        "clothes": None,
        "clothes_part": "upper",
        "raw_text": text,
    }

    age_match = re.search(r"(\d+)\s*세", text)
    if age_match:
        result["age"] = int(age_match.group(1))

    gender_match = re.search(r"\(([남여])", text)
    if gender_match:
        result["gender"] = "남" if gender_match.group(1) == "남" else "여"

    name_match = re.search(r"([가-힣]{2,4})\s*\([남여]", text)
    if not name_match:
        name_match = re.search(r"([가-힣]{2,4})\s*(씨|님|양)", text)
    if name_match:
        result["name"] = name_match.group(1)

    colors = ["빨간", "파란", "노란", "검은", "흰", "초록", "회색", "분홍", "보라", "주황", "밝은", "어두운"]
    found_colors = [c for c in colors if c in text]
    if found_colors:
        result["clothes"] = ", ".join(found_colors[:3])

    clothing_desc = re.search(r"(\d+cm.*?)(?:\.|$)", text)
    if clothing_desc and not result["clothes"]:
        result["clothes"] = clothing_desc.group(1).strip()[:80]
    elif not result["clothes"]:
        desc_match = re.search(r"[찾습][^.]*?([가-힣].{5,60})", text)
        if desc_match:
            result["clothes"] = desc_match.group(1).strip()[:80]

    lower_keywords = ["바지", "치마", "하의", "반바지", "청바지", "슬랙스", "하의"]
    upper_keywords = ["점퍼", "자켓", "상의", "티셔츠", "셔츠", "코트", "후드", "니트", "패딩"]

    has_lower = any(kw in text for kw in lower_keywords)
    has_upper = any(kw in text for kw in upper_keywords)

    if has_lower and has_upper:
        result["clothes_part"] = "both"
    elif has_lower:
        result["clothes_part"] = "lower"

    return AlertInfo(**result)
