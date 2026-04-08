from adapters.providers.base import CapabilityCallResult, CapabilityProvider
from adapters.providers.content_provider import PlaceholderContentProvider
from adapters.providers.image_provider import PlaceholderImageProvider
from adapters.providers.publish_check_provider import PlaceholderPublishCheckEnhancerProvider

__all__ = [
    "CapabilityCallResult",
    "CapabilityProvider",
    "PlaceholderContentProvider",
    "PlaceholderImageProvider",
    "PlaceholderPublishCheckEnhancerProvider",
]


def default_providers() -> list[CapabilityProvider]:
    return [
        PlaceholderContentProvider(),
        PlaceholderImageProvider(),
        PlaceholderPublishCheckEnhancerProvider(),
    ]
