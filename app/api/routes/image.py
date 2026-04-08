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
from domain.models.image_asset import ImageAsset
from services.errors import EntityNotFoundError
from services.image_service import ImageService


class ImageRouteSet:
    def __init__(self, *, db_path: str | Path | None = None):
        self.service = ImageService(db_path=db_path)
        self.repository = self.service.repository

    def routes(self) -> tuple[RouteRegistration, ...]:
        return (
            RouteRegistration("GET", "/images", self.list_images, "查询图片资产列表"),
            RouteRegistration("GET", "/images/{image_id}", self.get_image, "查询图片资产详情"),
            RouteRegistration("POST", "/images", self.create_image, "创建图片资产"),
            RouteRegistration("POST", "/images/{image_id}/mark-modified", self.mark_image_modified, "图片资产标记修改并触发重检"),
            RouteRegistration(
                "POST",
                "/contents/{content_id}/advance-to-image",
                self.advance_content_to_image,
                "内容版本推进为图片资产",
            ),
        )

    def list_images(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            where = {}
            content_variant_id = query.get("content_variant_id")
            if content_variant_id:
                where["content_variant_id"] = content_variant_id
            items = self.repository.list(ImageAsset, where=where or None, order_by="created_at DESC")
            return success_response(
                {
                    "items": models_to_items(items),
                    "total": len(items),
                },
                message="图片资产列表查询成功。",
            )

        return with_service_guard(action)

    def get_image(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            image_id = params["image_id"]
            image = self.repository.get(ImageAsset, image_id)
            if image is None:
                raise EntityNotFoundError(f"ImageAsset not found: {image_id}")
            return success_response(model_to_dict(image), message="图片资产详情查询成功。")

        return with_service_guard(action)

    def create_image(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            require_fields(payload, "content_variant_id", "asset_type", "storage_path")
            width = payload.get("width")
            height = payload.get("height")
            if width is not None and not isinstance(width, int):
                raise ValueError("Field width must be integer when provided.")
            if height is not None and not isinstance(height, int):
                raise ValueError("Field height must be integer when provided.")

            created = self.service.create_asset(
                content_variant_id=payload["content_variant_id"],
                asset_type=payload["asset_type"],
                storage_path=payload["storage_path"],
                template_id=payload.get("template_id"),
                prompt_snapshot=payload.get("prompt_snapshot"),
                width=width,
                height=height,
            )
            return success_response(model_to_dict(created), message="图片资产创建成功。")

        return with_service_guard(action)

    def advance_content_to_image(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            require_fields(payload, "asset_type", "storage_path")
            width = payload.get("width")
            height = payload.get("height")
            if width is not None and not isinstance(width, int):
                raise ValueError("Field width must be integer when provided.")
            if height is not None and not isinstance(height, int):
                raise ValueError("Field height must be integer when provided.")

            created = self.service.create_asset(
                content_variant_id=params["content_id"],
                asset_type=payload["asset_type"],
                storage_path=payload["storage_path"],
                template_id=payload.get("template_id"),
                prompt_snapshot=payload.get("prompt_snapshot"),
                width=width,
                height=height,
            )
            return success_response(model_to_dict(created), message="主链推进成功：内容版本 -> 图片资产。")

        return with_service_guard(action)

    def mark_image_modified(self, payload: JsonDict, query: JsonDict, params: JsonDict) -> JsonDict:
        def action() -> JsonDict:
            width = payload.get("width")
            height = payload.get("height")
            if width is not None and not isinstance(width, int):
                raise ValueError("Field width must be integer when provided.")
            if height is not None and not isinstance(height, int):
                raise ValueError("Field height must be integer when provided.")

            updated, invalidated = self.service.mark_modified(
                image_asset_id=params["image_id"],
                storage_path=payload.get("storage_path"),
                prompt_snapshot=payload.get("prompt_snapshot"),
                template_id=payload.get("template_id"),
                width=width,
                height=height,
            )
            return success_response(
                {
                    "image_asset": model_to_dict(updated),
                    "invalidated_checks": invalidated,
                    "requires_recheck": True,
                },
                message="图片资产已标记修改，旧检查记录已失效，请重新检查。",
            )

        return with_service_guard(action)
