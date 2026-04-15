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
from domain.models.signal import Signal
from services.errors import EntityNotFoundError
from services.discovery_service import DiscoveryService


class SignalRouteSet:
    def __init__(self, *, db_path: str | Path | None = None):
        self.service = DiscoveryService(db_path=db_path)
        self.repository = self.service.repository

    def routes(self) -> tuple[RouteRegistration, ...]:
        return (
            RouteRegistration("GET", "/signals", self.list_signals, "查询信号列表"),
            RouteRegistration("GET", "/signals/{signal_id}", self.get_signal, "查询信号详情"),
            RouteRegistration("POST", "/signals", self.create_signal, "创建信号"),
        )

    def list_signals(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            where = {}
            source_type = query.get("source_type")
            if source_type:
                where["source_type"] = source_type
            items = self.repository.list(Signal, where=where or None, order_by="created_at DESC")
            source_name = str(query.get("source_name") or "").strip().lower()
            if source_name:
                items = [
                    item for item in items
                    if source_name in str(item.source_ref or "").lower()
                    or source_name in str(item.source_url or "").lower()
                ]
            return success_response(
                {
                    "items": models_to_items(items),
                    "total": len(items),
                },
                message="信号列表查询成功。",
            )

        return with_service_guard(action)

    def get_signal(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            signal_id = params["signal_id"]
            signal = self.repository.get(Signal, signal_id)
            if signal is None:
                raise EntityNotFoundError(f"Signal not found: {signal_id}")
            return success_response(model_to_dict(signal), message="信号详情查询成功。")

        return with_service_guard(action)

    def create_signal(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            require_fields(payload, "source_type", "title")
            tags = payload.get("tags")
            if tags is not None and not isinstance(tags, list):
                raise ValueError("Field tags must be a list when provided.")

            created = self.service.create_signal(
                source_type=payload["source_type"],
                title=payload["title"],
                source_ref=payload.get("source_ref"),
                summary=payload.get("summary"),
                source_url=payload.get("source_url"),
                tags=tags,
                normalized_hash=payload.get("normalized_hash"),
            )
            return success_response(model_to_dict(created), message="信号创建成功。")

        return with_service_guard(action)
