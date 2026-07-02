from typing import TypedDict, Any


class ChatState(TypedDict):
    user_id: str

    message_sn: str | None
    missing_name: str | None
    gender: str | None
    age: int | None

    region: str | None
    start_date: str | None
    end_date: str | None
    appearance: str | None

    missing_slots: list[str]
    search_id: int | None

    response: str
    messages: list[dict[str, Any]]

    search_inserted: bool = False
