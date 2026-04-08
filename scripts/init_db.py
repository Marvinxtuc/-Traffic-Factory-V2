from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from domain.rules.statuses import (
    CheckItemSeverity,
    ContentVariantStatus,
    ExecutionRecordStatus,
    ImageAssetStatus,
    PublishCheckRecordStatus,
    PublishCheckResult,
    RetroRecordStatus,
    SignalStatus,
    TopicStatus,
)


def enum_values(enum_type: type) -> str:
    return ", ".join(f"'{item.value}'" for item in enum_type)


SCHEMA = [
    f"""
    CREATE TABLE IF NOT EXISTS signals (
        id TEXT PRIMARY KEY,
        source_type TEXT NOT NULL,
        source_ref TEXT,
        title TEXT NOT NULL,
        summary TEXT,
        source_url TEXT,
        captured_at TEXT NOT NULL,
        tags_json TEXT NOT NULL DEFAULT '[]',
        normalized_hash TEXT,
        status TEXT NOT NULL CHECK (status IN ({enum_values(SignalStatus)})),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS topics (
        id TEXT PRIMARY KEY,
        signal_id TEXT NOT NULL,
        title TEXT NOT NULL,
        angle TEXT,
        priority TEXT NOT NULL,
        target_platform TEXT,
        decision_note TEXT,
        status TEXT NOT NULL CHECK (status IN ({enum_values(TopicStatus)})),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (signal_id) REFERENCES signals(id)
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS content_variants (
        id TEXT PRIMARY KEY,
        topic_id TEXT NOT NULL,
        variant_type TEXT NOT NULL,
        platform TEXT NOT NULL,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        style_profile TEXT,
        revision_no INTEGER NOT NULL DEFAULT 1,
        status TEXT NOT NULL CHECK (status IN ({enum_values(ContentVariantStatus)})),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (topic_id) REFERENCES topics(id)
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS image_assets (
        id TEXT PRIMARY KEY,
        content_variant_id TEXT NOT NULL,
        asset_type TEXT NOT NULL,
        template_id TEXT,
        storage_path TEXT NOT NULL,
        prompt_snapshot TEXT,
        width INTEGER,
        height INTEGER,
        status TEXT NOT NULL CHECK (status IN ({enum_values(ImageAssetStatus)})),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (content_variant_id) REFERENCES content_variants(id)
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS publish_checks (
        id TEXT PRIMARY KEY,
        content_variant_id TEXT NOT NULL,
        image_asset_id TEXT,
        topic_id TEXT,
        platform TEXT,
        result TEXT NOT NULL CHECK (result IN ({enum_values(PublishCheckResult)})),
        problem_summary TEXT,
        suggested_action TEXT,
        risk_note TEXT,
        check_version INTEGER NOT NULL DEFAULT 1 CHECK (check_version >= 1),
        record_status TEXT NOT NULL CHECK (record_status IN ({enum_values(PublishCheckRecordStatus)})),
        block_count INTEGER NOT NULL DEFAULT 0,
        warn_count INTEGER NOT NULL DEFAULT 0,
        pass_count INTEGER NOT NULL DEFAULT 0,
        checked_at TEXT NOT NULL,
        invalidated_at TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (content_variant_id) REFERENCES content_variants(id),
        FOREIGN KEY (image_asset_id) REFERENCES image_assets(id),
        FOREIGN KEY (topic_id) REFERENCES topics(id)
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS publish_check_items (
        id TEXT PRIMARY KEY,
        publish_check_id TEXT NOT NULL,
        rule_code TEXT NOT NULL,
        rule_category TEXT NOT NULL,
        severity TEXT NOT NULL CHECK (severity IN ({enum_values(CheckItemSeverity)})),
        result TEXT NOT NULL CHECK (result IN ({enum_values(PublishCheckResult)})),
        message TEXT,
        suggestion TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (publish_check_id) REFERENCES publish_checks(id)
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS retro_records (
        id TEXT PRIMARY KEY,
        publish_check_id TEXT NOT NULL,
        signal_id TEXT,
        topic_id TEXT,
        content_variant_id TEXT,
        image_asset_id TEXT,
        publish_result_summary TEXT,
        metrics_json TEXT NOT NULL DEFAULT '{{}}',
        insight TEXT,
        next_action TEXT,
        status TEXT NOT NULL CHECK (status IN ({enum_values(RetroRecordStatus)})),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (publish_check_id) REFERENCES publish_checks(id),
        FOREIGN KEY (signal_id) REFERENCES signals(id),
        FOREIGN KEY (topic_id) REFERENCES topics(id),
        FOREIGN KEY (content_variant_id) REFERENCES content_variants(id),
        FOREIGN KEY (image_asset_id) REFERENCES image_assets(id)
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS execution_records (
        id TEXT PRIMARY KEY,
        capability_name TEXT NOT NULL,
        provider_name TEXT NOT NULL,
        input_ref TEXT NOT NULL,
        output_ref TEXT,
        status TEXT NOT NULL CHECK (status IN ({enum_values(ExecutionRecordStatus)})),
        started_at TEXT NOT NULL,
        ended_at TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_topics_signal_id ON topics(signal_id)",
    "CREATE INDEX IF NOT EXISTS idx_content_variants_topic_id ON content_variants(topic_id)",
    "CREATE INDEX IF NOT EXISTS idx_image_assets_content_variant_id ON image_assets(content_variant_id)",
    "CREATE INDEX IF NOT EXISTS idx_publish_checks_content_variant_id ON publish_checks(content_variant_id)",
    "CREATE INDEX IF NOT EXISTS idx_publish_checks_image_asset_id ON publish_checks(image_asset_id)",
    "CREATE INDEX IF NOT EXISTS idx_publish_checks_topic_id ON publish_checks(topic_id)",
    "CREATE INDEX IF NOT EXISTS idx_publish_check_items_publish_check_id ON publish_check_items(publish_check_id)",
    "CREATE INDEX IF NOT EXISTS idx_retro_records_publish_check_id ON retro_records(publish_check_id)",
]


def initialize_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        for statement in SCHEMA:
            connection.execute(statement)
        connection.commit()
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the phase-one SQLite schema.")
    parser.add_argument(
        "--db-path",
        default="data/runtime/traffic_factory.sqlite3",
        help="Path to the SQLite database file.",
    )
    args = parser.parse_args()
    db_path = Path(args.db_path)
    initialize_database(db_path)
    print(f"Initialized SQLite schema at {db_path}")


if __name__ == "__main__":
    main()
