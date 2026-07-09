from sqlalchemy.orm import Session

from backend.db.models import ChatbotSession


class ChatbotRepository:
    def __init__(self, db: Session):
        self.db = db

    # 경현씨 repository 작업
