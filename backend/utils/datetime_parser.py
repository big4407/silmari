from datetime import date, datetime


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    value = value.replace("/", "-")

    # .000000000 → .000000 으로 자르기
    if "." in value:
        head, frac = value.split(".", 1)
        value = f"{head}.{frac[:6]}"

    for fmt in [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y%m%d%H%M%S",
    ]:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

    raise ValueError(f"지원하지 않는 datetime 형식입니다: {value}")


def parse_date(value: str | None) -> date | None:
    if not value:
        return None

    value = value.strip()
    value = value.replace("/", "-")

    # 소수점 이하 초 제거
    if "." in value:
        head, frac = value.split(".", 1)
        value = f"{head}.{frac[:6]}"

    for fmt in [
        "%Y-%m-%d",
        "%Y%m%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
    ]:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    raise ValueError(f"지원하지 않는 date 형식입니다: {value}")
