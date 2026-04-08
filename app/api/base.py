from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from domain.models.base import DomainRecord
from services.errors import ConstraintViolationError, EntityNotFoundError, GateBlockedError, ServiceError


JsonDict = dict[str, Any]
RouteHandler = Callable[[JsonDict, JsonDict, JsonDict], JsonDict]


@dataclass(frozen=True, slots=True)
class RouteRegistration:
    method: str
    path: str
    handler: RouteHandler
    summary: str


def success_response(data: Any = None, *, message: str = "OK") -> JsonDict:
    return {
        "ok": True,
        "message": message,
        "data": data,
    }


def error_response(code: str, message: str, *, details: Any | None = None) -> JsonDict:
    payload: JsonDict = {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details is not None:
        payload["error"]["details"] = details
    return payload


def model_to_dict(entity: DomainRecord) -> JsonDict:
    return entity.to_record()


def models_to_items(entities: list[DomainRecord]) -> list[JsonDict]:
    return [model_to_dict(entity) for entity in entities]


def require_fields(payload: JsonDict, *fields: str) -> None:
    missing = [field for field in fields if payload.get(field) in (None, "")]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")


def as_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def with_service_guard(action: Callable[[], JsonDict]) -> JsonDict:
    try:
        return action()
    except ValueError as exc:
        return error_response("BAD_REQUEST", str(exc))
    except EntityNotFoundError as exc:
        return error_response("ENTITY_NOT_FOUND", str(exc))
    except GateBlockedError as exc:
        return error_response("GATE_BLOCKED", str(exc))
    except ConstraintViolationError as exc:
        return error_response("CONSTRAINT_VIOLATION", str(exc))
    except ServiceError as exc:
        return error_response("SERVICE_ERROR", str(exc))
    except Exception as exc:  # pragma: no cover - defensive guard
        return error_response("INTERNAL_ERROR", "Unhandled API error.", details=str(exc))
