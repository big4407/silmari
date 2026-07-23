from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_community.callbacks import get_openai_callback

from backend.core.config import settings
from backend.core.chatbot.graph import build_chatbot_graph
from backend.core.chatbot.utils import create_initial_state
from backend.db.models import ChatbotSession, LlmCallType, UserRole
from backend.repositories.chatbot_repository import ChatbotRepository

from backend.services.llm_call_service import LlmCallService
import time


class ChatbotService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ChatbotRepository(db)
        self.graph = build_chatbot_graph()
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=settings.openai_api_key,
        )
        self.llm_call_service = LlmCallService(db)

    def chat(self, session_id: str, user_id: str, message: str, user_role: str | None = None):
        chatbot_session = self.get_or_create_session(
            user_id=user_id,
            session_id=session_id,
        )

        state = chatbot_session.state_json
        # 기존 세션 복구 시에도 항상 실제 로그인 사용자로 맞춰준다.
        # (예전 버전은 session_id를 user_id로 잘못 저장해 검색 생성 시
        #  user.id FK 제약을 위반했다 — 기존 세션 상태도 여기서 자연히 복구됨)
        state["user_id"] = user_id

        state["messages"].append(
            {
                "role": "user",
                "content": message,
            }
        )

        start = time.perf_counter()
        call_status = "1"
        error_msg = None
        response = None
        result = None
        cb = None

        try:
            with get_openai_callback() as callback:
                cb = callback

                result = self.graph.invoke(
                    state,
                    config={
                        "configurable": {
                            "db": self.db,
                            "llm": self.llm,
                        }
                    },
                )

            response = result.get("response")

            # 공무원 역할은 실종자 관리 시스템 접근 권한이 없어(관리자·수사관
            # 전용) "케이스로 추가하시겠습니까?" 질문 자체가 의미 없다. 검색이
            # 막 완료된 시점에만 이 질문이 붙으므로, 그 문구를 떼고 그냥 검색
            # 완료 안내만 남긴다.
            if (
                result.get("search_inserted")
                and user_role == UserRole.PUBLIC_OFFICIAL.value
            ):
                response = "영상 검색을 완료했습니다."
                result["response"] = response

        except Exception as e:
            call_status = "0"
            error_msg = str(e)[:255]
            raise

        finally:
            search_id = result.get("search_id") if result else None

            self.llm_call_service.record_call(
                call_type=LlmCallType.CHATBOT,
                model_name=getattr(self.llm, "model", "unknown"),
                prompt=message,
                response=response,
                start_time=start,
                callback=cb,
                status=call_status,
                error_msg=error_msg,
                user_id=user_id,
                search_id=search_id,
                chatbot_s_id=session_id,
            )

        result["messages"].append(
            {
                "role": "assistant",
                "content": response,
            }
        )

        if result.get("search_inserted"):
            if search_id:
                self.llm_call_service.update_null_search_id_by_session(
                    chatbot_s_id=session_id,
                    search_id=search_id,
                )
            self.repository.delete(chatbot_session)
            session_id = None
        else:
            chatbot_session.state_json = result

        self.db.commit()

        search_inserted = result.get("search_inserted", False) if result else False
        # 실종자 관리 시스템은 관리자·수사관 전용이라 공무원 역할에는
        # "추가하기/조회만" 버튼을 아예 보여주지 않는다.
        offer_case_registration = (
            search_inserted and user_role != UserRole.PUBLIC_OFFICIAL.value
        )

        return {
            "response": response,
            "session_id": session_id,
            "search_id": result.get("search_id") if result else None,
            "search_inserted": search_inserted,
            # 검색이 막 완료된 경우에만 "케이스로 추가할까요?" 선택지를 보여준다.
            # 프론트가 이 값이 True일 때만 두 버튼(추가하기/조회만)을 렌더링하고,
            # False면 기존처럼 그냥 검색 결과로 넘어간다.
            "offer_case_registration": offer_case_registration,
            "case_prefill": (
                {
                    "missing_name": result.get("missing_name"),
                    "gender": result.get("gender"),
                    "age": result.get("age"),
                    "clothing": result.get("appearance"),
                    "missing_location": result.get("region"),
                }
                if offer_case_registration
                else None
            ),
        }

    def get_or_create_session(self, session_id: str, user_id: str) -> ChatbotSession:
        """
        세션을 가져오거나 생성하는 함수
        """
        chatbot_session = self.repository.get_by_session_id_and_user_id(
            session_id=session_id,
            user_id=user_id,
        )

        if chatbot_session is not None:
            return chatbot_session

        state = create_initial_state(user_id=user_id)

        session = self.repository.create(
            session_id=session_id,
            user_id=user_id,
            state_json=state,
        )
        self.db.commit()
        return session

    def exist_session(self, user_id: str, session_id: str | None) -> bool:
        """
        user_id와 session_id를 받아 session이 존재하는지 검증
        """
        if self.repository.get_by_session_id_and_user_id(
            session_id=session_id,
            user_id=user_id,
        ):
            return True
        return False

    def get_session_by_user_id(self, user_id: str) -> ChatbotSession | None:
        """
        user_id만으로 session을 가져오는 함수. 만약 없으면 가져오지 않음
        """
        return self.repository.get_by_user_id(
            user_id=user_id,
        )

    def get_session_messages(self, user_id: str, session_id: str):
        """
        세션에서 메시지를 가져오는 함수
        """
        chatbot_session = self.get_or_create_session(
            user_id=user_id, session_id=session_id
        )

        state = chatbot_session.state_json or {}

        return {
            "session_id": session_id,
            "messages": state.get("messages", []),
        }

    def delete_user_session(self, user_id: str) -> None:
        session = self.repository.get_by_user_id(user_id=user_id)

        if session is None:
            return

        self.repository.delete(session)
        self.db.commit()