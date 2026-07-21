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


def delete_video_embeddings(video_id: int) -> None:
    """video_id에 속한 모든 인물 임베딩을 Chroma에서 지운다.

    MySQL의 video 행을 지울 때(retention_service의 cctv_video 만료 삭제 등)
    반드시 같이 호출해야 한다 — 안 그러면 Chroma에는 그 video_id로 인덱싱된
    임베딩이 그대로 남는다. video.id는 AUTO_INCREMENT라 DB를 통째로
    리셋(TRUNCATE/재생성)하면 카운터가 처음부터 다시 시작되는데, 이때 예전에
    지워진 video_id가 완전히 다른 새 영상에 재할당되면: 검색이 그 남아있던
    옛 임베딩과 매칭 → analysis_detail.video_id(FK)는 지금 그 번호를 가진
    "다른" video 행을 정상적으로 가리켜서 에러 없이 조회됨 → 결과 화면에 그
    임베딩이 원래 뽑혔던 영상이 아니라 지금 그 번호를 가진 엉뚱한 영상이
    재생되는 문제로 이어진다(video_detail.video_timestamp가 실제 영상
    길이보다 길게 나오는 것도 같은 증상의 다른 얼굴일 수 있다 — 원래
    영상은 더 길었는데 지금 영상은 더 짧은 경우).

    video_service.py의 무거운 ML 스택(YOLO/FashionCLIP/torch)을 함께
    끌어오지 않도록 이 lazy get_chromadb()만 사용하는 가벼운 함수로
    따로 둔다(video_service의 lazy property와 같은 의도).
    """
    collection = get_chromadb()
    collection.delete(where={"video_id": video_id})