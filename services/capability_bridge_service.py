from __future__ import annotations

from pathlib import Path
from typing import Any

from adapters.providers import default_providers
from domain.models.publish_check import PublishCheck
from services.check_service import PublishCheckService
from services.content_service import ContentService
from services.execution_record_service import ExecutionRecordService
from services.image_service import ImageService
from services.errors import EntityNotFoundError
from skills.fallback import FallbackPolicy
from skills.registry import build_default_registry
from skills.router import ProviderRouter
from skills.runtime import CapabilityRuntime


class CapabilityBridgeService:
    """Minimal capability-layer bridge.

    This service keeps the current main-chain services untouched while providing
    a unified capability entry point with execution-record persistence.
    """

    def __init__(self, *, db_path: str | Path | None = None):
        self.execution_records = ExecutionRecordService(db_path=db_path)
        self.runtime = CapabilityRuntime(
            registry=build_default_registry(),
            router=ProviderRouter(default_providers()),
            fallback_policy=FallbackPolicy(),
            execution_records=self.execution_records,
        )
        self.content_service = ContentService(db_path=db_path)
        self.image_service = ImageService(db_path=db_path)
        self.publish_check_service = PublishCheckService(db_path=db_path)
        self.repository = self.content_service.repository

    def create_content_variant_with_capability(
        self,
        *,
        topic_id: str,
        platform: str,
        variant_type: str = "post",
        seed_title: str | None = None,
        seed_body: str | None = None,
        style_profile: str | None = None,
    ) -> dict[str, Any]:
        execution = self.runtime.execute(
            capability_name="content_generation",
            payload={
                "topic_id": topic_id,
                "platform": platform,
                "variant_type": variant_type,
                "seed_title": seed_title,
                "seed_body": seed_body,
                "style_profile": style_profile,
            },
        )
        created = self.content_service.create_variant(
            topic_id=topic_id,
            variant_type=str(execution.payload["variant_type"]),
            platform=str(execution.payload["platform"]),
            title=str(execution.payload["title"]),
            body=str(execution.payload["body"]),
            style_profile=(None if execution.payload.get("style_profile") is None else str(execution.payload["style_profile"])),
        )
        return {
            "content_variant": created,
            "execution": execution,
        }

    def create_image_asset_with_capability(
        self,
        *,
        content_variant_id: str,
        asset_type: str = "cover",
        storage_path: str | None = None,
        template_id: str | None = None,
        prompt_snapshot: str | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> dict[str, Any]:
        execution = self.runtime.execute(
            capability_name="image_generation",
            payload={
                "content_variant_id": content_variant_id,
                "asset_type": asset_type,
                "storage_path": storage_path,
                "template_id": template_id,
                "prompt_snapshot": prompt_snapshot,
                "width": width,
                "height": height,
            },
        )
        created = self.image_service.create_asset(
            content_variant_id=content_variant_id,
            asset_type=str(execution.payload["asset_type"]),
            storage_path=str(execution.payload["storage_path"]),
            template_id=(None if execution.payload.get("template_id") is None else str(execution.payload["template_id"])),
            prompt_snapshot=(
                None
                if execution.payload.get("prompt_snapshot") is None
                else str(execution.payload["prompt_snapshot"])
            ),
            width=execution.payload.get("width"),
            height=execution.payload.get("height"),
        )
        return {
            "image_asset": created,
            "execution": execution,
        }

    def run_publish_check_enhancement(self, *, check_id: str) -> dict[str, Any]:
        check = self.repository.get(PublishCheck, check_id)
        if check is None:
            raise EntityNotFoundError(f"PublishCheck not found: {check_id}")

        execution = self.runtime.execute(
            capability_name="publish_check_enhancement",
            payload={
                "check_id": check.id,
                "result": check.result.value,
                "topic_id": check.topic_id,
                "platform": check.platform,
            },
        )
        return {
            "publish_check": check,
            "execution": execution,
        }
