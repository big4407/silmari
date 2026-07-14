"""인증·검색·분석 체인 정합성 검사."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import (
    Analysis,
    AnalysisDetail,
    AnalysisStatus,
    AuthSession,
    LoginHistory,
    Message,
    Search,
    User,
    Video,
    VideoDetail,
)
from backend.schemas.data_integrity_schema import IntegrityCheckResult
from backend.services.region_integrity import _clip, _status
from backend.utils.timeutils import kst_now


def run_auth_integrity_checks(
    db: Session, *, sample_limit: int | None = 8
) -> list[IntegrityCheckResult]:
    checks: list[IntegrityCheckResult] = []
    user_ids = set(db.scalars(select(User.id)).all())

    if user_ids:
        orphan_sessions = [
            f"session#{sid}"
            for sid, uid in db.execute(
                select(AuthSession.id, AuthSession.user_id).where(
                    ~AuthSession.user_id.in_(user_ids)
                )
            ).all()
        ]
    else:
        orphan_sessions = [
            f"session#{sid}"
            for sid, _ in db.execute(select(AuthSession.id, AuthSession.user_id)).all()
        ]
    checks.append(
        IntegrityCheckResult(
            check_id="session_orphan_user",
            label="끊긴 세션",
            target="auth",
            description="auth_sessions.user_id가 user에 없음",
            status=_status(len(orphan_sessions)),
            issue_count=len(orphan_sessions),
            samples=_clip(orphan_sessions, sample_limit),
        )
    )

    now = kst_now()
    expired_active = list(
        db.scalars(
            select(AuthSession.id).where(
                AuthSession.expires_at < now,
                AuthSession.revoked_at.is_(None),
            )
        ).all()
    )
    checks.append(
        IntegrityCheckResult(
            check_id="session_expired_active",
            label="만료·미철회 세션",
            target="auth",
            description="만료됐으나 revoked_at이 비어 있음",
            status=_status(len(expired_active), warn_threshold=20),
            issue_count=len(expired_active),
            samples=_clip([f"session#{sid}" for sid in expired_active], sample_limit),
        )
    )

    if user_ids:
        orphan_login = [
            f"login#{lid}"
            for lid, uid in db.execute(
                select(LoginHistory.id, LoginHistory.user_id).where(
                    LoginHistory.user_id.isnot(None),
                    ~LoginHistory.user_id.in_(user_ids),
                )
            ).all()
        ]
    else:
        orphan_login = [
            f"login#{lid}"
            for lid, _ in db.execute(
                select(LoginHistory.id, LoginHistory.user_id).where(
                    LoginHistory.user_id.isnot(None)
                )
            ).all()
        ]
    checks.append(
        IntegrityCheckResult(
            check_id="login_orphan_user",
            label="끊긴 로그인 이력",
            target="auth",
            description="login_history.user_id가 user에 없음",
            status=_status(len(orphan_login)),
            issue_count=len(orphan_login),
            samples=_clip(orphan_login, sample_limit),
        )
    )

    return checks


def run_search_integrity_checks(
    db: Session, *, sample_limit: int | None = 8
) -> list[IntegrityCheckResult]:
    checks: list[IntegrityCheckResult] = []
    user_ids = set(db.scalars(select(User.id)).all())
    message_sns = set(db.scalars(select(Message.sn)).all())
    search_ids = set(db.scalars(select(Search.id)).all())
    video_ids = set(db.scalars(select(Video.id)).all())

    if user_ids:
        orphan_search_users = [
            f"search#{sid}"
            for sid, _ in db.execute(
                select(Search.id, Search.user_id).where(~Search.user_id.in_(user_ids))
            ).all()
        ]
    else:
        orphan_search_users = [
            f"search#{sid}"
            for sid, _ in db.execute(select(Search.id, Search.user_id)).all()
        ]
    checks.append(
        IntegrityCheckResult(
            check_id="search_orphan_user",
            label="끊긴 검색 요청자",
            target="search",
            description="search.user_id가 user에 없음",
            status=_status(len(orphan_search_users)),
            issue_count=len(orphan_search_users),
            samples=_clip(orphan_search_users, sample_limit),
        )
    )

    if message_sns:
        orphan_messages = [
            f"search#{sid}:{msn}"
            for sid, msn in db.execute(
                select(Search.id, Search.message_sn).where(
                    Search.message_sn.isnot(None),
                    ~Search.message_sn.in_(message_sns),
                )
            ).all()
        ]
    else:
        orphan_messages = [
            f"search#{sid}:{msn}"
            for sid, msn in db.execute(
                select(Search.id, Search.message_sn).where(
                    Search.message_sn.isnot(None)
                )
            ).all()
        ]
    checks.append(
        IntegrityCheckResult(
            check_id="search_orphan_message",
            label="끊긴 안내문자 참조",
            target="search",
            description="search.message_sn이 message에 없음",
            status=_status(len(orphan_messages)),
            issue_count=len(orphan_messages),
            samples=_clip(orphan_messages, sample_limit),
        )
    )

    if search_ids:
        orphan_analyses = [
            f"analysis#{aid}"
            for aid, sid in db.execute(
                select(Analysis.id, Analysis.search_id).where(
                    ~Analysis.search_id.in_(search_ids)
                )
            ).all()
        ]
    else:
        orphan_analyses = [
            f"analysis#{aid}"
            for aid, _ in db.execute(select(Analysis.id, Analysis.search_id)).all()
        ]
    checks.append(
        IntegrityCheckResult(
            check_id="analysis_orphan_search",
            label="끊긴 검색 참조",
            target="analysis",
            description="analysis.search_id가 search에 없음",
            status=_status(len(orphan_analyses)),
            issue_count=len(orphan_analyses),
            samples=_clip(orphan_analyses, sample_limit),
        )
    )

    if user_ids:
        orphan_analysis_users = [
            f"analysis#{aid}"
            for aid, _ in db.execute(
                select(Analysis.id, Analysis.user_id).where(
                    ~Analysis.user_id.in_(user_ids)
                )
            ).all()
        ]
    else:
        orphan_analysis_users = [
            f"analysis#{aid}"
            for aid, _ in db.execute(select(Analysis.id, Analysis.user_id)).all()
        ]
    checks.append(
        IntegrityCheckResult(
            check_id="analysis_orphan_user",
            label="끊긴 분석 요청자",
            target="analysis",
            description="analysis.user_id가 user에 없음",
            status=_status(len(orphan_analysis_users)),
            issue_count=len(orphan_analysis_users),
            samples=_clip(orphan_analysis_users, sample_limit),
        )
    )

    completed_empty = list(
        db.scalars(
            select(Analysis.id)
            .outerjoin(AnalysisDetail)
            .where(Analysis.analysis_status == AnalysisStatus.COMPLETED)
            .group_by(Analysis.id)
            .having(func.count(AnalysisDetail.id) == 0)
        ).all()
    )
    checks.append(
        IntegrityCheckResult(
            check_id="analysis_completed_empty",
            label="완료·결과 없음",
            target="analysis",
            description="analysis_status=완료인데 analysis_detail이 없음",
            status=_status(len(completed_empty)),
            issue_count=len(completed_empty),
            samples=_clip([f"analysis#{aid}" for aid in completed_empty], sample_limit),
        )
    )

    if video_ids:
        orphan_detail_videos = [
            f"detail#{did}"
            for did, vid in db.execute(
                select(AnalysisDetail.id, AnalysisDetail.video_id).where(
                    ~AnalysisDetail.video_id.in_(video_ids)
                )
            ).all()
        ]
        orphan_video_details = [
            f"video_detail#{did}"
            for did, vid in db.execute(
                select(VideoDetail.id, VideoDetail.video_id).where(
                    ~VideoDetail.video_id.in_(video_ids)
                )
            ).all()
        ]
    else:
        orphan_detail_videos = [
            f"detail#{did}"
            for did, _ in db.execute(
                select(AnalysisDetail.id, AnalysisDetail.video_id)
            ).all()
        ]
        orphan_video_details = [
            f"video_detail#{did}"
            for did, _ in db.execute(select(VideoDetail.id, VideoDetail.video_id)).all()
        ]

    checks.append(
        IntegrityCheckResult(
            check_id="analysis_detail_orphan_video",
            label="끊긴 영상 참조",
            target="analysis",
            description="analysis_detail.video_id가 video에 없음",
            status=_status(len(orphan_detail_videos)),
            issue_count=len(orphan_detail_videos),
            samples=_clip(orphan_detail_videos, sample_limit),
        )
    )

    checks.append(
        IntegrityCheckResult(
            check_id="video_detail_orphan_video",
            label="끊긴 영상 상세",
            target="video",
            description="video_detail.video_id가 video에 없음",
            status=_status(len(orphan_video_details)),
            issue_count=len(orphan_video_details),
            samples=_clip(orphan_video_details, sample_limit),
        )
    )

    return checks
