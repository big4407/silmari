from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI

from backend.core.config import settings
from backend.chatbot.graph import build_chatbot_graph
from backend.chatbot.utils import create_initial_state


class ChatbotService:
    def __init__(self, db: Session):
        self.db = db
        self.graph = build_chatbot_graph()
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=settings.openai_api_key,)

    def chat(self, user_id: str, message: str, prev_state: dict | None = None):
        state = prev_state or create_initial_state(user_id)

        state["user_id"] = user_id
        state["messages"].append({"role": "user", "content": message})

        result = self.graph.invoke(
            state,
            config={
                "configurable": {
                    "db": self.db,
                    "llm": self.llm,
                }
            },
        )

        return result
