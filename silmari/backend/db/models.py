from sqlalchemy import Column, Integer, String, DateTime, Text, Float, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

from utils.config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class DetectionRecord(Base):
    __tablename__ = "detection_records"

    id = Column(Integer, primary_key=True, index=True)
    alert_text = Column(Text)
    video_filename = Column(String(255))
    result_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class SearchResult(Base):
    __tablename__ = "search_results"

    id = Column(Integer, primary_key=True, index=True)
    alert_text = Column(Text)
    person_name = Column(String(100), index=True)
    person_age = Column(Integer, nullable=True)
    region = Column(String(100), nullable=True)
    video_filename = Column(String(255))
    thumbnail_filename = Column(String(255))
    best_confidence = Column(Float)
    best_timestamp_sec = Column(Float)
    clips_json = Column(Text)
    sms_info_json = Column(Text)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
