from typing import TypedDict

from datetime import date


class ChatState(TypedDict):
    user_id: str

    missing_name: str | None
    gender: str | None
    age: int | None

    region: str | None
    region_code: str | None

    start_date: date | None
    end_date: date | None

    appearance: str | None

    validation_step: str | None
    validation_status: str | None

    search_id: int | None
    search_inserted: bool

    response: str | None
    messages: list[dict]
