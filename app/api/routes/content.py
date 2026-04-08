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
from domain.models.content_variant import ContentVariant
from services.errors import EntityNotFoundError
from services.content_service import ContentService


class ContentRouteSet:
    def __init__(self, *, db_path: str | Path | None = None):
        self.service = ContentService(db_path=db_path)
        self.repository = self.service.repository

    def routes(self) -> tuple[RouteRegistration, ...]:
        return (
            RouteRegistration("GET", "/contents", self.list_contents, "查询内容版本列表"),
            RouteRegistration("GET", "/contents/{content_id}", self.get_content, "查询内容版本详情"),
            RouteRegistration("POST", "/contents", self.create_content, "创建内容版本"),
            RouteRegistration("POST", "/contents/{content_id}/mark-modified", self.mark_content_modified, "内容版本标记修改并触发重检"),
            RouteRegistration(
                "POST",
                "/topics/{topic_id}/advance-to-content",
                self.advance_topic_to_content,
                "选题推进为内容版本",
            ),
        )

    def list_contents(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            where = {}
            topic_id = query.get("topic_id")
            if topic_id:
                where["topic_id"] = topic_id
            items = self.repository.list(ContentVariant, where=where or None, order_by="created_at DESC")
            return success_response(
                {
                    "items": models_to_items(items),
                    "total": len(items),
                },
                message="内容版本列表查询成功。",
            )

        return with_service_guard(action)

    def get_content(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            content_id = params["content_id"]
            content = self.repository.get(ContentVariant, content_id)
            if content is None:
                raise EntityNotFoundError(f"ContentVariant not found: {content_id}")
            return success_response(model_to_dict(content), message="内容版本详情查询成功。")

        return with_service_guard(action)

    def create_content(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            require_fields(payload, "topic_id", "variant_type", "platform", "title", "body")
            created = self.service.create_variant(
                topic_id=payload["topic_id"],
                variant_type=payload["variant_type"],
                platform=payload["platform"],
                title=payload["title"],
                body=payload["body"],
                style_profile=payload.get("style_profile"),
            )
            return success_response(model_to_dict(created), message="内容版本创建成功。")

        return with_service_guard(action)

    def advance_topic_to_content(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            require_fields(payload, "variant_type", "platform", "title", "body")
            created = self.service.create_variant(
                topic_id=params["topic_id"],
                variant_type=payload["variant_type"],
                platform=payload["platform"],
                title=payload["title"],
                body=payload["body"],
                style_profile=payload.get("style_profile"),
            )
            return success_response(model_to_dict(created), message="主链推进成功：选题 -> 内容版本。")

        return with_service_guard(action)

    def mark_content_modified(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            updated, invalidated = self.service.mark_modified(
                content_variant_id=params["content_id"],
                title=payload.get("title"),
                body=payload.get("body"),
                style_profile=payload.get("style_profile"),
            )
            return success_response(
                {
                    "content_variant": model_to_dict(updated),
                    "invalidated_checks": invalidated,
                    "requires_recheck": True,
                },
                message="内容版本已标记修改，旧检查记录已失效，请重新检查。",
            )

        return with_service_guard(action)
