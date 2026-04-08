from __future__ import annotations

from adapters.providers.base import CapabilityCallResult


class PlaceholderPublishCheckEnhancerProvider:
    provider_name = "placeholder.publish-check"
    capabilities = ("publish_check_enhancement",)

    def invoke(self, capability_name: str, payload: dict[str, object]) -> CapabilityCallResult:
        response = {
            "enhancement_note": "一期占位：发布检查增强能力未接入外部 provider，仅保留统一接入结构。",
            "check_id": payload.get("check_id"),
            "result": payload.get("result"),
        }
        return CapabilityCallResult(
            capability_name=capability_name,
            provider_name=self.provider_name,
            payload=response,
            output_ref=f"{self.provider_name}:{capability_name}",
        )
