from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_community.callbacks import get_openai_callback

from backend.core.config import settings
from backend.chatbot.graph import build_chatbot_graph
from backend.chatbot.utils import create_initial_state
from backend.db.models import ChatbotSession
from backend.services.llm_call_service import LlmCallService
from backend.schemas.llm_call_schema import CallCreate


import json
from pathlib import Path
from datetime import datetime
import time


class ChatbotService:
    def __init__(self, db: Session):
        self.db = db
        self.graph = build_chatbot_graph()
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=settings.openai_api_key,
        )
        self.llm_call_service = LlmCallService(db)

    def chat(self, session_id: str, user_id: str, message: str):
        chatbot_session = self.get_or_create_session(
            user_id=user_id,
            session_id=session_id,
        )

        state = chatbot_session.state_json

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

        except Exception as e:
            call_status = "0"
            error_msg = str(e)[:255]
            raise

        finally:
            latency_ms = int((time.perf_counter() - start) * 1000)

            search_id = result.get("search_id") if result else None

            call_payload = CallCreate(
                call_type="2",  # 챗봇
                search_id=search_id,
                user_id=user_id,
                conversation_id=chatbot_session.id,
                model_name=getattr(self.llm, "model", "unknown"),
                prompt=message,
                response=response,
                input_tokens=cb.prompt_tokens if cb else None,
                output_tokens=cb.completion_tokens if cb else None,
                latency_ms=latency_ms,
                cost=cb.total_cost if cb else None,
                status=call_status,
                error_msg=error_msg,
            )

            self.llm_call_service.input_call(call_payload)

        result["messages"].append(
            {
                "role": "assistant",
                "content": response,
            }
        )

        if result.get("search_inserted"):
            chatbot_session.state_json = create_initial_state(user_id=user_id)
        else:
            chatbot_session.state_json = result

        self.db.commit()
        self.db.refresh(chatbot_session)

        return {
            "response": response,
            "session_id": session_id,
        }

    def get_or_create_session(self, session_id: str, user_id: str) -> ChatbotSession:
        """
        세션을 가져오거나 생성하는 함수
        """
        chatbot_session = (
            self.db.query(ChatbotSession)
            .filter(
                ChatbotSession.session_id == session_id,
                ChatbotSession.user_id == user_id,
            )
            .first()
        )

        if chatbot_session is not None:
            return chatbot_session

        state = create_initial_state(user_id=user_id)

        chatbot_session = ChatbotSession(
            session_id=session_id,
            user_id=user_id,
            state_json=state,
        )

        self.db.add(chatbot_session)
        self.db.commit()
        self.db.refresh(chatbot_session)

        return chatbot_session

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
