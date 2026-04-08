from __future__ import annotations

from dataclasses import dataclass

from domain.models.publish_check import PublishCheck
from domain.rules.publish_check_rules import CheckRuleOutcome, aggregate_publish_check_result
from domain.rules.statuses import PublishCheckRecordStatus, PublishCheckResult
from services.errors import ConstraintViolationError, GateBlockedError


@dataclass(slots=True)
class GateDecision:
    result: PublishCheckResult
    allows_next_step: bool
    requires_risk_record: bool
    rework_target: str | None


class CheckGateWorkflow:
    """Strong-gate helper for service-level decisions."""

    @staticmethod
    def decide_from_outcomes(outcomes: list[CheckRuleOutcome]) -> GateDecision:
        result = aggregate_publish_check_result(outcomes)
        if result == PublishCheckResult.PASS:
            return GateDecision(result, True, False, None)
        if result == PublishCheckResult.WARN:
            return GateDecision(result, True, True, None)
        return GateDecision(result, False, False, "content_or_image")

    @staticmethod
    def decide(check: PublishCheck) -> GateDecision:
        if check.record_status != PublishCheckRecordStatus.ACTIVE:
            return GateDecision(
                result=check.result,
                allows_next_step=False,
                requires_risk_record=False,
                rework_target="content_or_image",
            )
        if check.result == PublishCheckResult.PASS:
            return GateDecision(check.result, True, False, None)
        if check.result == PublishCheckResult.WARN:
            return GateDecision(check.result, True, True, None)
        return GateDecision(check.result, False, False, "content_or_image")

    @classmethod
    def ensure_retro_allowed(cls, check: PublishCheck) -> None:
        decision = cls.decide(check)
        if check.record_status != PublishCheckRecordStatus.ACTIVE:
            raise ConstraintViolationError("Invalidated publish checks cannot advance.")
        if not decision.allows_next_step:
            raise GateBlockedError("Blocked publish checks must return to content or image.")
