from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)

# 기존 ORM Base와 분리된 통계 전용 MetaData입니다.
stats_metadata = MetaData()

stats_case_event = Table(
    "stats_case_event",
    stats_metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("case_key", String(100), nullable=False, index=True),
    Column("event_type", String(30), nullable=False, index=True),
    Column("occurred_at", DateTime(timezone=True), nullable=False, index=True),
    Column("reported_at_snapshot", DateTime(timezone=True), nullable=True),
    Column("region_snapshot", String(255), nullable=True, index=True),
    Column("actor_id", Integer, nullable=True),
    Column("actor_name", String(100), nullable=True),
    Column("actor_role", String(50), nullable=True),
    Column("recorded_by_id", Integer, nullable=True),
    Column("recorded_by_name", String(100), nullable=False),
    Column("location_text", String(255), nullable=True),
    Column("latitude", Float, nullable=True),
    Column("longitude", Float, nullable=True),
    Column("source_search_id", Integer, nullable=True, index=True),
    Column("source_analysis_id", Integer, nullable=True),
    Column("source_analysis_detail_id", Integer, nullable=True),
    Column("note", Text, nullable=True),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    ),
)

stats_export_log = Table(
    "stats_export_log",
    stats_metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("stat_type", String(30), nullable=False, index=True),
    Column("from_date", Date, nullable=False),
    Column("to_date", Date, nullable=False),
    Column("file_format", String(10), nullable=False, default="CSV"),
    Column("file_name", String(255), nullable=False),
    Column("row_count", Integer, nullable=False, default=0),
    Column("requested_by_id", Integer, nullable=True),
    Column("requested_by_name", String(100), nullable=False),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    ),
)
