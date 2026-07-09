def create_initial_state(user_id: str):
    return {
        "user_id": user_id,
        "message_sn": None,
        "missing_name": None,
        "gender": None,
        "age": None,
        "region": None,
        "start_date": None,
        "end_date": None,
        "appearance": None,
        "missing_slots": [],
        "search_id": None,
        "response": "",
        "messages": [
            {
                "role": "assistant",
                "content": "안녕하세요! 실마리 챗봇입니다. 영상을 검색할 지역 및 일자, 인상착의를 입력해 주세요.",
            }
        ],
        "search_inserted": False,
    }
