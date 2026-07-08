"""
llm 사용량 체크를 위한 repository단
"""

from sqlalchemy.orm import Session

from backend.db.models import LlmCall


class LLmCallRepository:
    def __init__(self, db: Session):
        self.db = db
