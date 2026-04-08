from __future__ import annotations

from domain.models.base import utc_now
from domain.models.content_variant import ContentVariant
from domain.models.image_asset import ImageAsset
from domain.rules.statuses import ImageAssetStatus
from services.base import BaseService
from services.errors import EntityNotFoundError


class ImageService(BaseService):
    """Image generation skeleton.

    Input: content_variant_id plus image metadata
    Preconditions: the content variant must exist
    Output: persisted ImageAsset
    State change: ImageAsset -> READY_FOR_CHECK
    Failure: missing content variant
    Next step: the created image asset may enter the quality gate
    """

    def create_asset(
        self,
        *,
        content_variant_id: str,
        asset_type: str,
        storage_path: str,
        template_id: str | None = None,
        prompt_snapshot: str | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> ImageAsset:
        variant = self.repository.get(ContentVariant, content_variant_id)
        if variant is None:
            raise EntityNotFoundError(f"ContentVariant not found: {content_variant_id}")

        asset = ImageAsset(
            content_variant_id=variant.id,
            asset_type=asset_type,
            storage_path=storage_path,
            template_id=template_id,
            prompt_snapshot=prompt_snapshot,
            width=width,
            height=height,
            status=ImageAssetStatus.READY_FOR_CHECK,
        )
        return self.repository.add(asset)

    def mark_modified(
        self,
        *,
        image_asset_id: str,
        storage_path: str | None = None,
        prompt_snapshot: str | None = None,
        template_id: str | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> tuple[ImageAsset, int]:
        image = self.repository.get(ImageAsset, image_asset_id)
        if image is None:
            raise EntityNotFoundError(f"ImageAsset not found: {image_asset_id}")

        if storage_path is not None:
            image.storage_path = storage_path
        if prompt_snapshot is not None:
            image.prompt_snapshot = prompt_snapshot
        if template_id is not None:
            image.template_id = template_id
        if width is not None:
            image.width = width
        if height is not None:
            image.height = height

        image.updated_at = utc_now()
        self.repository.update(image)

        from services.check_service import PublishCheckService

        invalidated = PublishCheckService(db_path=self.repository.db_path).invalidate_for_image_asset_change(
            image_asset_id
        )
        refreshed = self.repository.get(ImageAsset, image_asset_id)
        if refreshed is None:
            raise EntityNotFoundError(f"ImageAsset not found: {image_asset_id}")
        return refreshed, invalidated
