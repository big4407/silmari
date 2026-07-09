"""행정구역·연관 테이블·감사 이력 정합성 검사."""

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
    Region,
    Search,
    User,
    Video,
    VideoDetail,
)
from backend.repositories.integrity_repository import IntegrityRepository
from backend.schemas.data_integrity_schema import IntegrityCheckResult, IntegrityRunResponse
from backend.utils.timeutils import kst_now


def _status(count: int, warn_threshold: int = 0) -> str:
    if count == 0:
        return "ok"
    if count <= warn_threshold:
        return "warn"
    return "error"


def _clip(items: list[str], sample_limit: int | None) -> list[str]:
    if sample_limit is None:
        return items
    return items[:sample_limit]


class IntegrityService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = IntegrityRepository(db)

    def run_suite(
        self, *, sample_limit: int | None = 8
    ) -> tuple[list[IntegrityCheckResult], int]:
        checks = [
            *self._run_region_checks(sample_limit=sample_limit),
            *self._run_auth_checks(sample_limit=sample_limit),
            *self._run_search_checks(sample_limit=sample_limit),
        ]
        total = sum(c.issue_count for c in checks if c.status != "ok")
        return checks, total

    def find_check(
        self, check_id: str, *, sample_limit: int | None = None
    ) -> IntegrityCheckResult | None:
        """check_id에 해당하는 검사 1건. sample_limit=None이면 전체 이슈 목록."""
        checks, _ = self.run_suite(sample_limit=sample_limit)
        for check in checks:
            if check.check_id == check_id:
                return check
        return None

    def get_previous_total(self) -> int | None:
        return self.repository.get_previous_total_issues()

    def record_run(
        self,
        *,
        actor_id: str,
        checks: list[IntegrityCheckResult],
        total_issues: int,
        delta_issues: int | None,
        ip_address: str | None,
    ) -> str | None:
        return self.repository.record_run(
            actor_id=actor_id,
            checks=checks,
            total_issues=total_issues,
            delta_issues=delta_issues,
            ip_address=ip_address,
        )

    def latest_run(self) -> IntegrityRunResponse | None:
        return self.repository.latest_run()

    def get_run_by_id(self, run_id: str) -> IntegrityRunResponse | None:
        return self.repository.get_run_by_id(run_id)

    def _run_region_checks(
        self, *, sample_limit: int | None = 8
    ) -> list[IntegrityCheckResult]:
        checks: list[IntegrityCheckResult] = []

        all_codes = set(self.db.scalars(select(Region.region_code)).all())

        if all_codes:
            orphan_parents = list(
                self.db.scalars(
                    select(Region.region_code).where(
                        Region.parent_code.isnot(None),
                        ~Region.parent_code.in_(all_codes),
                    )
                ).all()
            )
        else:
            orphan_parents = list(
                self.db.scalars(
                    select(Region.region_code).where(Region.parent_code.isnot(None))
                ).all()
            )
        checks.append(
            IntegrityCheckResult(
                check_id="region_orphan_parent",
                label="끊긴 상위 참조",
                target="region",
                description="parent_code가 region 테이블에 존재하지 않음",
                status=_status(len(orphan_parents)),
                issue_count=len(orphan_parents),
                samples=_clip(orphan_parents, sample_limit),
            )
        )

        self_parents = list(
            self.db.scalars(
                select(Region.region_code).where(
                    Region.parent_code == Region.region_code
                )
            ).all()
        )
        checks.append(
            IntegrityCheckResult(
                check_id="region_self_parent",
                label="자기 참조",
                target="region",
                description="parent_code가 자신의 region_code와 동일",
                status=_status(len(self_parents)),
                issue_count=len(self_parents),
                samples=_clip(self_parents, sample_limit),
            )
        )

        parent_map = {
            code: parent
            for code, parent in self.db.execute(
                select(Region.region_code, Region.parent_code)
            ).all()
        }
        cyclic: list[str] = []
        for code in parent_map:
            seen: set[str] = set()
            cursor: str | None = code
            while cursor:
                if cursor in seen:
                    cyclic.append(code)
                    break
                seen.add(cursor)
                cursor = parent_map.get(cursor)
        checks.append(
            IntegrityCheckResult(
                check_id="region_cycle",
                label="계층 순환",
                target="region",
                description="parent_code 체인에 순환 참조 존재",
                status=_status(len(cyclic)),
                issue_count=len(cyclic),
                samples=_clip(cyclic, sample_limit),
            )
        )

        missing_names = list(
            self.db.scalars(
                select(Region.region_code).where(
                    Region.full_name.is_(None),
                    Region.specific_name.is_(None),
                )
            ).all()
        )
        checks.append(
            IntegrityCheckResult(
                check_id="region_missing_name",
                label="명칭 누락",
                target="region",
                description="full_name·specific_name 모두 비어 있음",
                status=_status(len(missing_names), warn_threshold=5),
                issue_count=len(missing_names),
                samples=_clip(missing_names, sample_limit),
            )
        )

        if all_codes:
            orphan_videos = [
                f"video#{vid}:{rcode}"
                for vid, rcode in self.db.execute(
                    select(Video.id, Video.region_code).where(
                        Video.region_code.isnot(None),
                        ~Video.region_code.in_(all_codes),
                    )
                ).all()
            ]
        else:
            orphan_videos = [
                f"video#{vid}:{rcode}"
                for vid, rcode in self.db.execute(
                    select(Video.id, Video.region_code).where(
                        Video.region_code.isnot(None)
                    )
                ).all()
            ]
        checks.append(
            IntegrityCheckResult(
                check_id="video_orphan_region",
                label="영상 지역 코드",
                target="video",
                description="video.region_code가 region에 없음",
                status=_status(len(orphan_videos)),
                issue_count=len(orphan_videos),
                samples=_clip(orphan_videos, sample_limit),
            )
        )

        return checks

    def _run_auth_checks(
        self, *, sample_limit: int | None = 8
    ) -> list[IntegrityCheckResult]:
        checks: list[IntegrityCheckResult] = []
        user_ids = set(self.db.scalars(select(User.id)).all())

        if user_ids:
            orphan_sessions = [
                f"session#{sid}"
                for sid, uid in self.db.execute(
                    select(AuthSession.id, AuthSession.user_id).where(
                        ~AuthSession.user_id.in_(user_ids)
                    )
                ).all()
            ]
        else:
            orphan_sessions = [
                f"session#{sid}"
                for sid, _ in self.db.execute(
                    select(AuthSession.id, AuthSession.user_id)
                ).all()
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
            self.db.scalars(
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
                samples=_clip(
                    [f"session#{sid}" for sid in expired_active], sample_limit
                ),
            )
        )

        if user_ids:
            orphan_login = [
                f"login#{lid}"
                for lid, uid in self.db.execute(
                    select(LoginHistory.id, LoginHistory.user_id).where(
                        LoginHistory.user_id.isnot(None),
                        ~LoginHistory.user_id.in_(user_ids),
                    )
                ).all()
            ]
        else:
            orphan_login = [
                f"login#{lid}"
                for lid, _ in self.db.execute(
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

    def _run_search_checks(
        self, *, sample_limit: int | None = 8
    ) -> list[IntegrityCheckResult]:
        checks: list[IntegrityCheckResult] = []
        user_ids = set(self.db.scalars(select(User.id)).all())
        message_sns = set(self.db.scalars(select(Message.sn)).all())
        search_ids = set(self.db.scalars(select(Search.id)).all())
        video_ids = set(self.db.scalars(select(Video.id)).all())

        if user_ids:
            orphan_search_users = [
                f"search#{sid}"
                for sid, _ in self.db.execute(
                    select(Search.id, Search.user_id).where(
                        ~Search.user_id.in_(user_ids)
                    )
                ).all()
            ]
        else:
            orphan_search_users = [
                f"search#{sid}"
                for sid, _ in self.db.execute(select(Search.id, Search.user_id)).all()
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
                for sid, msn in self.db.execute(
                    select(Search.id, Search.message_sn).where(
                        Search.message_sn.isnot(None),
                        ~Search.message_sn.in_(message_sns),
                    )
                ).all()
            ]
        else:
            orphan_messages = [
                f"search#{sid}:{msn}"
                for sid, msn in self.db.execute(
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
                for aid, sid in self.db.execute(
                    select(Analysis.id, Analysis.search_id).where(
                        ~Analysis.search_id.in_(search_ids)
                    )
                ).all()
            ]
        else:
            orphan_analyses = [
                f"analysis#{aid}"
                for aid, _ in self.db.execute(
                    select(Analysis.id, Analysis.search_id)
                ).all()
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
                for aid, _ in self.db.execute(
                    select(Analysis.id, Analysis.user_id).where(
                        ~Analysis.user_id.in_(user_ids)
                    )
                ).all()
            ]
        else:
            orphan_analysis_users = [
                f"analysis#{aid}"
                for aid, _ in self.db.execute(
                    select(Analysis.id, Analysis.user_id)
                ).all()
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
            self.db.scalars(
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
                samples=_clip(
                    [f"analysis#{aid}" for aid in completed_empty], sample_limit
                ),
            )
        )

        if video_ids:
            orphan_detail_videos = [
                f"detail#{did}"
                for did, vid in self.db.execute(
                    select(AnalysisDetail.id, AnalysisDetail.video_id).where(
                        ~AnalysisDetail.video_id.in_(video_ids)
                    )
                ).all()
            ]
            orphan_video_details = [
                f"video_detail#{did}"
                for did, vid in self.db.execute(
                    select(VideoDetail.id, VideoDetail.video_id).where(
                        ~VideoDetail.video_id.in_(video_ids)
                    )
                ).all()
            ]
        else:
            orphan_detail_videos = [
                f"detail#{did}"
                for did, _ in self.db.execute(
                    select(AnalysisDetail.id, AnalysisDetail.video_id)
                ).all()
            ]
            orphan_video_details = [
                f"video_detail#{did}"
                for did, _ in self.db.execute(
                    select(VideoDetail.id, VideoDetail.video_id)
                ).all()
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
