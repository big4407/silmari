from sqlalchemy.orm import Session

from backend.models.message_model import Message


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_sn(self, sn: str) -> Message | None:
        return self.db.query(Message).filter(Message.sn == sn).first()

    def save(self, message: Message) -> Message:
        self.db.add(message)
        self.db.flush()
        return message
