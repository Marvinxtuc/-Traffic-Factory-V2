from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class SignalStatus(StrEnum):
    NEW = "NEW"
    READY_FOR_TOPIC = "READY_FOR_TOPIC"
    CONVERTED = "CONVERTED"
    DISCARDED = "DISCARDED"


class TopicStatus(StrEnum):
    NEW = "NEW"
    READY_FOR_CONTENT = "READY_FOR_CONTENT"
    IN_CONTENT = "IN_CONTENT"
    CLOSED = "CLOSED"


class ContentVariantStatus(StrEnum):
    DRAFT = "DRAFT"
    READY_FOR_IMAGE = "READY_FOR_IMAGE"
    IN_CHECK = "IN_CHECK"
    NEEDS_REVISION = "NEEDS_REVISION"


class ImageAssetStatus(StrEnum):
    DRAFT = "DRAFT"
    READY_FOR_CHECK = "READY_FOR_CHECK"
    NEEDS_REVISION = "NEEDS_REVISION"
    SUPERSEDED = "SUPERSEDED"


class PublishCheckResult(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    BLOCK = "BLOCK"


class PublishCheckRecordStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INVALIDATED = "INVALIDATED"


class CheckItemSeverity(StrEnum):
    INFO = "INFO"
    WARN = "WARN"
    BLOCK = "BLOCK"


class RetroRecordStatus(StrEnum):
    DRAFT = "DRAFT"
    CLOSED = "CLOSED"


class ExecutionRecordStatus(StrEnum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
