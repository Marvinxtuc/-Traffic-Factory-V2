from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar

from domain.models.base import DomainRecord, new_id, utc_now
from domain.rules.statuses import ExecutionRecordStatus


@dataclass(slots=True, kw_only=True)
class ExecutionRecord(DomainRecord):
    """Optional execution trace reserved for the future capability layer.

    Primary key: id
    Foreign keys: none in phase one
    Status field: ExecutionRecordStatus
    Created when: a provider or skill execution is started
    Used by: future audit and fallback tracing
    Relation: support object only, does not participate in the main chain
    """

    TABLE_NAME: ClassVar[str] = "execution_records"

    capability_name: str
    provider_name: str
    input_ref: str
    id: str = field(default_factory=lambda: new_id("exe"))
    output_ref: str | None = None
    status: ExecutionRecordStatus = ExecutionRecordStatus.PENDING
    started_at: datetime = field(default_factory=utc_now)
    ended_at: datetime | None = None
