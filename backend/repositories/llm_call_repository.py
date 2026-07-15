"""
llm 사용량 체크를 위한 repository단
"""

from sqlalchemy import (
    Integer,
    String,
    asc,
    cast,
    desc,
    func,
    literal,
)
from sqlalchemy.orm import Session, Query


from backend.db.models import LlmCall, User
from backend.schemas.llm_call_schema import (
    CallCreate,
    CallUpdate,
    CallSearchParams,
    LlmCallAdminSearchParams,
)


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

    def get_admin_grouped_list(
        self,
        params: LlmCallAdminSearchParams,
    ) -> tuple[list, int]:
        """
        관리자용 LLM 호출 목록 조회.

        안내문자 호출은 한 건당 한 행으로 반환하고,
        챗봇 호출은 chatbot_s_id 단위로 집계한다.

        call_type이 None이면 두 결과를 합쳐서 반환한다.
        """
        queries = []

        if params.call_type in (None, "1"):
            message_query = self._build_message_admin_query(params)
            queries.append(message_query)

        if params.call_type in (None, "2"):
            chatbot_query = self._build_chatbot_admin_query(params)
            queries.append(chatbot_query)

        if not queries:
            # call_type=3(안내문자 파싱)처럼 이 그룹 조회가 아직 다루지 않는
            # 값이 들어오면 조합할 쿼리가 하나도 없다 — 그대로 두면 아래
            # queries[0]에서 IndexError가 난다.
            return [], 0

        if len(queries) == 1:
            grouped_subquery = queries[0].subquery()
        else:
            grouped_subquery = queries[0].union_all(*queries[1:]).subquery()

        total = self.db.query(func.count()).select_from(grouped_subquery).scalar() or 0

        query = self.db.query(
            *grouped_subquery.c,
            User.username.label("username"),
        ).outerjoin(
            User,
            User.id == grouped_subquery.c.user_id,
        )

        if params.order_by == "oldest":
            query = query.order_by(
                asc(grouped_subquery.c.last_called_at),
                asc(grouped_subquery.c.row_key),
            )
        else:
            query = query.order_by(
                desc(grouped_subquery.c.last_called_at),
                desc(grouped_subquery.c.row_key),
            )

        offset = (params.page - 1) * params.size

        items = query.offset(offset).limit(params.size).all()

        return items, total

    def _build_message_admin_query(
        self,
        params: LlmCallAdminSearchParams,
    ):
        """
        call_type='1' 호출을 한 건당 한 행으로 구성한다.
        """

        input_tokens = func.coalesce(
            LlmCall.input_tokens,
            0,
        )

        output_tokens = func.coalesce(
            LlmCall.output_tokens,
            0,
        )

        latency_ms = func.coalesce(
            LlmCall.latency_ms,
            0,
        )

        cost = func.coalesce(LlmCall.cost, 0)

        query = self.db.query(
            LlmCall.model_name.label("model"),
            func.concat(
                "call-",
                cast(LlmCall.id, String),
            ).label("row_key"),
            literal("1").label("call_type"),
            cast(
                literal(None),
                String(36),
            ).label("chatbot_session_id"),
            LlmCall.id.label("llm_call_id"),
            LlmCall.user_id.label("user_id"),
            LlmCall.search_id.label("search_id"),
            literal(1).label("call_count"),
            input_tokens.label("input_tokens"),
            output_tokens.label("output_tokens"),
            (input_tokens + output_tokens).label("total_tokens"),
            latency_ms.label("total_latency_ms"),
            cast(
                latency_ms,
                Integer,
            ).label("avg_latency_ms"),
            cost.label("cost"),
            LlmCall.created_at.label("first_called_at"),
            LlmCall.created_at.label("last_called_at"),
        ).filter(LlmCall.call_type == "1")

        return self._apply_admin_filters(
            query=query,
            params=params,
        )

    def _build_chatbot_admin_query(
        self,
        params: LlmCallAdminSearchParams,
    ):
        """
        call_type='2' 호출을 chatbot_s_id 단위로 집계한다.
        """
        input_tokens = func.coalesce(
            func.sum(LlmCall.input_tokens),
            0,
        )

        output_tokens = func.coalesce(
            func.sum(LlmCall.output_tokens),
            0,
        )

        total_latency_ms = func.coalesce(
            func.sum(LlmCall.latency_ms),
            0,
        )

        avg_latency_ms = func.coalesce(
            func.avg(LlmCall.latency_ms),
            0,
        )

        cost = func.coalesce(
            func.sum(LlmCall.cost),
            0,
        )

        query = self.db.query(
            LlmCall.model_name.label("model"),
            func.concat(
                "chatbot-",
                LlmCall.chatbot_s_id,
            ).label("row_key"),
            literal("2").label("call_type"),
            LlmCall.chatbot_s_id.label("chatbot_session_id"),
            cast(
                literal(None),
                Integer,
            ).label("llm_call_id"),
            func.max(LlmCall.user_id).label("user_id"),
            func.max(LlmCall.search_id).label("search_id"),
            func.count(LlmCall.id).label("call_count"),
            input_tokens.label("input_tokens"),
            output_tokens.label("output_tokens"),
            (input_tokens + output_tokens).label("total_tokens"),
            total_latency_ms.label("total_latency_ms"),
            avg_latency_ms.label("avg_latency_ms"),
            cost.label("cost"),
            func.min(LlmCall.created_at).label("first_called_at"),
            func.max(LlmCall.created_at).label("last_called_at"),
        ).filter(
            LlmCall.call_type == "2",
            LlmCall.chatbot_s_id.isnot(None),
        )

        query = self._apply_admin_filters(
            query=query,
            params=params,
        )

        return query.group_by(
            LlmCall.chatbot_s_id,
        )

    def _apply_admin_filters(
        self,
        query: Query,
        params: LlmCallAdminSearchParams,
    ) -> Query:
        """
        관리자 목록 공통 검색 조건 적용.

        call_type은 각 조회 쿼리에서 고정하므로 여기서는 처리하지 않는다.
        """
        if params.search_id is not None:
            query = query.filter(LlmCall.search_id == params.search_id)

        if params.user_id is not None:
            query = query.filter(LlmCall.user_id == params.user_id)

        if params.model_name is not None:
            query = query.filter(LlmCall.model_name == params.model_name)

        if params.status is not None:
            query = query.filter(LlmCall.status == params.status)

        if params.start_date is not None:
            query = query.filter(LlmCall.created_at >= params.start_date)

        if params.end_date is not None:
            query = query.filter(LlmCall.created_at <= params.end_date)

        return query

    def get_calls_by_chatbot_s_id(
        self,
        chatbot_s_id: str,
    ) -> list[LlmCall]:
        """
        chatbot_s_id에 속한 챗봇 LLM 호출 목록 조회.

        상세 화면에서 호출 순서를 그대로 보여주기 위해
        생성일시와 id 기준 오름차순으로 정렬한다.
        """
        return (
            self.db.query(LlmCall)
            .filter(
                LlmCall.call_type == "2",
                LlmCall.chatbot_s_id == chatbot_s_id,
            )
            .order_by(
                asc(LlmCall.created_at),
                asc(LlmCall.id),
            )
            .all()
        )

    def update_null_search_id_by_session(
        self, chatbot_s_id: str, search_id: int
    ) -> None:
        """세션의 search_id 가 아직 비어있는(검색 생성 전) 기록들을 일괄 채운다."""
        (
            self.db.query(LlmCall)
            .filter(
                LlmCall.chatbot_s_id == chatbot_s_id,
                LlmCall.search_id.is_(None),
            )
            .update(
                {LlmCall.search_id: search_id},
                synchronize_session=False,
            )
        )