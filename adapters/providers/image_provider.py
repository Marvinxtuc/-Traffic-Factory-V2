from __future__ import annotations

from adapters.providers.base import CapabilityCallResult


class PlaceholderImageProvider:
    provider_name = "placeholder.image"
    capabilities = ("image_generation",)

    def invoke(self, capability_name: str, payload: dict[str, object]) -> CapabilityCallResult:
        response = {
            "asset_type": payload.get("asset_type", "cover"),
            "storage_path": payload.get("storage_path", "tmp/generated/placeholder-image.png"),
            "template_id": payload.get("template_id"),
            "prompt_snapshot": payload.get("prompt_snapshot", "placeholder image capability"),
            "width": payload.get("width"),
            "height": payload.get("height"),
        }
        return CapabilityCallResult(
            capability_name=capability_name,
            provider_name=self.provider_name,
            payload=response,
            output_ref=f"{self.provider_name}:{capability_name}",
        )
