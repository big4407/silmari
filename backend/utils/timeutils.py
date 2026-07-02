"""datetime 유틸.

- as_utc: JWT/세션 만료 비교(deps, auth_service)에 사용 — 인증 계산은 UTC 기준.
- kst_now: DB 기록성 시간(created_at 등)의 기본값 — 국내 전용이라 KST로 저장.

[정책] 길 B — 기록성 시간은 KST 저장, 만료/인증 계산은 UTC 유지.
"""

from datetime import datetime, timedelta, timezone

# 한국 표준시 (UTC+9, 서머타임 없음)
KST = timezone(timedelta(hours=9))


def as_utc(value: datetime) -> datetime:
    """naive datetime은 UTC로 간주, aware는 UTC로 변환."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def kst_now() -> datetime:
    """현재 시각을 KST(naive)로 반환 — DB 기록성 시간 기본값용.

    tzinfo를 떼어낸 naive KST 를 돌려준다. DateTime 컬럼(timezone 미지정)에
    그대로 저장되어, DB를 직접 조회하면 한국시간으로 보인다.
    """
    return datetime.now(KST).replace(tzinfo=None)
