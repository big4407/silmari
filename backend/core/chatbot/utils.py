def create_initial_state(user_id: str):
    return {
        "user_id": user_id,
        "message_sn": None,
        "missing_name": None,
        "gender": None,
        "age": None,
        "region": None,
        "start_time": None,
        "end_time": None,
        "appearance": None,
        "missing_slots": [],
        "search_id": None,
        "response": "",
        "messages": [],
    }
