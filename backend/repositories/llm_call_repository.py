"""
llm 사용량 체크를 위한 repository단
"""

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from backend.db.models import LlmCall
from backend.schemas.llm_call_schema import CallCreate, CallUpdate, CallSearchParams


class LLmCallRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: CallCreate) -> LlmCall:
        llm_call = LlmCall(**payload.model_dump())

        self.db.add(llm_call)
        self.db.flush()
        self.db.refresh(llm_call)

        return llm_call

    def get_by_id(self, llm_call_id: int) -> LlmCall | None:
        return self.db.query(LlmCall).filter(LlmCall.id == llm_call_id).first()

    def get_list(
        self,
        params: CallSearchParams,
    ) -> tuple[list[LlmCall], int]:
        query = self.db.query(LlmCall)

        if params.call_type is not None:
            query = query.filter(LlmCall.call_type == params.call_type)

        if params.search_id is not None:
            query = query.filter(LlmCall.search_id == params.search_id)

        if params.user_id is not None:
            query = query.filter(LlmCall.user_id == params.user_id)

        if params.chatbot_s_id is not None:
            query = query.filter(LlmCall.chatbot_s_id == params.chatbot_s_id)

        if params.model_name is not None:
            query = query.filter(LlmCall.model_name == params.model_name)

        if params.status is not None:
            query = query.filter(LlmCall.status == params.status)

        if params.start_date is not None:
            query = query.filter(LlmCall.created_at >= params.start_date)

        if params.end_date is not None:
            query = query.filter(LlmCall.created_at <= params.end_date)

        total = query.count()

        order_column = LlmCall.created_at

        if params.order_by == "oldest":
            query = query.order_by(asc(order_column))
        else:
            query = query.order_by(desc(order_column))

        offset = (params.page - 1) * params.size

        items = query.offset(offset).limit(params.size).all()

        return items, total

    def update(
        self,
        llm_call_id: int,
        payload: CallUpdate,
    ) -> LlmCall | None:
        llm_call = self.get_by_id(llm_call_id)

        if llm_call is None:
            return None

        update_data = payload.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(llm_call, key, value)

        self.db.flush()
        self.db.refresh(llm_call)

        return llm_call

    def delete(self, llm_call_id: int) -> bool:
        llm_call = self.get_by_id(llm_call_id)

        if llm_call is None:
            return False

        self.db.delete(llm_call)
        self.db.flush()

        return True
