"""
SQLAlchemy 엔진·세션·Base 선언.

[연결] core/config.py 의 database_url (MySQL 또는 DATABASE_URL_OVERRIDE)
[get_db] FastAPI Depends용 제너레이터 — 요청마다 SessionLocal 생성·종료
"""
# db/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.core.config import settings


class Base(DeclarativeBase):
    pass


_url = settings.database_url
_connect_args = {"check_same_thread": False} if _url.startswith("sqlite") else {}

engine = create_engine(
    _url,
    pool_pre_ping=True,
    echo=False,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()