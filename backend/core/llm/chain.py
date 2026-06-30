"""
LLM 파싱 체인 진입점.

현재는 parser.parse_alert_text() 를 직접 호출.
파이프라인(pipeline.py) 1단계에서 sms_text → alert_info 변환에 사용.
"""
from backend.core.llm.parser import parse_alert_text

# TODO: LangChain 체인 / 에이전트로 교체


def run_alert_parse_chain(text: str):
    return parse_alert_text(text)
