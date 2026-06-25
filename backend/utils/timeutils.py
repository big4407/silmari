from datetime import datetime, timezone

def as_utc(value: datetime) -> datetime:
    """naive datetime은 UTC로 간주, aware는 UTC로 변환."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)