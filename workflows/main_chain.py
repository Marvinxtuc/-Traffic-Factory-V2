from __future__ import annotations

from pathlib import Path

from domain.rules.statuses import PublishCheckResult
from services import (
    ContentService,
    DiscoveryService,
    ImageService,
    PublishCheckService,
    RetroService,
    TopicService,
)


class MainChainWorkflow:
    """Minimal phase-one chain orchestrator.

    This workflow does not add new business logic; it only wires the service
    skeletons together so the main object progression is explicit and reusable.
    """

    def __init__(self, *, db_path: str | Path | None = None):
        self.discovery_service = DiscoveryService(db_path=db_path)
        self.topic_service = TopicService(db_path=db_path)
        self.content_service = ContentService(db_path=db_path)
        self.image_service = ImageService(db_path=db_path)
        self.publish_check_service = PublishCheckService(db_path=db_path)
        self.retro_service = RetroService(db_path=db_path)

    def advance_signal_to_topic(self, **kwargs):
        return self.topic_service.create_from_signal(**kwargs)

    def advance_topic_to_content(self, **kwargs):
        return self.content_service.create_variant(**kwargs)

    def advance_content_to_image(self, **kwargs):
        return self.image_service.create_asset(**kwargs)

    def advance_to_publish_check(self, **kwargs):
        return self.publish_check_service.create_check(**kwargs)

    def advance_to_retro(self, **kwargs):
        return self.retro_service.create_from_check(**kwargs)

    def invalidate_checks_for_content_change(self, *, content_variant_id: str) -> int:
        return self.publish_check_service.invalidate_for_content_variant_change(content_variant_id)

    def invalidate_checks_for_image_change(self, *, image_asset_id: str) -> int:
        return self.publish_check_service.invalidate_for_image_asset_change(image_asset_id)

    def run_minimal_chain(
        self,
        *,
        source_type: str,
        signal_title: str,
        topic_title: str,
        variant_type: str,
        platform: str,
        content_title: str,
        content_body: str,
        asset_type: str,
        storage_path: str,
        declares_image: bool,
        publish_result_summary: str,
    ) -> dict[str, object]:
        signal = self.discovery_service.create_signal(source_type=source_type, title=signal_title)
        topic = self.advance_signal_to_topic(signal_id=signal.id, title=topic_title)
        variant = self.advance_topic_to_content(
            topic_id=topic.id,
            variant_type=variant_type,
            platform=platform,
            title=content_title,
            body=content_body,
        )
        image = self.advance_content_to_image(
            content_variant_id=variant.id,
            asset_type=asset_type,
            storage_path=storage_path,
        )
        check, items = self.advance_to_publish_check(
            content_variant_id=variant.id,
            image_asset_id=image.id,
            declares_image=declares_image,
            topic_id=topic.id,
            platform=platform,
        )
        retro = None
        if check.result != PublishCheckResult.BLOCK:
            retro = self.advance_to_retro(
                publish_check_id=check.id,
                signal_id=signal.id,
                topic_id=topic.id,
                publish_result_summary=publish_result_summary,
            )
        return {
            "signal": signal,
            "topic": topic,
            "content_variant": variant,
            "image_asset": image,
            "publish_check": check,
            "publish_check_items": items,
            "retro_record": retro,
        }
