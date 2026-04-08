from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar

from domain.models.base import DomainRecord, new_id, utc_now
from domain.rules.statuses import ContentVariantStatus


@dataclass(slots=True, kw_only=True)
class ContentVariant(DomainRecord):
    """Content draft or rewrite generated from a topic.

    Primary key: id
    Foreign keys: topic_id -> topics.id
    Status field: ContentVariantStatus
    Created when: a topic enters the content lab
    Used by: image generation, publish checks, retrospective review
    Relation: one content variant may fan out into many image assets
    """

    TABLE_NAME: ClassVar[str] = "content_variants"

    topic_id: str
    variant_type: str
    platform: str
    title: str
    body: str
    id: str = field(default_factory=lambda: new_id("cnt"))
    style_profile: str | None = None
    revision_no: int = 1
    status: ContentVariantStatus = ContentVariantStatus.DRAFT
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
