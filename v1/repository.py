from __future__ import annotations

import json
import sqlite3
from typing import Any

from v1.contracts import (
    ContentJobStatus,
    SignalStatus,
    TopicStatus,
    ensure_content_job_transition,
    ensure_signal_transition,
    ensure_topic_transition,
)
from v1.db import utc_now_iso


def upsert_source(
    conn: sqlite3.Connection,
    *,
    source_type: str,
    source_name: str,
    source_url: str | None,
) -> int:
    now = utc_now_iso()
    normalized_url = source_url or ""

    existing = conn.execute(
        """
        SELECT id
        FROM sources
        WHERE source_type = ?
          AND source_name = ?
          AND COALESCE(source_url, '') = ?
        LIMIT 1
        """,
        (source_type, source_name, normalized_url),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE sources SET updated_at = ? WHERE id = ?",
            (now, int(existing["id"])),
        )
        return int(existing["id"])

    cursor = conn.execute(
        """
        INSERT INTO sources (
            source_type,
            source_name,
            source_url,
            is_active,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, 1, ?, ?)
        """,
        (source_type, source_name, source_url, now, now),
    )
    return int(cursor.lastrowid)


def save_signal(conn: sqlite3.Connection, normalized_signal: dict[str, Any]) -> tuple[int, bool]:
    tags_json = json.dumps(normalized_signal.get("tags", []), ensure_ascii=False)
    try:
        cursor = conn.execute(
            """
            INSERT INTO trend_signals (
                source_id,
                source_type,
                source_name,
                external_id,
                title,
                summary,
                content_raw,
                canonical_url,
                author,
                published_at,
                collected_at,
                lang,
                tags_json,
                quality_score,
                freshness_score,
                business_score,
                dedup_key,
                status,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_signal["source_id"],
                normalized_signal["source_type"],
                normalized_signal["source_name"],
                normalized_signal.get("external_id"),
                normalized_signal["title"],
                normalized_signal.get("summary"),
                normalized_signal.get("content_raw"),
                normalized_signal.get("canonical_url"),
                normalized_signal.get("author"),
                normalized_signal.get("published_at"),
                normalized_signal["collected_at"],
                normalized_signal.get("lang"),
                tags_json,
                normalized_signal["quality_score"],
                normalized_signal["freshness_score"],
                normalized_signal["business_score"],
                normalized_signal["dedup_key"],
                SignalStatus(normalized_signal.get("status", SignalStatus.NEW.value)).value,
                normalized_signal["created_at"],
                normalized_signal["updated_at"],
            ),
        )
    except sqlite3.IntegrityError:
        row = conn.execute(
            "SELECT id FROM trend_signals WHERE dedup_key = ?",
            (normalized_signal["dedup_key"],),
        ).fetchone()
        return int(row["id"]), False

    return int(cursor.lastrowid), True


def _row_to_signal(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    payload["tags"] = json.loads(payload.pop("tags_json", "[]") or "[]")
    return payload


def _row_to_content_job(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    payload["input_payload"] = json.loads(payload.pop("input_payload_json", "{}") or "{}")
    output_payload_json = payload.pop("output_payload_json", None)
    payload["output_payload"] = json.loads(output_payload_json or "{}")
    return payload


def _row_to_content_version(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    payload["meta"] = json.loads(payload.pop("meta_json", "{}") or "{}")
    return payload


def list_signals(
    conn: sqlite3.Connection,
    *,
    source_type: str | None,
    status: str | None,
    order: str,
    limit: int,
) -> list[dict[str, Any]]:
    where_parts = ["1=1"]
    params: list[Any] = []

    if source_type:
        where_parts.append("source_type = ?")
        params.append(source_type)
    if status:
        where_parts.append("status = ?")
        params.append(status)

    order_sql = "ASC" if order.lower() == "asc" else "DESC"
    params.append(limit)

    rows = conn.execute(
        f"""
        SELECT *
        FROM trend_signals
        WHERE {' AND '.join(where_parts)}
        ORDER BY collected_at {order_sql}, id {order_sql}
        LIMIT ?
        """,
        params,
    ).fetchall()

    return [_row_to_signal(row) for row in rows]


def get_signal(conn: sqlite3.Connection, signal_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM trend_signals WHERE id = ?", (signal_id,)).fetchone()
    if not row:
        return None
    return _row_to_signal(row)


def update_signal_status(
    conn: sqlite3.Connection,
    *,
    signal_id: int,
    target_status: SignalStatus,
) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM trend_signals WHERE id = ?", (signal_id,)).fetchone()
    if not row:
        raise ValueError(f"Signal not found: {signal_id}")

    current_status = SignalStatus(row["status"])
    ensure_signal_transition(current_status, target_status)

    now = utc_now_iso()
    conn.execute(
        "UPDATE trend_signals SET status = ?, updated_at = ? WHERE id = ?",
        (target_status.value, now, signal_id),
    )
    updated = conn.execute("SELECT * FROM trend_signals WHERE id = ?", (signal_id,)).fetchone()
    if not updated:
        raise RuntimeError("Failed to reload signal after update")
    return _row_to_signal(updated)


def create_topic_from_signal(
    conn: sqlite3.Connection,
    *,
    signal_id: int,
    topic_title: str,
    angle: str | None,
    target_platform: str | None,
    commercial_value: float,
) -> tuple[int, bool]:
    now = utc_now_iso()
    signal_row = conn.execute(
        "SELECT id, status FROM trend_signals WHERE id = ?",
        (signal_id,),
    ).fetchone()
    if not signal_row:
        raise ValueError(f"Signal not found: {signal_id}")

    signal_status = SignalStatus(signal_row["status"])

    existing = conn.execute(
        "SELECT id FROM topic_pool WHERE signal_id = ?",
        (signal_id,),
    ).fetchone()
    if existing:
        if signal_status != SignalStatus.CONVERTED:
            ensure_signal_transition(signal_status, SignalStatus.CONVERTED)
            conn.execute(
                "UPDATE trend_signals SET status = ?, updated_at = ? WHERE id = ?",
                (SignalStatus.CONVERTED.value, now, signal_id),
            )
        return int(existing["id"]), False

    ensure_signal_transition(signal_status, SignalStatus.CONVERTED)
    cursor = conn.execute(
        """
        INSERT INTO topic_pool (
            signal_id,
            topic_title,
            angle,
            target_platform,
            commercial_value,
            status,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            signal_id,
            topic_title,
            angle,
            target_platform,
            commercial_value,
            TopicStatus.PENDING.value,
            now,
            now,
        ),
    )
    conn.execute(
        "UPDATE trend_signals SET status = ?, updated_at = ? WHERE id = ?",
        (SignalStatus.CONVERTED.value, now, signal_id),
    )
    return int(cursor.lastrowid), True


