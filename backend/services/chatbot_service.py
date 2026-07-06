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
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=settings.openai_api_key,
        )

    USAGE_FILE = Path("llm_call_log.jsonl")

    def save_llm_call_jsonl(self, record: dict):
        with self.USAGE_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def chat(self, session_id: str, message: str):
        chatbot_session = self.get_or_create_session(session_id)

        state = chatbot_session.state_json

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

        chatbot_session.state_json = result
        self.db.commit()
        self.db.refresh(chatbot_session)

        return {
            "response": response,
            "session_id": session_id,
        }

    def get_or_create_session(self, session_id: str) -> ChatbotSession:
        chatbot_session = (
            self.db.query(ChatbotSession)
            .filter(ChatbotSession.session_id == session_id)
            .first()
        )

        if chatbot_session is not None:
            return chatbot_session

        state = create_initial_state(user_id=f"{session_id}")

        chatbot_session = ChatbotSession(
            session_id=session_id,
            user_id=None,
            state_json=state,
        )

        self.db.add(chatbot_session)
        self.db.commit()
        self.db.refresh(chatbot_session)

        return chatbot_session
