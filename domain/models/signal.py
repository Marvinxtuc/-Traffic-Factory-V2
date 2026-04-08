from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar

from domain.models.base import DomainRecord, new_id, utc_now
from domain.rules.statuses import SignalStatus


@dataclass(slots=True, kw_only=True)
class Signal(DomainRecord):
    """Discovery root object for phase one.

    Primary key: id
    Foreign keys: none
    Status field: SignalStatus
    Created when: discovery captures a source item or an operator enters a clue
    Used by: topic planning and retrospective trace-back
    Relation: one signal may fan out into many topics
    """

    TABLE_NAME: ClassVar[str] = "signals"

    source_type: str
    title: str
    id: str = field(default_factory=lambda: new_id("sig"))
    source_ref: str | None = None
    summary: str | None = None
    source_url: str | None = None
    captured_at: datetime = field(default_factory=utc_now)
    tags_json: list[str] = field(default_factory=list)
    normalized_hash: str | None = None
    status: SignalStatus = SignalStatus.NEW
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
