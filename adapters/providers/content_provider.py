from __future__ import annotations

from adapters.providers.base import CapabilityCallResult


class PlaceholderContentProvider:
    provider_name = "placeholder.content"
    capabilities = ("content_generation",)

    def invoke(self, capability_name: str, payload: dict[str, object]) -> CapabilityCallResult:
        title = str(payload.get("seed_title") or "能力层生成标题")
        body = str(payload.get("seed_body") or "能力层生成正文占位")
        response = {
            "variant_type": payload.get("variant_type", "post"),
            "platform": payload.get("platform", "xiaohongshu"),
            "title": title,
            "body": body,
            "style_profile": payload.get("style_profile"),
        }
        return CapabilityCallResult(
            capability_name=capability_name,
            provider_name=self.provider_name,
            payload=response,
            output_ref=f"{self.provider_name}:{capability_name}",
        )
