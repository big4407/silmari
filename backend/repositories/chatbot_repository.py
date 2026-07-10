from sqlalchemy.orm import Session

from backend.db.models import ChatbotSession


class ChatbotRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        session_id: str,
        user_id: str,
        state_json: dict,
    ):
        chatbot_session = ChatbotSession(
            session_id=session_id,
            user_id=user_id,
            state_json=state_json,
        )
        self.db.add(chatbot_session)
        self.db.flush()
        self.db.refresh(chatbot_session)
        return chatbot_session

    def get_by_session_id_and_user_id(
        self,
        *,
        session_id: str,
        user_id: str,
    ) -> ChatbotSession | None:
        return (
            self.db.query(ChatbotSession)
            .filter(
                ChatbotSession.session_id == session_id,
                ChatbotSession.user_id == user_id,
            )
            .first()
        )

    def delete(self, chatbot_session: ChatbotSession) -> None:
        self.db.delete(chatbot_session)
        self.db.flush()
