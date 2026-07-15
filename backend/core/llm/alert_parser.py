"""
안내문자 본문(msg_cn)에서 LLM으로 실종자 정보를 구조화 추출한다.

실제 문자는 "인상착의:" 같은 정형 라벨 없이 자유 서식으로 온다. 예:
  "해운대구 주민인 노영찬씨(남,76세)를 찾습니다-163cm,60kg,파란색티,검정바지,
   검정신발,흰머리 vo.la/GhZjLn / ☎182 [부산경찰청]"
정규식으로는 한계가 있어(라벨도 없고, 나이·키·몸무게·옷차림이 쉼표로 뒤섞여
나열됨) LLM 구조화 출력을 쓴다 — core/chatbot의 슬롯 추출과 같은 패턴.
"""
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from backend.core.config import settings

ALERT_PARSE_MODEL = "gpt-4o-mini"

ALERT_PARSE_PROMPT = """
너는 실종자 안내문자에서 정보를 추출하는 도우미다.

문자 본문에서 다음 정보를 추출한다.
- missing_name: 실종자 이름. "노영찬씨"처럼 호칭이 붙어있으면 이름만 뽑는다
  (예: "노영찬").
- gender: 성별. "M"(남) 또는 "F"(여) 코드로만 답한다. 모르면 null.
- age: 나이(숫자만). "76세"면 76. 모르면 null.
- clothing: 인상착의 — 옷 색상·종류, 신발, 머리색 등 외형 관련 정보만 모아
  자연스러운 문장으로 정리한다("파란색 티셔츠, 검정 바지, 검정 신발, 흰머리"
  처럼). 키·몸무게처럼 옷차림이 아닌 정보, 연락처·단축URL·기관명·신고 안내
  문구(예: "☎182", "vo.la/...", "[부산경찰청]")는 포함하지 않는다.

알 수 없는 값은 null로 둔다. 추측하지 않는다.
"""


class ExtractedAlertInfo(BaseModel):
    """LLM 구조화 출력 스키마 — HTTP 응답 스키마는 schemas/message_schema.py에 별도."""

    missing_name: str | None = Field(None, description="실종자 이름")
    gender: str | None = Field(None, description='"M" 또는 "F"')
    age: int | None = Field(None, description="나이")
    clothing: str | None = Field(None, description="인상착의(옷차림 관련 정보만)")


def parse_alert_message(msg_cn: str) -> ExtractedAlertInfo:
    if not msg_cn or not msg_cn.strip():
        return ExtractedAlertInfo()

    llm = ChatOpenAI(
        model=ALERT_PARSE_MODEL, temperature=0, api_key=settings.openai_api_key
    )
    extractor = llm.with_structured_output(ExtractedAlertInfo)
    messages = [
        {"role": "system", "content": ALERT_PARSE_PROMPT},
        {"role": "user", "content": msg_cn},
    ]
    result = extractor.invoke(messages)

    # gender 코드 정규화 — LLM이 "남"/"남성" 등 다른 표기를 줄 경우를 대비.
    if result.gender:
        g = result.gender.strip().upper()
        result.gender = g if g in ("M", "F") else None

    # DB 컬럼 길이 제한(SearchCreate: missing_name<=20, clothing<=100)에 맞춘다.
    if result.missing_name:
        result.missing_name = result.missing_name[:20]
    if result.clothing:
        result.clothing = result.clothing[:100]

    return result