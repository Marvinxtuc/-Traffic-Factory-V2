from __future__ import annotations

from domain.models.base import utc_now
from domain.models.signal import Signal
from domain.rules.statuses import SignalStatus
from services.base import BaseService


class DiscoveryService(BaseService):
    """Discovery service skeleton.

    Inputs: signal source metadata
    Preconditions: none
    Output: persisted Signal
    State change: NEW -> READY_FOR_TOPIC
    Failure: none at this stage beyond storage failure
    Next step: a READY_FOR_TOPIC signal may be converted into a topic
    """

    def create_signal(
        self,
        *,
        source_type: str,
        title: str,
        source_ref: str | None = None,
        summary: str | None = None,
        source_url: str | None = None,
        tags: list[str] | None = None,
        normalized_hash: str | None = None,
    ) -> Signal:
        signal = Signal(
            source_type=source_type,
            title=title,
            source_ref=source_ref,
            summary=summary,
            source_url=source_url,
            tags_json=tags or [],
            normalized_hash=normalized_hash,
            status=SignalStatus.READY_FOR_TOPIC,
        )
        signal.updated_at = utc_now()
        return self.repository.add(signal)
