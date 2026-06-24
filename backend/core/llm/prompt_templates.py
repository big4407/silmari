ALERT_PARSE_PROMPT = """다음 안전안내문자에서 실종자 정보를 추출하세요.

문자 내용:
{text}

다음 JSON 형식으로 반환:
- name: 이름
- age: 나이 (숫자)
- clothes: 옷 색상/종류
- clothes_part: upper | lower | both
"""
