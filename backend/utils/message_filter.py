"""
재난문자 중 실종 안내문자 판별 필터.

[조건] 재해구분명(dst_se_nm) == "기타" AND 실종 키워드 포함 AND 제외 키워드 없음
[사용] message_service.collect_messages, safetydata_client
"""
# 실종자 문자는 재난 문자에서 재해구분명 기타에만 속해있음
MISSING_PERSON_DISASTER_TYPE = "기타"

# 실종자 문자라고 판단할 만한 키워드
MISSING_PERSON_KEYWORDS = [
    "실종",
    "찾습",
    "배회",
    "가출",
    "목격",
    "보호",
    "찾고",
]

# 제외 키워드
EXCLUDE_KEYWORDS = [
    "물놀이",
    "수상안전",
    "보호장비",
]


def is_missing_person_message(
    msg_cn: str,
    dst_se_nm: str | None,
) -> bool:
    """
    메시지를 받아서 실종자 문자인지 판단하는 함수
    """
    # 재해구분명이 기타가 아닐 경우
    if dst_se_nm != MISSING_PERSON_DISASTER_TYPE:
        return False

    # 제외 키워드가 하나라도 들어가면 실종자 문자가 아니라고 판단
    if any(keyword in msg_cn for keyword in EXCLUDE_KEYWORDS):
        return False

    # 키워드가 하나라도 들어가는 경우 실종자 문자라고 판단
    return any(keyword in msg_cn for keyword in MISSING_PERSON_KEYWORDS)
    # return msg_cn # 필터링 없이 테스트 할 때용
