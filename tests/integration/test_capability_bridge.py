from __future__ import annotations

from domain.models.execution_record import ExecutionRecord
from services.capability_bridge_service import CapabilityBridgeService
from services.check_service import PublishCheckService
from services.discovery_service import DiscoveryService
from services.topic_service import TopicService
from tests.support import IsolatedTestCase


class TestCapabilityBridgeIntegration(IsolatedTestCase):
    def test_content_and_image_capability_flow_writes_execution_records(self):
        discovery = DiscoveryService(db_path=self.db_path)
        topic_service = TopicService(db_path=self.db_path)
        bridge = CapabilityBridgeService(db_path=self.db_path)

        signal = discovery.create_signal(source_type="manual", title="capability-signal")
        topic = topic_service.create_from_signal(signal_id=signal.id, title="capability-topic")

        content_result = bridge.create_content_variant_with_capability(
            topic_id=topic.id,
            platform="xiaohongshu",
            seed_title="bridge-seed-title",
            seed_body="bridge-seed-body",
        )
        variant = content_result["content_variant"]
        self.assertEqual(variant.topic_id, topic.id)

        image_result = bridge.create_image_asset_with_capability(
            content_variant_id=variant.id,
            storage_path="tmp/test-output/bridge-image.png",
        )
        image = image_result["image_asset"]
        self.assertEqual(image.content_variant_id, variant.id)

        records = bridge.execution_records.repository.list(ExecutionRecord, order_by="started_at ASC")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].capability_name, "content_generation")
        self.assertEqual(records[1].capability_name, "image_generation")
        self.assertEqual(records[0].status.value, "SUCCEEDED")
        self.assertEqual(records[1].status.value, "SUCCEEDED")

    def test_publish_check_enhancement_writes_execution_record(self):
        discovery = DiscoveryService(db_path=self.db_path)
        topic_service = TopicService(db_path=self.db_path)
        bridge = CapabilityBridgeService(db_path=self.db_path)
        check_service = PublishCheckService(db_path=self.db_path)

        signal = discovery.create_signal(source_type="manual", title="enhancement-signal")
        topic = topic_service.create_from_signal(signal_id=signal.id, title="enhancement-topic")
        content_result = bridge.create_content_variant_with_capability(
            topic_id=topic.id,
            platform="xiaohongshu",
            seed_title="enhancement-title",
            seed_body="enhancement-body",
        )
        variant = content_result["content_variant"]
        check, _ = check_service.create_check(
            content_variant_id=variant.id,
            declares_image=False,
            topic_id=topic.id,
            platform="xiaohongshu",
        )

        enhancement = bridge.run_publish_check_enhancement(check_id=check.id)
        self.assertEqual(enhancement["publish_check"].id, check.id)
        self.assertEqual(enhancement["execution"].capability_name, "publish_check_enhancement")

        records = bridge.execution_records.repository.list(ExecutionRecord, order_by="started_at ASC")
        self.assertEqual(records[-1].capability_name, "publish_check_enhancement")
        self.assertEqual(records[-1].status.value, "SUCCEEDED")
