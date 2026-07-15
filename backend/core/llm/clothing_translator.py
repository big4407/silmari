"""
인상착의(한글) → FashionCLIP 검색 쿼리(영문) LLM 번역.

core/search/clothing_query.py의 taxonomy 사전 매칭이 아무것도 못 찾았을 때만
쓰는 fallback이다(신조어·복잡한 문장·taxonomy에 없는 표현 등). 대부분의 요청은
taxonomy 매칭만으로 끝나서 LLM 호출까지 안 간다 — 여기까지 오는 건 소수케이스.
"""
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from backend.core.config import settings

CLOTHING_TRANSLATE_MODEL = "gpt-4o-mini"

CLOTHING_TRANSLATE_PROMPT = """
너는 한글 인상착의 설명을 FashionCLIP(영어 기반 이미지 검색 모델) 쿼리로
번역하는 도우미다.

입력된 한글 인상착의 텍스트를 "a person wearing ..." 형태의 짧고 자연스러운
영어 문장으로 번역한다. 색상·의류 종류·액세서리처럼 외형에 관한 정보만
포함하고, 그 외 정보(이름·나이·키·몸무게·지역·연락처 등)는 넣지 않는다.

인상착의 정보가 전혀 없으면 clothes_en을 null로 둔다. 추측하지 않는다.
"""


class TranslatedClothing(BaseModel):
    clothes_en: str | None = Field(
        None, description='영문 FashionCLIP 쿼리, 예: "a person wearing a black hoodie"'
    )


def translate_clothing_with_llm(clothing_ko: str) -> str | None:
    if not clothing_ko or not clothing_ko.strip():
        return None

    llm = ChatOpenAI(
        model=CLOTHING_TRANSLATE_MODEL, temperature=0, api_key=settings.openai_api_key
    )
    extractor = llm.with_structured_output(TranslatedClothing)
    messages = [
        {"role": "system", "content": CLOTHING_TRANSLATE_PROMPT},
        {"role": "user", "content": clothing_ko},
    ]
    result = extractor.invoke(messages)
    return result.clothes_en
