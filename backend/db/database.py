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


# ──────────────────────────────────────────────────────────────
# Chroma (벡터 DB) 연결 — 인물 임베딩 저장소
# MariaDB 의 engine/SessionLocal 과 같은 "연결" 계층. 실제 작업은 crud.py.
# ──────────────────────────────────────────────────────────────
import chromadb

CHROMA_COLLECTION_NAME = "silmari_person_embeddings"

_chroma_client = None
_chroma_collection = None


def get_chromadb():
    """Chroma 인물 임베딩 컬렉션을 반환(lazy singleton).

    코사인 공간 명시(기본 L2 아님). 영속 경로는 settings.chroma_dir,
    미설정 시 data/chroma 로 폴백.
    """
    global _chroma_client, _chroma_collection
    if _chroma_collection is None:
        persist_dir = getattr(settings, "chroma_dir", None) or "data/chroma"
        _chroma_client = chromadb.PersistentClient(path=str(persist_dir))
        _chroma_collection = _chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _chroma_collection