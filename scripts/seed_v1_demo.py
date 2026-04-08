from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from v1.contracts import ContentJobStatus, SignalStatus, SourceType
from v1.db import DEFAULT_DB_PATH, connect_db, init_db
from v1.ingestion import normalize_signal
from v1.repository import (
    create_content_job,
    create_topic_from_signal,
    get_topic,
    save_signal,
    upsert_source,
)


def seed(db_path: Path) -> None:
    init_db(db_path)
    with connect_db(db_path) as conn:
        source_id = upsert_source(
            conn,
            source_type=SourceType.MANUAL.value,
            source_name="seed_manual",
            source_url=None,
        )

        signal_payloads = [
            {
                "title": "AI coding workflows keep accelerating in 2026",
                "summary": "Teams report faster iteration speed with coding copilots.",
                "content_raw": "Developers combine linting, review gates, and automation for stable output.",
                "canonical_url": "https://example.com/ai-coding-2026",
                "external_id": "seed-1",
            },
            {
                "title": "Newsletter conversion rises when hooks are data-backed",
                "summary": "Signal-driven headline tests improve open and click rates.",
                "content_raw": "Operational teams use a signal pool to prioritize topics with commercial potential.",
                "canonical_url": "https://example.com/newsletter-conversion",
                "external_id": "seed-2",
            },
        ]

        signal_ids: list[int] = []
        for payload in signal_payloads:
            normalized = normalize_signal(
                source_type=SourceType.MANUAL.value,
                source_name="seed_manual",
                source_id=source_id,
                title=payload["title"],
                summary=payload["summary"],
                content_raw=payload["content_raw"],
                canonical_url=payload["canonical_url"],
                author="seed-script",
                published_at=None,
                external_id=payload["external_id"],
                lang="en",
                tags=None,
                status=SignalStatus.NEW.value,
            )
            signal_id, _ = save_signal(conn, normalized)
            signal_ids.append(signal_id)

        topic_id, _ = create_topic_from_signal(
            conn,
            signal_id=signal_ids[0],
            topic_title="How to build stable AI coding workflows",
            angle="Process and risk controls",
            target_platform="newsletter",
            commercial_value=0.7,
        )

        topic = get_topic(conn, topic_id)
        if topic:
            create_content_job(
                conn,
                topic_id=topic_id,
                content_type="article",
                input_payload={"topic_id": topic_id, "seed": True},
                output_payload={
                    "mode": "mock",
                    "headline": topic["topic_title"],
                    "draft": "[MOCK] Seed content output.",
                },
                status=ContentJobStatus.COMPLETED,
            )

        conn.commit()

    print(f"Seed completed for: {db_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Traffic Factory V1 demo data.")
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database path",
    )
    args = parser.parse_args()
    seed(Path(args.db_path))


if __name__ == "__main__":
    main()
