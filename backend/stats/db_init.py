from __future__ import annotations

from threading import Lock

from sqlalchemy.orm import Session

from .models import stats_metadata

_lock = Lock()
_initialized_bind_ids: set[int] = set()


def ensure_stats_tables(db: Session) -> None:
    """
    통계 API를 처음 호출할 때 통계 전용 테이블만 생성합니다.
    기존 운영 테이블은 수정하지 않습니다.

    운영 배포에서는 Alembic으로 동일 두 테이블을 생성하는 방식이
    더 적합합니다.
    """
    bind = db.get_bind()
    bind_id = id(bind)

    if bind_id in _initialized_bind_ids:
        return

    with _lock:
        if bind_id in _initialized_bind_ids:
            return

        stats_metadata.create_all(
            bind=bind,
            checkfirst=True,
        )
        _initialized_bind_ids.add(bind_id)
