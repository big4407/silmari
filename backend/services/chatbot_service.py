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


class ChatbotService:
    def __init__(self, db: Session):
        self.db = db
        self.graph = build_chatbot_graph()
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=settings.openai_api_key,
        )

    USAGE_FILE = Path("chatbot_usage.json")

    def save_usage(self, session_id: str, cb):
        usage = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "prompt_tokens": cb.prompt_tokens,
            "completion_tokens": cb.completion_tokens,
            "total_tokens": cb.total_tokens,
            "total_cost_usd": cb.total_cost,
            "successful_requests": cb.successful_requests,
        }

        if self.USAGE_FILE.exists():
            with open(self.USAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []

        data.append(usage)

        with open(self.USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def chat(self, session_id: str, message: str):
        chatbot_session = self.get_or_create_session(session_id)

        state = chatbot_session.state_json

        state["messages"].append(
            {
                "role": "user",
                "content": message,
            }
        )

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

        response = result["response"]

        chatbot_session.state_json = result
        self.db.commit()
        self.db.refresh(chatbot_session)
        
        self.save_usage(session_id, cb)

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
