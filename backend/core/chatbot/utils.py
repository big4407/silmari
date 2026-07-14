from backend.core.chatbot.state import ChatState


def create_initial_state(user_id: str) -> ChatState:
    return {
        "user_id": user_id,
        "missing_name": None,
        "gender": None,
        "age": None,
        "region": None,
        "region_code": None,
        "start_date": None,
        "end_date": None,
        "appearance": None,
        "validation_step": None,
        "validation_status": None,
        "search_id": None,
        "search_inserted": False,
        "response": "",
        "messages": [
            {
                "role": "assistant",
                "content": "안녕하세요! 실마리 챗봇입니다. 영상을 검색할 지역 및 일자, 인상착의를 입력해 주세요.",
            }
        ],
    }
