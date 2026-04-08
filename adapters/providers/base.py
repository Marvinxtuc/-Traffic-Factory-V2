from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class CapabilityCallResult:
    capability_name: str
    provider_name: str
    payload: dict[str, Any] = field(default_factory=dict)
    output_ref: str | None = None


class CapabilityProvider(Protocol):
    provider_name: str
    capabilities: tuple[str, ...]

    def invoke(self, capability_name: str, payload: dict[str, Any]) -> CapabilityCallResult:
        ...
