from __future__ import annotations

from domain.models.content_variant import ContentVariant
from domain.models.image_asset import ImageAsset
from domain.models.publish_check import PublishCheck
from domain.models.publish_check_item import PublishCheckItem
from domain.models.retro_record import RetroRecord
from domain.models.signal import Signal
from domain.models.topic import Topic
from domain.rules.statuses import (
    ContentVariantStatus,
    PublishCheckRecordStatus,
    PublishCheckResult,
    RetroRecordStatus,
    SignalStatus,
    TopicStatus,
)
from services.errors import EntityNotFoundError
from tests.support import IsolatedTestCase


class TestMainChainIntegration(IsolatedTestCase):
    def test_main_chain_positive_flow_persists_every_object(self):
        workflow = self.make_workflow()
        repository = workflow.discovery_service.repository
        chain = self.create_chain(workflow, content_case="pass", create_image=True)

        check, items = workflow.advance_to_publish_check(
            content_variant_id=chain["content_variant"].id,
            image_asset_id=chain["image_asset"].id,
            declares_image=True,
            topic_id=chain["topic"].id,
            platform=chain["content_variant"].platform,
        )
        retro = workflow.advance_to_retro(
            publish_check_id=check.id,
            signal_id=chain["signal"].id,
            topic_id=chain["topic"].id,
            publish_result_summary=self.case_data["retro"]["publish_result_summary"],
            insight=self.case_data["retro"]["insight"],
            next_action=self.case_data["retro"]["next_action"],
        )

        persisted_signal = repository.get(Signal, chain["signal"].id)
        persisted_topic = repository.get(Topic, chain["topic"].id)
        persisted_variant = repository.get(ContentVariant, chain["content_variant"].id)
        persisted_image = repository.get(ImageAsset, chain["image_asset"].id)
        persisted_check = repository.get(PublishCheck, check.id)
        persisted_retro = repository.get(RetroRecord, retro.id)

        self.assertIsNotNone(persisted_signal)
        self.assertEqual(persisted_signal.status, SignalStatus.CONVERTED)
        self.assertIsNotNone(persisted_topic)
        self.assertEqual(persisted_topic.status, TopicStatus.IN_CONTENT)
        self.assertIsNotNone(persisted_variant)
        self.assertEqual(persisted_variant.status, ContentVariantStatus.IN_CHECK)
        self.assertIsNotNone(persisted_image)
        self.assertIsNotNone(persisted_check)
        self.assertEqual(persisted_check.result, PublishCheckResult.PASS)
        self.assertEqual(persisted_check.record_status, PublishCheckRecordStatus.ACTIVE)
        self.assertEqual(len(repository.list(PublishCheckItem, where={"publish_check_id": check.id})), len(items))
        self.assertIsNotNone(persisted_retro)
        self.assertEqual(persisted_retro.status, RetroRecordStatus.CLOSED)

    def test_topic_requires_existing_signal(self):
        workflow = self.make_workflow()

        with self.assertRaisesRegex(EntityNotFoundError, "Signal not found"):
            workflow.advance_signal_to_topic(signal_id="sig_missing", title="no-signal-topic")

    def test_content_requires_existing_topic(self):
        workflow = self.make_workflow()

        with self.assertRaisesRegex(EntityNotFoundError, "Topic not found"):
            workflow.advance_topic_to_content(
                topic_id="top_missing",
                variant_type="post",
                platform="xiaohongshu",
                title="content-without-topic",
                body="body",
            )

    def test_image_requires_existing_content_variant(self):
        workflow = self.make_workflow()

        with self.assertRaisesRegex(EntityNotFoundError, "ContentVariant not found"):
            workflow.advance_content_to_image(
                content_variant_id="cnt_missing",
                asset_type="cover",
                storage_path="tmp/test-output/missing.png",
            )

    def test_retro_requires_existing_publish_check(self):
        workflow = self.make_workflow()

        with self.assertRaisesRegex(EntityNotFoundError, "PublishCheck not found"):
            workflow.advance_to_retro(publish_check_id="chk_missing", publish_result_summary="no-check")
