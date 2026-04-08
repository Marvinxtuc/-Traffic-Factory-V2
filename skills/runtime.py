from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from adapters.providers.base import CapabilityCallResult
from services.execution_record_service import ExecutionRecordService
from skills.fallback import FallbackPolicy
from skills.registry import SkillRegistry
from skills.router import ProviderRouter


@dataclass(frozen=True, slots=True)
class CapabilityExecutionResult:
    capability_name: str
    provider_name: str
    payload: dict[str, Any]
    output_ref: str | None
    execution_record_id: str


class CapabilityRuntime:
    def __init__(
        self,
        *,
        registry: SkillRegistry,
        router: ProviderRouter,
        fallback_policy: FallbackPolicy,
        execution_records: ExecutionRecordService,
    ) -> None:
        self.registry = registry
        self.router = router
        self.fallback_policy = fallback_policy
        self.execution_records = execution_records

    def execute(self, *, capability_name: str, payload: dict[str, Any]) -> CapabilityExecutionResult:
        self.registry.require(capability_name)
        providers = self.router.resolve(capability_name)
        if not providers:
            raise ValueError(f"No providers for capability: {capability_name}")

        input_ref = json.dumps(payload, ensure_ascii=True, sort_keys=True)
        last_error: Exception | None = None
        for index, provider in enumerate(providers):
            record = self.execution_records.start(
                capability_name=capability_name,
                provider_name=provider.provider_name,
                input_ref=input_ref,
            )
            try:
                result = provider.invoke(capability_name, payload)
            except Exception as exc:
                last_error = exc
                self.execution_records.fail(record_id=record.id, output_ref=str(exc))
                decision = self.fallback_policy.decide(error=exc, remaining_providers=len(providers) - index - 1)
                if not decision.use_next_provider:
                    break
                continue

            self.execution_records.succeed(record_id=record.id, output_ref=result.output_ref)
            return CapabilityExecutionResult(
                capability_name=result.capability_name,
                provider_name=result.provider_name,
                payload=result.payload,
                output_ref=result.output_ref,
                execution_record_id=record.id,
            )

        if last_error is not None:
            raise RuntimeError(f"Capability execution failed: {capability_name}") from last_error
        raise RuntimeError(f"Capability execution failed: {capability_name}")
