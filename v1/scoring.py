from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


@dataclass(frozen=True)
class ScoreInput:
    source_type: str
    title: str
    summary: str
    content_raw: str
    published_at_iso: str | None
    collected_at_iso: str
    tags: list[str]


@dataclass(frozen=True)
class ScoreOutput:
    quality_score: float
    freshness_score: float
    business_score: float


class ScoreProvider(Protocol):
    def score(self, payload: ScoreInput) -> ScoreOutput:
        ...


def _clamp_score(value: float, *, default: float) -> float:
    if isinstance(value, float) and math.isnan(value):
        return default
    return max(0.0, min(1.0, round(float(value), 3)))


class DefaultRuleScoreProvider:
    """Round 2 default scoring provider (replaceable)."""

    def score(self, payload: ScoreInput) -> ScoreOutput:
        quality = min(1.0, (len(payload.summary) / 300.0) + (len(payload.content_raw) / 3000.0))

        if payload.published_at_iso:
            try:
                published_at = datetime.fromisoformat(payload.published_at_iso)
                now = datetime.now(timezone.utc)
                age_days = max((now - published_at).total_seconds() / 86400.0, 0.0)
                freshness = max(0.0, 1.0 - (age_days / 30.0))
            except ValueError:
                freshness = 0.5
        else:
            freshness = 0.5

        # V1 default: fixed baseline, reserved for future business model strategy.
        business = 0.5

        return ScoreOutput(
            quality_score=_clamp_score(quality, default=0.0),
            freshness_score=_clamp_score(freshness, default=0.5),
            business_score=_clamp_score(business, default=0.5),
        )


def score_signal(payload: ScoreInput, provider: ScoreProvider | None = None) -> ScoreOutput:
    active_provider = provider or DefaultRuleScoreProvider()
    raw = active_provider.score(payload)

    return ScoreOutput(
        quality_score=_clamp_score(raw.quality_score, default=0.0),
        freshness_score=_clamp_score(raw.freshness_score, default=0.5),
        business_score=_clamp_score(raw.business_score, default=0.5),
    )
