"""
LLM 사용량 체크를 위한 서비스단
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.db.models import LlmCall
from backend.repositories.llm_call_repository import LLmCallRepository
from backend.schemas.llm_call_schema import (
    CallCreate,
    CallUpdate,
    CallSearchParams,
)


class LlmCallService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = LLmCallRepository(db)

    def _get_or_404(self, id: int) -> LlmCall:
        """
        id로 조회, 없으면 404 예외 발생
        """
        call = self.repository.get_by_id(id)

        if call is None:
            raise HTTPException(
                status_code=404,
                detail="해당 id의 LLM 사용 기록이 없습니다.",
            )

        return call

    def input_call(self, payload: CallCreate) -> LlmCall:
        """
        LLM 호출 기록 생성
        """
        call = self.repository.create(payload)

        self.db.commit()
        self.db.refresh(call)

        return call

    def get_call(self, id: int) -> LlmCall:
        """
        LLM 호출 기록 단건 조회
        """
        return self._get_or_404(id)

    def get_calls(
        self,
        params: CallSearchParams,
    ) -> tuple[list[LlmCall], int]:
        """
        LLM 호출 기록 목록 조회
        """
        return self.repository.get_list(params)

    def update_call(
        self,
        id: int,
        payload: CallUpdate,
    ) -> LlmCall:
        """
        LLM 호출 기록 수정
        """
        self._get_or_404(id)

        call = self.repository.update(id, payload)

        self.db.commit()
        self.db.refresh(call)

        return call

    def delete_call(self, id: int) -> None:
        """
        LLM 호출 기록 삭제
        """
        self._get_or_404(id)

        self.repository.delete(id)

        self.db.commit()
