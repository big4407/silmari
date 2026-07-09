from sqlalchemy.orm import Session

from backend.db.models import ChatbotSession


class ChatbotRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_session_id(self, session_id: str) -> ChatbotSession | None:
        return (
            self.db.query(ChatbotSession)
            .filter(ChatbotSession.session_id == session_id)
            .first()
        )

    def create(self, session_id: str, user_id: str, state: dict) -> ChatbotSession:
        chatbot_session = ChatbotSession(
            session_id=session_id,
            user_id=user_id,
            state_json=state,
        )
        self.db.add(chatbot_session)
        self.db.commit()
        self.db.refresh(chatbot_session)
        return chatbot_session

    def save_state(
        self, chatbot_session: ChatbotSession, state: dict, user_id: str
    ) -> ChatbotSession:
        chatbot_session.state_json = state
        chatbot_session.user_id = user_id
        self.db.commit()
        self.db.refresh(chatbot_session)
        return chatbot_session
