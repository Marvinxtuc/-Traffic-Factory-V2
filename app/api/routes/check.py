from __future__ import annotations

from pathlib import Path

from app.api.base import (
    JsonDict,
    RouteRegistration,
    as_bool,
    model_to_dict,
    models_to_items,
    require_fields,
    success_response,
    with_service_guard,
)
from domain.models.publish_check import PublishCheck
from domain.models.publish_check_item import PublishCheckItem
from services.errors import EntityNotFoundError
from services.check_service import PublishCheckService


class PublishCheckRouteSet:
    def __init__(self, *, db_path: str | Path | None = None):
        self.service = PublishCheckService(db_path=db_path)
        self.repository = self.service.repository

    def routes(self) -> tuple[RouteRegistration, ...]:
        return (
            RouteRegistration("GET", "/checks", self.list_checks, "查询发布检查列表"),
            RouteRegistration("GET", "/checks/{check_id}", self.get_check, "查询发布检查详情"),
            RouteRegistration("POST", "/checks/submit", self.submit_check, "提交发布检查"),
            RouteRegistration(
                "POST",
                "/contents/{content_id}/submit-check",
                self.submit_check_for_content,
                "内容版本提交发布检查",
            ),
        )

    def list_checks(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            where = {}
            for field in ("content_variant_id", "image_asset_id", "record_status", "result"):
                value = query.get(field)
                if value:
                    where[field] = value
            items = self.repository.list(PublishCheck, where=where or None, order_by="checked_at DESC")
            return success_response(
                {
                    "items": models_to_items(items),
                    "total": len(items),
                },
                message="发布检查列表查询成功。",
            )

        return with_service_guard(action)

    def get_check(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            check_id = params["check_id"]
            check = self.repository.get(PublishCheck, check_id)
            if check is None:
                raise EntityNotFoundError(f"PublishCheck not found: {check_id}")
            items = self.repository.list(PublishCheckItem, where={"publish_check_id": check_id}, order_by="created_at ASC")
            return success_response(
                {
                    "check": model_to_dict(check),
                    "items": models_to_items(items),
                },
                message="发布检查详情查询成功。",
            )

        return with_service_guard(action)

    def submit_check(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            require_fields(payload, "content_variant_id")
            created, items = self.service.create_check(
                content_variant_id=payload["content_variant_id"],
                image_asset_id=payload.get("image_asset_id"),
                declares_image=as_bool(payload.get("declares_image"), default=False),
                topic_id=payload.get("topic_id"),
                platform=payload.get("platform"),
            )
            return success_response(
                {
                    "check": model_to_dict(created),
                    "items": models_to_items(items),
                },
                message="发布检查提交成功。",
            )

        return with_service_guard(action)

    def submit_check_for_content(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            created, items = self.service.create_check(
                content_variant_id=params["content_id"],
                image_asset_id=payload.get("image_asset_id"),
                declares_image=as_bool(payload.get("declares_image"), default=False),
                topic_id=payload.get("topic_id"),
                platform=payload.get("platform"),
            )
            return success_response(
                {
                    "check": model_to_dict(created),
                    "items": models_to_items(items),
                },
                message="主链推进成功：内容包 -> 发布检查。",
            )

        return with_service_guard(action)
