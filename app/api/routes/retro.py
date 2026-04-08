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
from domain.models.retro_record import RetroRecord
from services.errors import EntityNotFoundError
from services.retro_service import RetroService


class RetroRouteSet:
    def __init__(self, *, db_path: str | Path | None = None):
        self.service = RetroService(db_path=db_path)
        self.repository = self.service.repository

    def routes(self) -> tuple[RouteRegistration, ...]:
        return (
            RouteRegistration("GET", "/retros", self.list_retros, "查询复盘记录列表"),
            RouteRegistration("GET", "/retros/{retro_id}", self.get_retro, "查询复盘记录详情"),
            RouteRegistration("POST", "/retros", self.create_retro, "创建复盘记录"),
            RouteRegistration(
                "POST",
                "/checks/{check_id}/advance-to-retro",
                self.advance_check_to_retro,
                "发布检查推进为复盘记录",
            ),
        )

    def list_retros(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            where = {}
            publish_check_id = query.get("publish_check_id")
            if publish_check_id:
                where["publish_check_id"] = publish_check_id
            items = self.repository.list(RetroRecord, where=where or None, order_by="created_at DESC")
            return success_response(
                {
                    "items": models_to_items(items),
                    "total": len(items),
                },
                message="复盘记录列表查询成功。",
            )

        return with_service_guard(action)

    def get_retro(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            retro_id = params["retro_id"]
            retro = self.repository.get(RetroRecord, retro_id)
            if retro is None:
                raise EntityNotFoundError(f"RetroRecord not found: {retro_id}")
            return success_response(model_to_dict(retro), message="复盘记录详情查询成功。")

        return with_service_guard(action)

    def create_retro(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            require_fields(payload, "publish_check_id")
            metrics_json = payload.get("metrics_json")
            if metrics_json is not None and not isinstance(metrics_json, dict):
                raise ValueError("Field metrics_json must be an object when provided.")

            created = self.service.create_from_check(
                publish_check_id=payload["publish_check_id"],
                signal_id=payload.get("signal_id"),
                topic_id=payload.get("topic_id"),
                content_variant_id=payload.get("content_variant_id"),
                image_asset_id=payload.get("image_asset_id"),
                publish_result_summary=payload.get("publish_result_summary"),
                metrics_json=metrics_json,
                insight=payload.get("insight"),
                next_action=payload.get("next_action"),
            )
            return success_response(model_to_dict(created), message="复盘记录创建成功。")

        return with_service_guard(action)

    def advance_check_to_retro(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            metrics_json = payload.get("metrics_json")
            if metrics_json is not None and not isinstance(metrics_json, dict):
                raise ValueError("Field metrics_json must be an object when provided.")

            created = self.service.create_from_check(
                publish_check_id=params["check_id"],
                signal_id=payload.get("signal_id"),
                topic_id=payload.get("topic_id"),
                content_variant_id=payload.get("content_variant_id"),
                image_asset_id=payload.get("image_asset_id"),
                publish_result_summary=payload.get("publish_result_summary"),
                metrics_json=metrics_json,
                insight=payload.get("insight"),
                next_action=payload.get("next_action"),
            )
            return success_response(model_to_dict(created), message="主链推进成功：发布检查 -> 复盘记录。")

        return with_service_guard(action)
