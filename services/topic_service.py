from __future__ import annotations

from domain.models.base import utc_now
from domain.models.signal import Signal
from domain.models.topic import Topic
from domain.rules.statuses import SignalStatus, TopicStatus
from services.base import BaseService
from services.errors import ConstraintViolationError, EntityNotFoundError


class TopicService(BaseService):
    """Topic creation skeleton.

    Input: signal_id plus topic metadata
    Preconditions: the signal must exist and must not be discarded
    Output: persisted Topic
    State change: Signal -> CONVERTED, Topic -> READY_FOR_CONTENT
    Failure: missing or discarded signal
    Next step: the created topic may enter content generation
    """

    def create_from_signal(
        self,
        *,
        signal_id: str,
        title: str,
        angle: str | None = None,
        priority: str = "P1",
        target_platform: str | None = None,
        decision_note: str | None = None,
    ) -> Topic:
        signal = self.repository.get(Signal, signal_id)
        if signal is None:
            raise EntityNotFoundError(f"Signal not found: {signal_id}")
        if signal.status == SignalStatus.DISCARDED:
            raise ConstraintViolationError("Discarded signals cannot create topics.")

        topic = Topic(
            signal_id=signal.id,
            title=title,
            angle=angle,
            priority=priority,
            target_platform=target_platform,
            decision_note=decision_note,
            status=TopicStatus.READY_FOR_CONTENT,
        )
        created = self.repository.add(topic)

        signal.status = SignalStatus.CONVERTED
        signal.updated_at = utc_now()
        self.repository.update(signal)
        return created
