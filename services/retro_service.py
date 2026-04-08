from __future__ import annotations

from domain.models.publish_check import PublishCheck
from domain.models.retro_record import RetroRecord
from domain.rules.statuses import PublishCheckRecordStatus, PublishCheckResult, RetroRecordStatus
from services.base import BaseService
from services.errors import ConstraintViolationError, EntityNotFoundError, GateBlockedError


class RetroService(BaseService):
    """Retrospective creation skeleton.

    Input: publish_check_id plus retrospective fields
    Preconditions: the publish check must exist, stay ACTIVE and resolve to PASS/WARN
    Output: persisted RetroRecord
    State change: RetroRecord -> CLOSED
    Failure: missing check, blocked or invalidated check, duplicate retro record
    Next step: phase-one chain closes here
    """

    def create_from_check(
        self,
        *,
        publish_check_id: str,
        signal_id: str | None = None,
        topic_id: str | None = None,
        content_variant_id: str | None = None,
        image_asset_id: str | None = None,
        publish_result_summary: str | None = None,
        metrics_json: dict[str, int | float | str] | None = None,
        insight: str | None = None,
        next_action: str | None = None,
    ) -> RetroRecord:
        check = self.repository.get(PublishCheck, publish_check_id)
        if check is None:
            raise EntityNotFoundError(f"PublishCheck not found: {publish_check_id}")
        if check.record_status != PublishCheckRecordStatus.ACTIVE:
            raise ConstraintViolationError("RetroRecord requires an active PublishCheck.")
        if check.result == PublishCheckResult.BLOCK:
            raise GateBlockedError("BLOCK publish checks cannot create retrospective records.")

        existing = self.repository.list(RetroRecord, where={"publish_check_id": publish_check_id})
        if existing:
            raise ConstraintViolationError("Only one RetroRecord is allowed per PublishCheck in phase one.")

        retro = RetroRecord(
            publish_check_id=publish_check_id,
            signal_id=signal_id,
            topic_id=topic_id or check.topic_id,
            content_variant_id=content_variant_id or check.content_variant_id,
            image_asset_id=image_asset_id or check.image_asset_id,
            publish_result_summary=publish_result_summary,
            metrics_json=metrics_json or {},
            insight=insight,
            next_action=next_action,
            status=RetroRecordStatus.CLOSED,
        )
        return self.repository.add(retro)
