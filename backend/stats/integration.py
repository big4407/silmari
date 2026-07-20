from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from backend.db.database import get_db


@dataclass(frozen=True)
class StatsActor:
    user_id: str | None
    name: str
    role: str | None = None


def get_stats_actor(request: Request) -> StatsActor:
    """Resolve the current actor from request state.

    If authentication middleware did not populate ``request.state.user``, the
    statistics module still records the action as coming from ``system``.
    """

    user = getattr(request.state, "user", None)
    if user is None:
        return StatsActor(user_id=None, name="system", role=None)

    return StatsActor(
        user_id=getattr(user, "id", None),
        name=(
            getattr(user, "name", None)
            or getattr(user, "username", None)
            or "authenticated-user"
        ),
        role=getattr(user, "role", None),
    )
