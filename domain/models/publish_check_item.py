from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar

from domain.models.base import DomainRecord, new_id, utc_now
from domain.rules.statuses import CheckItemSeverity, PublishCheckResult


@dataclass(slots=True, kw_only=True)
class PublishCheckItem(DomainRecord):
    """Detailed inspection row attached to a publish check.

    Primary key: id
    Foreign keys: publish_check_id -> publish_checks.id
    Status/result fields: CheckItemSeverity + PublishCheckResult
    Created when: a publish check expands into rule-level findings
    Used by: quality-gate UI and audit trace-back
    Relation: one publish check owns many publish check items
    """

    TABLE_NAME: ClassVar[str] = "publish_check_items"

    publish_check_id: str
    rule_code: str
    rule_category: str
    severity: CheckItemSeverity
    result: PublishCheckResult
    id: str = field(default_factory=lambda: new_id("chi"))
    message: str | None = None
    suggestion: str | None = None
    created_at: datetime = field(default_factory=utc_now)
