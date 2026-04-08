from __future__ import annotations

import hashlib
import re


def normalize_title_for_dedup(title: str) -> str:
    lowered = title.strip().lower()
    # Minimal normalization only; no semantic fuzzy match in V1.
    normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", lowered)
    return re.sub(r"\s+", " ", normalized).strip()


def build_dedup_locator(*, canonical_url: str, external_id: str | None, normalized_title: str) -> str:
    if canonical_url:
        return f"url:{canonical_url}"
    if external_id:
        return f"external:{external_id.strip()}"
    return f"title:{normalized_title}"


def build_dedup_key(
    *,
    source_type: str,
    source_name: str,
    canonical_url: str,
    title: str,
    published_at_iso: str | None,
    external_id: str | None,
) -> str:
    normalized_title = normalize_title_for_dedup(title)
    locator = build_dedup_locator(
        canonical_url=canonical_url.strip(),
        external_id=external_id,
        normalized_title=normalized_title,
    )
    published_day = (published_at_iso or "")[:10]

    seed = "|".join(
        [
            source_type,
            source_name,
            locator,
            normalized_title,
            published_day,
        ]
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()
