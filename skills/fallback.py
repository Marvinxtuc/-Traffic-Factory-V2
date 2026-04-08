from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FallbackDecision:
    use_next_provider: bool
    reason: str


class FallbackPolicy:
    """Minimal fallback policy for phase one capability skeleton."""

    def decide(self, *, error: Exception, remaining_providers: int) -> FallbackDecision:
        if remaining_providers > 0:
            return FallbackDecision(
                use_next_provider=True,
                reason=f"Current provider failed: {error}. Try next provider.",
            )
        return FallbackDecision(
            use_next_provider=False,
            reason=f"No more providers available after error: {error}",
        )
