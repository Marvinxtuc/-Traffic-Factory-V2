from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar

from domain.models.base import DomainRecord, new_id, utc_now
from domain.rules.statuses import ImageAssetStatus


@dataclass(slots=True, kw_only=True)
class ImageAsset(DomainRecord):
    """Visual asset generated from a content variant.

    Primary key: id
    Foreign keys: content_variant_id -> content_variants.id
    Status field: ImageAssetStatus
    Created when: a content variant enters the image lab
    Used by: publish checks and retrospective review
    Relation: one content variant may own many image assets
    """

    TABLE_NAME: ClassVar[str] = "image_assets"

    content_variant_id: str
    asset_type: str
    storage_path: str
    id: str = field(default_factory=lambda: new_id("img"))
    template_id: str | None = None
    prompt_snapshot: str | None = None
    width: int | None = None
    height: int | None = None
    status: ImageAssetStatus = ImageAssetStatus.DRAFT
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
