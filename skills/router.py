from __future__ import annotations

from adapters.providers.base import CapabilityProvider


class ProviderRouter:
    def __init__(self, providers: list[CapabilityProvider] | None = None) -> None:
        self._providers: list[CapabilityProvider] = list(providers or [])

    def register_provider(self, provider: CapabilityProvider) -> None:
        self._providers.append(provider)

    def resolve(self, capability_name: str) -> list[CapabilityProvider]:
        return [provider for provider in self._providers if capability_name in provider.capabilities]

    def list_providers(self) -> list[str]:
        return [provider.provider_name for provider in self._providers]
