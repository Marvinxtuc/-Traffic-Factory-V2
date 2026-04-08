from __future__ import annotations

from enum import Enum


class SourceType(str, Enum):
    RSS = "rss"
    WEB = "web"
    MANUAL = "manual"


class SignalStatus(str, Enum):
    NEW = "new"
    REVIEWED = "reviewed"
    CONVERTED = "converted"
    ARCHIVED = "archived"


class TopicStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    DROPPED = "dropped"


class ContentJobStatus(str, Enum):
    QUEUED = "queued"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


SIGNAL_STATUS_TRANSITIONS: dict[SignalStatus, set[SignalStatus]] = {
    SignalStatus.NEW: {SignalStatus.REVIEWED, SignalStatus.CONVERTED, SignalStatus.ARCHIVED},
    SignalStatus.REVIEWED: {SignalStatus.CONVERTED, SignalStatus.ARCHIVED},
    SignalStatus.CONVERTED: {SignalStatus.ARCHIVED},
    SignalStatus.ARCHIVED: set(),
}

TOPIC_STATUS_TRANSITIONS: dict[TopicStatus, set[TopicStatus]] = {
    TopicStatus.PENDING: {TopicStatus.IN_PROGRESS, TopicStatus.DONE, TopicStatus.DROPPED},
    TopicStatus.IN_PROGRESS: {TopicStatus.DONE, TopicStatus.DROPPED},
    TopicStatus.DONE: set(),
    TopicStatus.DROPPED: set(),
}

CONTENT_JOB_STATUS_TRANSITIONS: dict[ContentJobStatus, set[ContentJobStatus]] = {
    ContentJobStatus.QUEUED: {ContentJobStatus.GENERATING, ContentJobStatus.FAILED},
    ContentJobStatus.GENERATING: {ContentJobStatus.COMPLETED, ContentJobStatus.FAILED},
    ContentJobStatus.COMPLETED: set(),
    ContentJobStatus.FAILED: set(),
}


def enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


def sql_in_values(enum_cls: type[Enum]) -> str:
    return ", ".join(f"'{value}'" for value in enum_values(enum_cls))


def ensure_signal_transition(current: SignalStatus, target: SignalStatus) -> None:
    if current == target:
        return
    allowed = SIGNAL_STATUS_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(f"Invalid signal status transition: {current.value} -> {target.value}")


def ensure_topic_transition(current: TopicStatus, target: TopicStatus) -> None:
    if current == target:
        return
    allowed = TOPIC_STATUS_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(f"Invalid topic status transition: {current.value} -> {target.value}")


def ensure_content_job_transition(current: ContentJobStatus, target: ContentJobStatus) -> None:
    if current == target:
        return
    allowed = CONTENT_JOB_STATUS_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(f"Invalid content job status transition: {current.value} -> {target.value}")
