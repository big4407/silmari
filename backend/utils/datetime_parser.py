from datetime import date, datetime
from dateutil.parser import parse

# datetime 형식
def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    for fmt in [
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y%m%d%H%M%S",
    ]: # 실제 문자 형식에 맞춰서 수정 필요
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

    raise ValueError(f"지원하지 않는 datetime 형식입니다: {value}")

# date 형식
def parse_date(value: str | None) -> date | None:
    if not value:
        return None

    try:
        return parse(value).date()
    except Exception:
        raise ValueError(f"지원하지 않는 date 형식입니다: {value}")