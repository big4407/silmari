from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI

from backend.core.config import settings
from backend.chatbot.graph import build_chatbot_graph
from backend.chatbot.utils import create_initial_state
from backend.db.models import ChatbotSession

class ChatbotService:
    def __init__(self, db: Session):
        self.db = db
        self.graph = build_chatbot_graph()
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=settings.openai_api_key,)

    def chat(self, session_id: str, message: str):
        chatbot_session = self.get_or_create_session(session_id)

        state = chatbot_session.state_json

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
        if result.get("search_inserted"):
            chatbot_session.state_json = create_initial_state(user_id=f"{session_id}")
        else:
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
