from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI

from backend.core.config import settings
from backend.core.chatbot.graph import build_chatbot_graph
from backend.core.chatbot.utils import create_initial_state
from backend.db.models import ChatbotSession
from backend.repositories.chatbot_repository import ChatbotRepository


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

    def chat(self, session_id: str, message: str, user_id: str):
        chatbot_session = self.get_or_create_session(session_id, user_id)

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

        self.repository.save_state(chatbot_session, result, user_id)

        return {
            "response": response,
            "session_id": session_id,
        }

    def get_or_create_session(self, session_id: str, user_id: str) -> ChatbotSession:
        chatbot_session = self.repository.find_by_session_id(session_id)

        if chatbot_session is not None:
            return chatbot_session

        state = create_initial_state(user_id=user_id)

        return self.repository.create(session_id, user_id, state)
