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
    CallResponse,
    LlmCallGroupListResponse,
    LlmCallAdminSearchParams,
    MessageLlmCallDetail,
    ChatbotLlmCallDetail,
    LlmCallGroupItem,
)

import time
import math


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

    def update_null_search_id_by_session(
        self,
        *,
        chatbot_s_id: str,
        search_id: int,
    ) -> int:
        return self.repository.update_null_search_id_by_session(
            chatbot_s_id=chatbot_s_id,
            search_id=search_id,
        )

    def record_call(
        self,
        *,
        call_type: str,
        model_name: str,
        prompt: str,
        response: str | None,
        start_time: float,
        callback=None,
        status: str = "1",
        error_msg: str | None = None,
        user_id: str | None = None,
        search_id: int | None = None,
        chatbot_s_id: str | None = None,
    ):
        """
        LLM 호출 정보를 llm_call 테이블에 기록한다.

        이 함수는 이미 수행된 LLM 호출의 사용량, 응답, 지연 시간, 성공/실패 상태를
        공통 형식으로 저장하기 위한 기록용 함수이다.

        사용 위치:
            - 챗봇 응답 생성
            - 인상착의 한영 변환
            - 그 외 프로젝트 내 모든 LLM 호출 지점

        사용 방법:
            1. LLM을 호출하기 직전에 start_time을 기록한다.
               예:
                   start_time = time.perf_counter()

            2. get_openai_callback()을 사용하는 경우, LLM 호출을 with 블록 안에서 실행한다.
               예:
                   with get_openai_callback() as callback:
                       response = llm.invoke(prompt)

            3. LLM 호출이 끝난 뒤 finally 블록에서 이 함수를 호출한다.
               성공/실패와 관계없이 기록을 남기기 위해 finally에서 호출하는 것을 권장한다.

        Args:
            call_type:
                LLM 호출 유형.
                    "1" = 인상착의 한영 변환
                    "2" = 챗봇
                실제 의미는 llm_call 테이블 명세와 맞춰 관리한다.

            model_name:
                사용한 LLM 모델명.
                예:
                    getattr(self.llm, "model", "unknown")

            prompt:
                LLM에 입력한 프롬프트 또는 사용자 입력 메시지.
                챗봇의 경우 사용자 message,
                변환/비교 작업의 경우 실제 LLM에 전달한 prompt를 넣는다.

            response:
                LLM 응답 결과.
                호출 실패로 응답을 받지 못한 경우 None을 넣을 수 있다.

            start_time:
                LLM 호출 직전에 time.perf_counter()로 기록한 시작 시간.
                이 값과 현재 시간을 비교하여 latency_ms를 계산한다.

                주의:
                    start_time은 함수 전체 시작 시간이 아니라,
                    가능하면 실제 LLM 호출 바로 직전에 기록해야 한다.
                    그래야 DB 조회, 전처리, 후처리 시간이 섞이지 않고
                    LLM 호출 지연 시간에 가까운 값이 저장된다.

            callback:
                get_openai_callback()으로 받은 callback 객체.
                prompt_tokens, completion_tokens, total_cost를 기록하는 데 사용한다.
                callback을 사용하지 않았거나 토큰 정보를 얻을 수 없는 경우 None 가능하다.

            status:
                호출 성공 여부.
                기본값은 "1".
                예:
                    "1" = 성공
                    "0" = 실패

            error_msg:
                실패 시 저장할 에러 메시지.
                DB 컬럼 길이를 고려해 호출부에서 str(e)[:255]처럼 잘라 넣는 것을 권장한다.
                성공 시 None.

            user_id:
                LLM 호출을 요청한 사용자 ID.
                비로그인 또는 시스템 호출이면 None 가능하다.

            search_id:
                특정 search 요청과 연결되는 경우 search.id.
                검색 생성 전이라 아직 search_id가 없으면 None으로 저장한 뒤,
                나중에 update_null_search_id_by_session() 같은 후처리로 연결할 수 있다.

            chatbot_s_id:
                챗봇 세션 ID.
                챗봇 호출이 아니면 None.
                챗봇 대화 중 생성된 여러 LLM 호출을 같은 세션 기준으로 묶을 때 사용한다.

        Returns:
            self.input_call(payload)의 반환값.
            보통 생성된 llm_call 테이블의 call 객체를 반환한다.
        """

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        payload = CallCreate(
            call_type=call_type,
            search_id=search_id,
            user_id=user_id,
            chatbot_s_id=chatbot_s_id,
            model_name=model_name,
            prompt=prompt,
            response=response,
            input_tokens=callback.prompt_tokens if callback else None,
            output_tokens=callback.completion_tokens if callback else None,
            latency_ms=latency_ms,
            cost=callback.total_cost if callback else None,
            status=status,
            error_msg=error_msg,
        )

        return self.input_call(payload)

    def get_admin_list(
        self,
        params: LlmCallAdminSearchParams,
    ) -> LlmCallGroupListResponse:
        """
        관리자용 LLM 호출 통합 목록 조회.
        """
        rows, total = self.repository.get_admin_grouped_list(params)
        
        items = [
            LlmCallGroupItem(
                row_key=row.row_key,
                model=row.model,
                call_type=row.call_type,
                chatbot_s_id=row.chatbot_session_id,
                llm_call_id=row.llm_call_id,
                user_id=row.user_id,
                username=row.username,
                search_id=row.search_id,
                call_count=int(row.call_count or 0),
                input_tokens=int(row.input_tokens or 0),
                output_tokens=int(row.output_tokens or 0),
                total_tokens=int(row.total_tokens or 0),
                total_latency_ms=int(row.total_latency_ms or 0),
                cost=float(row.cost or 0),
                avg_latency_ms=round(
                    float(row.avg_latency_ms or 0),
                    2,
                ),
                first_called_at=row.first_called_at,
                last_called_at=row.last_called_at,
            )
            for row in rows
        ]

        return LlmCallGroupListResponse(
            items=items,
            page=params.page,
            size=params.size,
            total=total,
            total_pages=math.ceil(total / params.size) if total else 0,
        )

    def get_message_call_detail(
        self,
        llm_call_id: int,
    ) -> MessageLlmCallDetail:
        """
        안내문자 LLM 호출 상세 조회.

        call_type='1'인 개별 호출만 조회한다.
        """
        call = self._get_or_404(llm_call_id)

        if call.call_type != "1":
            raise HTTPException(
                status_code=404,
                detail="해당 id의 안내문자 LLM 호출 기록이 없습니다.",
            )

        return MessageLlmCallDetail(
            llm_call=CallResponse.model_validate(call),
            search_id=call.search_id,
        )

    def get_chatbot_call_detail(
        self,
        chatbot_s_id: str,
    ) -> ChatbotLlmCallDetail:
        """
        chatbot_s_id에 속한 LLM 호출 목록과 집계 정보 조회.
        """
        calls = self.repository.get_calls_by_chatbot_s_id(chatbot_s_id)

        if not calls:
            raise HTTPException(
                status_code=404,
                detail="해당 챗봇 세션의 LLM 호출 기록이 없습니다.",
            )

        call_count = len(calls)

        input_tokens = sum(call.input_tokens or 0 for call in calls)
        output_tokens = sum(call.output_tokens or 0 for call in calls)

        success_count = sum(1 for call in calls if call.status == "1")
        failure_count = sum(1 for call in calls if call.status == "0")

        success_rate = round(
            success_count / call_count * 100,
            2,
        )

        latency_values = [
            call.latency_ms for call in calls if call.latency_ms is not None
        ]

        avg_latency_ms = (
            round(
                sum(latency_values) / len(latency_values),
                2,
            )
            if latency_values
            else 0.0
        )

        # get_calls_by_chatbot_s_id가 시간 오름차순으로 반환한다고 가정
        first_call = calls[0]

        search_id = next(
            (call.search_id for call in reversed(calls) if call.search_id is not None),
            None,
        )

        return ChatbotLlmCallDetail(
            chatbot_s_id=chatbot_s_id,
            session_id=chatbot_s_id,
            user_id=first_call.user_id,
            search_id=search_id,
            call_count=call_count,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            success_count=success_count,
            failure_count=failure_count,
            success_rate=success_rate,
            avg_latency_ms=avg_latency_ms,
            calls=[CallResponse.model_validate(call) for call in calls],
        )
