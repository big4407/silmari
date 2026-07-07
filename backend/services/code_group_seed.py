"""sys_code_group / sys_code_item 기본 시드 — Python enum 과 동기."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import (
    AdminAction,
    AnalysisStatus,
    ApprovalStatus,
    Gender,
    LoginFailStatus,
    SearchType,
    SysCodeGroup,
    SysCodeItem,
    UserRole,
)

# (group_key, group_label, description, sort_order)
_GROUPS: list[tuple[str, str, str, int]] = [
    ("user_role", "사용자 역할", "회원 권한·메뉴 접근에 사용", 1),
    ("approval_status", "가입 승인 상태", "회원 가입·승인 워크플로", 2),
    ("search_type", "검색 유형", "검색 요청 출처", 3),
    ("analysis_status", "분석 상태", "CCTV·영상 분석 진행 상태", 4),
    ("gender", "성별", "실종자·탐지 대상 성별 코드", 5),
    ("login_fail_reason", "로그인 실패 사유", "감사 로그·로그인 이력", 6),
    ("admin_action", "관리자 행동", "감사 로그 행동 유형", 7),
]

# (group_key, code, label, description, sort_order)
_ITEMS: list[tuple[str, str, str, str | None, int]] = [
    ("user_role", UserRole.ADMIN.value, "관리자", None, 1),
    ("user_role", UserRole.INVESTIGATOR.value, "수사관", None, 2),
    ("user_role", UserRole.PUBLIC_OFFICIAL.value, "공무원", None, 3),
    ("approval_status", ApprovalStatus.PENDING.value, "승인 대기", None, 1),
    ("approval_status", ApprovalStatus.APPROVED.value, "승인", None, 2),
    ("approval_status", ApprovalStatus.REJECTED.value, "반려", None, 3),
    ("approval_status", ApprovalStatus.SUSPENDED.value, "정지", None, 4),
    ("search_type", SearchType.SMS.value, "안내문자(SMS)", None, 1),
    ("search_type", SearchType.CHATBOT.value, "챗봇", None, 2),
    ("search_type", SearchType.AUTO.value, "자동검색", None, 3),
    ("analysis_status", AnalysisStatus.NOT_STARTED.value, "분석 전", None, 1),
    ("analysis_status", AnalysisStatus.PARTIAL.value, "부분 완료", None, 2),
    ("analysis_status", AnalysisStatus.COMPLETED.value, "완료", None, 3),
    ("gender", Gender.MALE.value, "남", None, 1),
    ("gender", Gender.FEMALE.value, "여", None, 2),
    (
        "login_fail_reason",
        LoginFailStatus.BAD_CREDENTIALS.value,
        "아이디·비밀번호 불일치",
        None,
        1,
    ),
    ("login_fail_reason", LoginFailStatus.PENDING.value, "승인 대기", None, 2),
    ("login_fail_reason", LoginFailStatus.REJECTED.value, "가입 반려", None, 3),
    ("login_fail_reason", LoginFailStatus.SUSPENDED.value, "계정 정지", None, 4),
    ("login_fail_reason", LoginFailStatus.NO_ROLE.value, "역할 미부여", None, 5),
    ("admin_action", AdminAction.APPROVE.value, "승인", None, 1),
    ("admin_action", AdminAction.REJECT.value, "반려", None, 2),
    ("admin_action", AdminAction.SUSPEND.value, "정지", None, 3),
    ("admin_action", AdminAction.REACTIVATE.value, "재승인", None, 4),
    ("admin_action", AdminAction.DELETE.value, "삭제", None, 5),
    ("admin_action", AdminAction.UPDATE.value, "수정", None, 6),
]


def seed_code_groups_if_empty(db: Session) -> int:
    count = db.scalar(select(func.count()).select_from(SysCodeGroup)) or 0
    if count > 0:
        return 0

    for key, label, desc, order in _GROUPS:
        db.add(
            SysCodeGroup(
                group_key=key,
                group_label=label,
                description=desc,
                sort_order=order,
            )
        )

    for gkey, code, label, desc, order in _ITEMS:
        db.add(
            SysCodeItem(
                group_key=gkey,
                code=code,
                label=label,
                description=desc,
                sort_order=order,
                is_active=True,
            )
        )

    db.commit()
    return len(_GROUPS)