def get_topic(conn: sqlite3.Connection, topic_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM topic_pool WHERE id = ?", (topic_id,)).fetchone()
    if not row:
        return None
    return dict(row)


def update_topic_status(
    conn: sqlite3.Connection,
    *,
    topic_id: int,
    target_status: TopicStatus,
) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM topic_pool WHERE id = ?", (topic_id,)).fetchone()
    if not row:
        raise ValueError(f"Topic not found: {topic_id}")

    current_status = TopicStatus(row["status"])
    ensure_topic_transition(current_status, target_status)

    now = utc_now_iso()
    conn.execute(
        "UPDATE topic_pool SET status = ?, updated_at = ? WHERE id = ?",
        (target_status.value, now, topic_id),
    )
    updated = conn.execute("SELECT * FROM topic_pool WHERE id = ?", (topic_id,)).fetchone()
    if not updated:
        raise RuntimeError("Failed to reload topic after update")
    return dict(updated)


def list_topics(conn: sqlite3.Connection, *, limit: int = 100) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            t.*,
            s.title AS signal_title,
            s.source_name AS signal_source_name,
            s.collected_at AS signal_collected_at
        FROM topic_pool t
        JOIN trend_signals s ON s.id = t.signal_id
        ORDER BY t.created_at DESC, t.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def create_content_version(
    conn: sqlite3.Connection,
    *,
    topic_id: int,
    content_type: str,
    content_text: str,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = utc_now_iso()
    cursor = conn.execute(
        """
        INSERT INTO content_versions (
            topic_id,
            content_type,
            content_text,
            meta_json,
            created_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            topic_id,
            content_type,
            content_text,
            json.dumps(meta or {}, ensure_ascii=False),
            now,
        ),
    )
    row = conn.execute("SELECT * FROM content_versions WHERE id = ?", (int(cursor.lastrowid),)).fetchone()
    if not row:
        raise RuntimeError("Failed to fetch content version after insert")
    return _row_to_content_version(row)


def list_content_versions(
    conn: sqlite3.Connection,
    *,
    topic_id: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    params: list[Any] = []
    where_sql = ""
    if topic_id is not None:
        where_sql = "WHERE topic_id = ?"
        params.append(topic_id)
    params.append(limit)

    rows = conn.execute(
        f"""
        SELECT *
        FROM content_versions
        {where_sql}
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [_row_to_content_version(row) for row in rows]


def get_content_version(conn: sqlite3.Connection, version_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM content_versions WHERE id = ?", (version_id,)).fetchone()
    if not row:
        return None
    return _row_to_content_version(row)


def create_content_job(
    conn: sqlite3.Connection,
    *,
    topic_id: int,
    content_type: str,
    input_payload: dict[str, Any],
    output_payload: dict[str, Any] | None,
    status: ContentJobStatus,
) -> dict[str, Any]:
    now = utc_now_iso()
    cursor = conn.execute(
        """
        INSERT INTO content_jobs (
            topic_id,
            content_type,
            input_payload_json,
            output_payload_json,
            status,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            topic_id,
            content_type,
            json.dumps(input_payload, ensure_ascii=False),
            json.dumps(output_payload, ensure_ascii=False) if output_payload is not None else None,
            status.value,
            now,
            now,
        ),
    )
    row = conn.execute("SELECT * FROM content_jobs WHERE id = ?", (int(cursor.lastrowid),)).fetchone()
    if not row:
        raise RuntimeError("Failed to fetch content job after insert")
    return _row_to_content_job(row)


def update_content_job_status(
    conn: sqlite3.Connection,
    *,
    job_id: int,
    target_status: ContentJobStatus,
    output_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = conn.execute(
        "SELECT * FROM content_jobs WHERE id = ?",
        (job_id,),
    ).fetchone()
    if not current:
        raise ValueError(f"Content job not found: {job_id}")

    current_status = ContentJobStatus(current["status"])
    ensure_content_job_transition(current_status, target_status)

    now = utc_now_iso()
    conn.execute(
        """
        UPDATE content_jobs
        SET status = ?,
            output_payload_json = COALESCE(?, output_payload_json),
            updated_at = ?
        WHERE id = ?
        """,
        (
            target_status.value,
            json.dumps(output_payload, ensure_ascii=False) if output_payload is not None else None,
            now,
            job_id,
        ),
    )

    updated = conn.execute("SELECT * FROM content_jobs WHERE id = ?", (job_id,)).fetchone()
    if not updated:
        raise RuntimeError("Failed to reload content job after update")
    return _row_to_content_job(updated)
