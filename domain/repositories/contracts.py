from __future__ import annotations

from typing import Protocol, TypeVar


ModelT = TypeVar("ModelT")


class Repository(Protocol[ModelT]):
    """Minimal repository contract placeholder for future persistence work."""

    def add(self, entity: ModelT) -> None:
        ...

    def get(self, entity_id: str) -> ModelT | None:
        ...
