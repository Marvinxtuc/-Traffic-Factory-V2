from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import types
from typing import Any, Mapping, get_args, get_origin, get_type_hints
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=True)
    return value


def _unwrap_optional(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin in (types.UnionType, getattr(__import__("typing"), "Union")):
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(args) == 1:
            return _unwrap_optional(args[0])
    return annotation


def _deserialize(raw: Any, annotation: Any) -> Any:
    target = _unwrap_optional(annotation)
    if raw is None:
        return None
    origin = get_origin(target)
    if isinstance(target, type) and issubclass(target, Enum):
        return target(raw)
    if target is datetime:
        return datetime.fromisoformat(raw)
    if origin in (list, dict):
        if isinstance(raw, str):
            return json.loads(raw)
    return raw


@dataclass(slots=True)
class DomainRecord:
    """Base helper used by phase-one domain models."""

    def to_record(self) -> dict[str, Any]:
        return {key: _serialize(value) for key, value in asdict(self).items()}

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "DomainRecord":
        hints = get_type_hints(cls)
        kwargs = {}
        for key, value in dict(record).items():
            if key in hints:
                kwargs[key] = _deserialize(value, hints[key])
        return cls(**kwargs)
