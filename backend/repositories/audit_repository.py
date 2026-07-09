from sqlalchemy.orm import Session

from backend.db.models import AdminHistory


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, entry: AdminHistory) -> None:
        """감사 로그 1건을 추가한다.

        커밋은 호출 측(서비스) 트랜잭션에 맡긴다 — add + flush 만 한다.
        """
        self.db.add(entry)
        self.db.flush()
