class ServiceError(Exception):
    """Base service-layer error."""


class EntityNotFoundError(ServiceError):
    """Raised when an upstream object is missing."""


class ConstraintViolationError(ServiceError):
    """Raised when a service action violates chain constraints."""


class GateBlockedError(ServiceError):
    """Raised when a blocked publish check prevents the next step."""
