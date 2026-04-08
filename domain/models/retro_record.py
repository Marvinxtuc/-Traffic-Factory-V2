from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar

from domain.models.base import DomainRecord, new_id, utc_now
from domain.rules.statuses import RetroRecordStatus


@dataclass(slots=True, kw_only=True)
class RetroRecord(DomainRecord):
    """Retrospective record created after a valid publish check.

    Primary key: id
    Foreign keys: publish_check_id -> publish_checks.id
                  signal_id -> signals.id
                  topic_id -> topics.id
                  content_variant_id -> content_variants.id
                  image_asset_id -> image_assets.id
    Status field: RetroRecordStatus
    Created when: an operator records post-publish outcomes
    Used by: strategy review, topic selection, content iteration
    Relation: one publish check may produce one retrospective record in phase one
    """

    TABLE_NAME: ClassVar[str] = "retro_records"

    publish_check_id: str
    id: str = field(default_factory=lambda: new_id("ret"))
    signal_id: str | None = None
    topic_id: str | None = None
    content_variant_id: str | None = None
    image_asset_id: str | None = None
    publish_result_summary: str | None = None
    metrics_json: dict[str, float | int | str] = field(default_factory=dict)
    insight: str | None = None
    next_action: str | None = None
    status: RetroRecordStatus = RetroRecordStatus.DRAFT
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
