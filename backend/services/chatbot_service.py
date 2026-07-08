from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_community.callbacks import get_openai_callback

from backend.core.config import settings
from backend.chatbot.graph import build_chatbot_graph
from backend.chatbot.utils import create_initial_state
from backend.db.models import ChatbotSession


import json
from pathlib import Path
from datetime import datetime
import time


class ChatbotService:
    def __init__(self, db: Session):
        self.db = db
        self.graph = build_chatbot_graph()
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=settings.openai_api_key,)

    def chat(self, session_id: str, user_id: str, message: str):
        """
        챗봇과 채팅하는 함수. session_id, user_id가 필요하고 메시지를 입력해야 한다.
        """
        # 세션이 있으면 가져오고, 없으면 생성한다
        chatbot_session = self.get_or_create_session(
            user_id=user_id,
            session_id=session_id,
        )

        # 챗봇과의 채팅 세션에서 state를 가져온다
        state = chatbot_session.state_json

        # state에 유저 메시지 추가
        state["messages"].append(
            {
                "role": "user",
                "content": message,
            }
        )

        start = time.perf_counter()
        status = "1"
        error_msg = None
        response = None
        result = None

        try:
            with get_openai_callback() as cb:
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
            status = "0"
            error_msg = str(e)[:255]
            cb = None
            raise

        finally:
            latency_ms = int((time.perf_counter() - start) * 1000)

            record = {
                "call_type": "2",  # 챗봇
                "search_id": None,
                "user_id": None,
                "conversation_id": None,
                "model_name": getattr(self.llm, "model_name", "gpt-4o-mini"),
                "prompt": message,
                "response": response,
                "input_tokens": cb.prompt_tokens if cb else None,
                "output_tokens": cb.completion_tokens if cb else None,
                "latency_ms": latency_ms,
                "cost": cb.total_cost if cb else None,
                "status": status,
                "error_msg": error_msg,
                "created_at": datetime.now().isoformat(),
            }

            self.save_llm_call_jsonl(record)

        # state에 챗봇 메시지 추가
        result["messages"].append(
            {
                "role": "assistant",
                "content": response,
            }
        )

        # 성공적으로 search 테이블에 insert했다면 state를 초기화
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
