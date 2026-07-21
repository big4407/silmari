"""
실종자 관리 케이스 비즈니스 로직 — 상태 전이(대기→진행중→완료)와 담당자 배정.

[흐름] routers/missing_person_cases.py → MissingPersonCaseService →
       MissingPersonCaseRepository (MissingPersonCase ORM)

상태 전이 규칙:
  대기 --(담당하기)--> 진행중 --(완료 처리)--> 완료 (완료는 되돌릴 수 없음)
                진행중 --(담당 취소)--> 대기
"""
from __future__ import annotations

import time

from fastapi import HTTPException
from langchain_community.callbacks import get_openai_callback
from sqlalchemy.orm import Session

from backend.core.llm.alert_parser import ALERT_PARSE_MODEL, parse_alert_message
from backend.db.models import LlmCallType, MissingPersonCase, MissingPersonCaseStatus
from backend.repositories.missing_person_case_repository import (
    MissingPersonCaseRepository,
)
from backend.schemas.missing_person_case_schema import (
    MissingPersonCaseItem,
    MissingPersonCaseListResponse,
    MissingPersonCaseManualCreate,
)
from backend.services.llm_call_service import LlmCallService
from backend.utils.timeutils import kst_now


class MissingPersonCaseService:
    def __init__(self, db: Session, repository: MissingPersonCaseRepository | None = None):
        self.db = db
        self.repository = repository or MissingPersonCaseRepository(db)
        self.llm_call_service = LlmCallService(db)

    @staticmethod
    def _to_item(case: MissingPersonCase) -> MissingPersonCaseItem:
        data = MissingPersonCaseItem.model_validate(case).model_dump()
        data["assigned_investigator_name"] = (
            case.assigned_investigator.full_name or case.assigned_investigator.username
            if case.assigned_investigator
            else None
        )
        return MissingPersonCaseItem(**data)

    def create_from_message(
        self, sn: str, *, msg_cn: str, missing_location: str | None
    ) -> MissingPersonCase:
        """안내문자 1건(sn)당 케이스 1건 — sn 하나당 이미 있으면 새로 안 만든다(멱등).

        같은 sn으로 문자가 다시 수집되는 일은 없다(message.sn은 PK라 재수집 시
        건너뜀, services/message_service.py 참고) — 그래도 방어적으로 확인한다.

        이름/성별/나이/인상착의는 여기서 안 채운다(LLM 비용 — 클래스 docstring
        참고). enrich_from_message()가 필요할 때 그 1건만 채운다.
        """
        existing = self.repository.get_by_sn(sn)
        if existing is not None:
            return existing

        return self.repository.create(
            {
                "sn": sn,
                "msg_cn": msg_cn,
                "missing_location": missing_location,
                "status": MissingPersonCaseStatus.PENDING,
            }
        )

    def enrich_from_message(self, case_id: int) -> MissingPersonCaseItem:
        """안내문자 원문(msg_cn)에서 이름/성별/나이/인상착의를 LLM으로 뽑아 채운다.

        담당자가 케이스를 열어볼 때(또는 명시적으로 눌렀을 때)만 호출되는
        1건짜리 호출이다 — 수집 시점의 배치 파싱과 달리 여기선 비용 걱정 없이
        바로 돌린다. msg_cn이 없는 케이스(챗봇 기반)는 채울 원문 자체가 없어서
        에러를 던진다. 다른 LLM 호출과 동일하게 get_openai_callback()으로 감싸서
        llm_call 테이블에 기록한다(call_type=안내문자 파싱과 같은 성격이라
        재사용 — LLM 운영 관리 화면에서 같이 집계되도록).
        """
        case = self.repository.get_by_id(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="케이스를 찾을 수 없습니다.")
        if not case.msg_cn:
            raise HTTPException(
                status_code=409, detail="이 케이스는 원문(안내문자)이 없어 채울 수 없습니다."
            )

        start = time.perf_counter()
        call_status = "1"
        error_msg = None
        parsed = None
        callback = None

        try:
            with get_openai_callback() as cb:
                callback = cb
                parsed = parse_alert_message(case.msg_cn)
        except Exception as e:
            call_status = "0"
            error_msg = str(e)[:255]
            raise
        finally:
            self.llm_call_service.record_call(
                call_type=LlmCallType.ALERT_PARSE,
                model_name=ALERT_PARSE_MODEL,
                prompt=case.msg_cn,
                response=parsed.model_dump_json() if parsed else None,
                start_time=start,
                callback=callback,
                status=call_status,
                error_msg=error_msg,
            )

        if parsed.missing_name:
            case.missing_name = parsed.missing_name
        if parsed.gender:
            case.gender = parsed.gender
        if parsed.age is not None:
            case.age = parsed.age
        if parsed.clothing:
            case.clothing = parsed.clothing

        self.db.commit()
        self.db.refresh(case)
        return self._to_item(case)

    def create_manual(
        self, payload: MissingPersonCaseManualCreate, *, actor_id: str
    ) -> MissingPersonCaseItem:
        """챗봇 상담 등 안내문자에 안 묶인 케이스 수동 등록 — 등록자가 바로 담당자가 된다."""
        sn = self.repository.next_chatbot_sn()
        now = kst_now()

        case = self.repository.create(
            {
                "sn": sn,
                "missing_name": payload.missing_name,
                "gender": payload.gender,
                "age": payload.age,
                "clothing": payload.clothing,
                "missing_location": payload.missing_location,
                "missing_time": payload.missing_time,
                "notes": payload.notes,
                "status": MissingPersonCaseStatus.IN_PROGRESS,
                "assigned_investigator_id": actor_id,
                "assigned_at": now,
            }
        )
        self.db.commit()
        self.db.refresh(case)
        return self._to_item(case)

    def list_cases(
        self,
        page: int,
        per_page: int,
        *,
        status: str | None = None,
        assigned_investigator_id: str | None = None,
        keyword: str | None = None,
    ) -> MissingPersonCaseListResponse:
        items, total = self.repository.find_all(
            page,
            per_page,
            status=status,
            assigned_investigator_id=assigned_investigator_id,
            keyword=keyword,
        )
        return MissingPersonCaseListResponse(
            items=[self._to_item(c) for c in items], total=total, page=page, per_page=per_page
        )

    def get_case(self, case_id: int) -> MissingPersonCaseItem:
        case = self.repository.get_by_id(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="케이스를 찾을 수 없습니다.")
        return self._to_item(case)

    def assign(
        self, case_id: int, *, actor_id: str, investigator_id: str | None = None
    ) -> MissingPersonCaseItem:
        """"담당하기" — 대기 상태에서만 가능. 담당자 배정과 동시에 진행중으로 넘어간다.

        investigator_id를 지정하면 그 사람을 담당자로 배정한다(관리자가 "담당자
        지정" 드롭다운으로 수사관을 고르는 경우) — 없으면 actor_id(호출한 본인)를
        담당자로 배정한다(수사관이 직접 "담당하기" 누르는 기존 흐름). 관리자만
        investigator_id를 쓸 수 있는지는 라우터에서 역할 확인 후 넘겨준다.
        """
        case = self.repository.get_by_id(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="케이스를 찾을 수 없습니다.")
        if case.status != MissingPersonCaseStatus.PENDING:
            raise HTTPException(
                status_code=409,
                detail="대기 상태인 케이스만 담당을 시작할 수 있습니다.",
            )

        case.assigned_investigator_id = investigator_id or actor_id
        case.assigned_at = kst_now()
        case.status = MissingPersonCaseStatus.IN_PROGRESS
        self.db.commit()
        self.db.refresh(case)
        return self._to_item(case)

    def unassign(self, case_id: int) -> MissingPersonCaseItem:
        """"담당 취소" — 진행중 상태에서만 가능. 대기로 되돌린다(데이터는 안 지움)."""
        case = self.repository.get_by_id(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="케이스를 찾을 수 없습니다.")
        if case.status != MissingPersonCaseStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=409,
                detail="진행중 상태인 케이스만 담당을 취소할 수 있습니다.",
            )

        case.assigned_investigator_id = None
        case.assigned_at = None
        case.status = MissingPersonCaseStatus.PENDING
        self.db.commit()
        self.db.refresh(case)
        return self._to_item(case)

    def resolve(self, case_id: int) -> MissingPersonCaseItem:
        """"완료 처리" — 진행중 상태에서만 가능. 되돌릴 수 없다(통계 안정성을 위한 정책)."""
        case = self.repository.get_by_id(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="케이스를 찾을 수 없습니다.")
        if case.status != MissingPersonCaseStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=409,
                detail="진행중 상태인 케이스만 완료 처리할 수 있습니다.",
            )

        case.status = MissingPersonCaseStatus.RESOLVED
        case.resolved_at = kst_now()
        self.db.commit()
        self.db.refresh(case)
        return self._to_item(case)

    def update_notes(self, case_id: int, notes: str | None) -> MissingPersonCaseItem:
        case = self.repository.get_by_id(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="케이스를 찾을 수 없습니다.")

        case.notes = notes
        self.db.commit()
        self.db.refresh(case)
        return self._to_item(case)