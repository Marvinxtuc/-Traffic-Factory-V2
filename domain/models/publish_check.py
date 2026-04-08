from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar

from domain.models.base import DomainRecord, new_id, utc_now
from domain.rules.statuses import PublishCheckRecordStatus, PublishCheckResult


@dataclass(slots=True, kw_only=True)
class PublishCheck(DomainRecord):
    """Append-only quality gate record for a content package.

    Primary key: id
    Foreign keys: content_variant_id -> content_variants.id
                  image_asset_id -> image_assets.id (required when an image exists)
                  topic_id -> topics.id (redundant query anchor)
    Status/result fields: PublishCheckResult + PublishCheckRecordStatus
    Created when: a content variant is submitted to the quality gate
    Used by: gate decisions, retrospective creation, audit views
    Relation: one content variant may produce many publish checks over time
    """

    TABLE_NAME: ClassVar[str] = "publish_checks"

    content_variant_id: str
    result: PublishCheckResult
    id: str = field(default_factory=lambda: new_id("chk"))
    image_asset_id: str | None = None
    topic_id: str | None = None
    platform: str | None = None
    problem_summary: str | None = None
    suggested_action: str | None = None
    risk_note: str | None = None
    check_version: int = 1
    record_status: PublishCheckRecordStatus = PublishCheckRecordStatus.ACTIVE
    block_count: int = 0
    warn_count: int = 0
    pass_count: int = 0
    checked_at: datetime = field(default_factory=utc_now)
    invalidated_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
