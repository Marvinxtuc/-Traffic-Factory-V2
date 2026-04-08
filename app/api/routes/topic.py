from __future__ import annotations

from pathlib import Path

from app.api.base import (
    JsonDict,
    RouteRegistration,
    model_to_dict,
    models_to_items,
    require_fields,
    success_response,
    with_service_guard,
)
from domain.models.topic import Topic
from services.errors import EntityNotFoundError
from services.topic_service import TopicService


class TopicRouteSet:
    def __init__(self, *, db_path: str | Path | None = None):
        self.service = TopicService(db_path=db_path)
        self.repository = self.service.repository

    def routes(self) -> tuple[RouteRegistration, ...]:
        return (
            RouteRegistration("GET", "/topics", self.list_topics, "查询选题列表"),
            RouteRegistration("GET", "/topics/{topic_id}", self.get_topic, "查询选题详情"),
            RouteRegistration("POST", "/topics", self.create_topic, "创建选题"),
            RouteRegistration(
                "POST",
                "/signals/{signal_id}/advance-to-topic",
                self.advance_signal_to_topic,
                "信号推进为选题",
            ),
        )

    def list_topics(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            where = {}
            signal_id = query.get("signal_id")
            if signal_id:
                where["signal_id"] = signal_id
            items = self.repository.list(Topic, where=where or None, order_by="created_at DESC")
            return success_response(
                {
                    "items": models_to_items(items),
                    "total": len(items),
                },
                message="选题列表查询成功。",
            )

        return with_service_guard(action)

    def get_topic(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            topic_id = params["topic_id"]
            topic = self.repository.get(Topic, topic_id)
            if topic is None:
                raise EntityNotFoundError(f"Topic not found: {topic_id}")
            return success_response(model_to_dict(topic), message="选题详情查询成功。")

        return with_service_guard(action)

    def create_topic(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            require_fields(payload, "signal_id", "title")
            created = self.service.create_from_signal(
                signal_id=payload["signal_id"],
                title=payload["title"],
                angle=payload.get("angle"),
                priority=payload.get("priority", "P1"),
                target_platform=payload.get("target_platform"),
                decision_note=payload.get("decision_note"),
            )
            return success_response(model_to_dict(created), message="选题创建成功。")

        return with_service_guard(action)

    def advance_signal_to_topic(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            require_fields(payload, "title")
            created = self.service.create_from_signal(
                signal_id=params["signal_id"],
                title=payload["title"],
                angle=payload.get("angle"),
                priority=payload.get("priority", "P1"),
                target_platform=payload.get("target_platform"),
                decision_note=payload.get("decision_note"),
            )
            return success_response(model_to_dict(created), message="主链推进成功：信号 -> 选题。")

        return with_service_guard(action)
