from core.llm.parser import parse_alert_text

# TODO: LangChain 체인 / 에이전트로 교체


def run_alert_parse_chain(text: str):
    return parse_alert_text(text)
