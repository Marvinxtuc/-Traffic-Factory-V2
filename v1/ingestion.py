from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from bs4 import BeautifulSoup

from v1.dedup import build_dedup_key
from v1.db import utc_now_iso
from v1.scoring import ScoreProvider, ScoreInput, score_signal

STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "will",
    "into",
    "about",
}


def clean_text(raw: str | None) -> str:
    if not raw:
        return ""
    text_input = str(raw).strip()
    if text_input.startswith(("http://", "https://")) and "<" not in text_input:
        return re.sub(r"\s+", " ", text_input).strip()
    text = BeautifulSoup(text_input, "html.parser").get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()


def parse_datetime_to_iso(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        pass

    if parsed is None:
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def extract_tags(title: str, raw_tags: list[str] | None = None) -> list[str]:
    if raw_tags:
        normalized = [clean_text(tag).lower() for tag in raw_tags if clean_text(tag)]
        return sorted(set(normalized))[:10]

    words = re.findall(r"[a-zA-Z0-9_]{3,}", title.lower())
    tags = [word for word in words if word not in STOP_WORDS]
    return sorted(set(tags))[:10]


def normalize_signal(
    *,
    source_type: str,
    source_name: str,
    source_id: int,
    title: str,
    summary: str | None,
    content_raw: str | None,
    canonical_url: str | None,
    author: str | None,
    published_at: str | None,
    external_id: str | None,
    lang: str | None,
    tags: list[str] | None,
    status: str = "new",
    score_provider: ScoreProvider | None = None,
) -> dict[str, Any]:
    collected_at = utc_now_iso()

    clean_title = clean_text(title)
    clean_summary = clean_text(summary)
    clean_content = clean_text(content_raw)
    canonical = clean_text(canonical_url)
    clean_author = clean_text(author)
    published_at_iso = parse_datetime_to_iso(published_at)
    extracted_tags = extract_tags(clean_title, tags)

    score = score_signal(
        ScoreInput(
            source_type=source_type,
            title=clean_title,
            summary=clean_summary,
            content_raw=clean_content,
            published_at_iso=published_at_iso,
            collected_at_iso=collected_at,
            tags=extracted_tags,
        ),
        provider=score_provider,
    )

    dedup_key = build_dedup_key(
        source_type=source_type,
        source_name=source_name,
        canonical_url=canonical,
        title=clean_title,
        published_at_iso=published_at_iso,
        external_id=external_id,
    )

    now = utc_now_iso()
    return {
        "source_id": source_id,
        "source_type": source_type,
        "source_name": source_name,
        "external_id": external_id,
        "title": clean_title,
        "summary": clean_summary,
        "content_raw": clean_content,
        "canonical_url": canonical,
        "author": clean_author,
        "published_at": published_at_iso,
        "collected_at": collected_at,
        "lang": lang or "unknown",
        "tags": extracted_tags,
        "quality_score": score.quality_score,
        "freshness_score": score.freshness_score,
        "business_score": score.business_score,
        "dedup_key": dedup_key,
        "status": status,
        "created_at": now,
        "updated_at": now,
    }
