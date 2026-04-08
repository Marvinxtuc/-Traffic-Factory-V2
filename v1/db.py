from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from v1.contracts import ContentJobStatus, SignalStatus, SourceType, TopicStatus, sql_in_values

DEFAULT_DB_PATH = Path("data/runtime/traffic_factory_v1.sqlite3")

SCHEMA_SQL = f"""
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL CHECK(source_type IN ({sql_in_values(SourceType)})),
    source_name TEXT NOT NULL,
    source_url TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source_type, source_name, source_url)
);

CREATE TABLE IF NOT EXISTS trend_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER,
    source_type TEXT NOT NULL CHECK(source_type IN ({sql_in_values(SourceType)})),
    source_name TEXT NOT NULL,
    external_id TEXT,
    title TEXT NOT NULL,
    summary TEXT,
    content_raw TEXT,
    canonical_url TEXT,
    author TEXT,
    published_at TEXT,
    collected_at TEXT NOT NULL,
    lang TEXT,
    tags_json TEXT NOT NULL DEFAULT '[]',
    quality_score REAL NOT NULL DEFAULT 0 CHECK(quality_score >= 0 AND quality_score <= 1),
    freshness_score REAL NOT NULL DEFAULT 0 CHECK(freshness_score >= 0 AND freshness_score <= 1),
    business_score REAL NOT NULL DEFAULT 0 CHECK(business_score >= 0 AND business_score <= 1),
    dedup_key TEXT NOT NULL CHECK(LENGTH(TRIM(dedup_key)) > 0),
    status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ({sql_in_values(SignalStatus)})),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES sources(id),
    UNIQUE(dedup_key)
);

CREATE TABLE IF NOT EXISTS topic_pool (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER NOT NULL,
    topic_title TEXT NOT NULL,
    angle TEXT,
    target_platform TEXT,
    commercial_value REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ({sql_in_values(TopicStatus)})),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (signal_id) REFERENCES trend_signals(id),
    UNIQUE(signal_id)
);

CREATE TABLE IF NOT EXISTS content_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    content_type TEXT NOT NULL,
    input_payload_json TEXT NOT NULL,
    output_payload_json TEXT,
    status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ({sql_in_values(ContentJobStatus)})),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (topic_id) REFERENCES topic_pool(id)
);

CREATE TABLE IF NOT EXISTS content_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    content_type TEXT NOT NULL,
    content_text TEXT NOT NULL,
    meta_json TEXT NOT NULL DEFAULT '{{}}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (topic_id) REFERENCES topic_pool(id)
);

CREATE INDEX IF NOT EXISTS idx_trend_signals_collected_at
ON trend_signals(collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_trend_signals_source_type
ON trend_signals(source_type);

CREATE INDEX IF NOT EXISTS idx_trend_signals_status
ON trend_signals(status);

CREATE INDEX IF NOT EXISTS idx_topic_pool_created_at
ON topic_pool(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_content_versions_created_at
ON content_versions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_content_versions_topic_id
ON content_versions(topic_id, created_at DESC);
"""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect_db(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with connect_db(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
