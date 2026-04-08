from __future__ import annotations

from app.web.action_bridge import WebActionBridge
from domain.models.publish_check import PublishCheck
from domain.rules.statuses import PublishCheckRecordStatus, PublishCheckResult
from tests.support import IsolatedTestCase


class TestWebActionBridgeIntegration(IsolatedTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.bridge = WebActionBridge(db_path=self.db_path)
        self.workflow = self.make_workflow()
        self.repository = self.workflow.discovery_service.repository

    def test_discovery_to_topic_action_can_succeed_and_reject_missing_signal(self):
        signal = self.workflow.discovery_service.create_signal(source_type="manual", title="web-action-signal")

        success = self.bridge.run(
            "discovery_to_topic",
            {
                "signal_id": signal.id,
                "title": "web-action-topic",
            },
        )
        self.assertTrue(success["ok"])

        missing = self.bridge.run(
            "discovery_to_topic",
            {
                "signal_id": "sig_missing",
                "title": "bad-topic",
            },
        )
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["error"]["code"], "ENTITY_NOT_FOUND")

    def test_content_page_actions_link_to_image_and_precheck(self):
        signal = self.workflow.discovery_service.create_signal(source_type="manual", title="content-signal")
        topic = self.workflow.advance_signal_to_topic(signal_id=signal.id, title="content-topic")

        content = self.bridge.run(
            "topic_to_content",
            {
                "topic_id": topic.id,
                "variant_type": "post",
                "platform": "xiaohongshu",
                "title": "content title",
                "body": "content body",
            },
        )
        self.assertTrue(content["ok"])
        content_id = content["data"]["id"]

        precheck_fail = self.bridge.run("content_precheck", {"content_variant_id": content_id})
        self.assertFalse(precheck_fail["ok"])
        self.assertEqual(precheck_fail["error"]["code"], "PRECHECK_FAILED")

        image = self.bridge.run(
            "content_to_image",
            {
                "content_variant_id": content_id,
                "asset_type": "cover",
                "storage_path": "tmp/test-output/web-action-image.png",
            },
        )
        self.assertTrue(image["ok"])

        precheck_success = self.bridge.run("content_precheck", {"content_variant_id": content_id})
        self.assertTrue(precheck_success["ok"])
        self.assertEqual(precheck_success["data"]["image_count"], 1)

    def test_check_page_actions_enforce_gate_and_rollback(self):
        signal = self.workflow.discovery_service.create_signal(source_type="manual", title="block-signal")
        topic = self.workflow.advance_signal_to_topic(signal_id=signal.id, title="block-topic")
        content = self.workflow.advance_topic_to_content(
            topic_id=topic.id,
            variant_type="post",
            platform="xiaohongshu",
            title="block-title",
            body="body exists",
        )

        check_resp = self.bridge.run(
            "image_submit_check",
            {
                "content_variant_id": content.id,
                "declares_image": True,
                "topic_id": topic.id,
                "platform": "xiaohongshu",
            },
        )
        self.assertTrue(check_resp["ok"])
        self.assertEqual(check_resp["data"]["check"]["result"], PublishCheckResult.BLOCK.value)
        check_id = check_resp["data"]["check"]["id"]

        rollback = self.bridge.run("check_rollback", {"check_id": check_id})
        self.assertTrue(rollback["ok"])
        self.assertTrue(rollback["data"]["requires_rework"])
        self.assertEqual(rollback["data"]["rollback_route"], "/images")

        retro_blocked = self.bridge.run("check_to_retro", {"check_id": check_id})
        self.assertFalse(retro_blocked["ok"])
        self.assertEqual(retro_blocked["error"]["code"], "GATE_BLOCKED")

    def test_recheck_action_appends_new_publish_check_record(self):
        chain = self.create_chain(self.workflow, content_case="pass", create_image=True)
        first_check, _ = self.workflow.advance_to_publish_check(
            content_variant_id=chain["content_variant"].id,
            image_asset_id=chain["image_asset"].id,
            declares_image=True,
            topic_id=chain["topic"].id,
            platform=chain["content_variant"].platform,
        )

        rechecked = self.bridge.run("check_recheck", {"check_id": first_check.id})
        self.assertTrue(rechecked["ok"])

        checks = self.repository.list(
            PublishCheck,
            where={"content_variant_id": chain["content_variant"].id},
            order_by="check_version ASC",
        )
        self.assertEqual(len(checks), 2)
        self.assertEqual(checks[0].record_status, PublishCheckRecordStatus.INVALIDATED)
        self.assertEqual(checks[1].record_status, PublishCheckRecordStatus.ACTIVE)

    def test_retro_create_action_requires_publish_check_and_allows_warn(self):
        missing = self.bridge.run("retro_create", {"publish_result_summary": "missing"})
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["error"]["code"], "BAD_REQUEST")

        chain = self.create_chain(self.workflow, content_case="warn", create_image=True)
        check, _ = self.workflow.advance_to_publish_check(
            content_variant_id=chain["content_variant"].id,
            image_asset_id=chain["image_asset"].id,
            declares_image=True,
            topic_id=chain["topic"].id,
            platform=chain["content_variant"].platform,
        )
        self.assertEqual(check.result, PublishCheckResult.WARN)

        created = self.bridge.run(
            "retro_create",
            {
                "publish_check_id": check.id,
                "publish_result_summary": "warn path retro",
            },
        )
        self.assertTrue(created["ok"])

    def test_mark_modified_actions_invalidate_old_checks(self):
        chain = self.create_chain(self.workflow, content_case="pass", create_image=True)
        check, _ = self.workflow.advance_to_publish_check(
            content_variant_id=chain["content_variant"].id,
            image_asset_id=chain["image_asset"].id,
            declares_image=True,
            topic_id=chain["topic"].id,
            platform=chain["content_variant"].platform,
        )

        marked_content = self.bridge.run(
            "content_mark_modified",
            {
                "content_variant_id": chain["content_variant"].id,
                "body": "content changed by bridge action",
            },
        )
        self.assertTrue(marked_content["ok"])
        self.assertEqual(marked_content["data"]["invalidated_checks"], 1)

        checks_after_content = self.repository.list(
            PublishCheck,
            where={"content_variant_id": chain["content_variant"].id},
            order_by="check_version ASC",
        )
        self.assertEqual(checks_after_content[-1].record_status, PublishCheckRecordStatus.INVALIDATED)

        check_again = self.bridge.run(
            "image_submit_check",
            {
                "content_variant_id": chain["content_variant"].id,
                "image_asset_id": chain["image_asset"].id,
                "declares_image": True,
                "topic_id": chain["topic"].id,
                "platform": chain["content_variant"].platform,
            },
        )
        self.assertTrue(check_again["ok"])

        marked_image = self.bridge.run(
            "image_mark_modified",
            {
                "image_asset_id": chain["image_asset"].id,
                "storage_path": "tmp/test-output/image-v2.png",
            },
        )
        self.assertTrue(marked_image["ok"])
        self.assertEqual(marked_image["data"]["invalidated_checks"], 1)
