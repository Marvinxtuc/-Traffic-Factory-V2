from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar

from domain.models.base import DomainRecord, new_id, utc_now
from domain.rules.statuses import TopicStatus


@dataclass(slots=True, kw_only=True)
class Topic(DomainRecord):
    """Production candidate derived from a signal.

    Primary key: id
    Foreign keys: signal_id -> signals.id
    Status field: TopicStatus
    Created when: a signal is accepted into the topic pool
    Used by: content generation, checks, retrospective review
    Relation: one topic may fan out into many content variants
    """

    TABLE_NAME: ClassVar[str] = "topics"

    signal_id: str
    title: str
    id: str = field(default_factory=lambda: new_id("top"))
    angle: str | None = None
    priority: str = "P1"
    target_platform: str | None = None
    decision_note: str | None = None
    status: TopicStatus = TopicStatus.NEW
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
