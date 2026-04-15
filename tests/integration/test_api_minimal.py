from __future__ import annotations

from app.api.main import MinimalApiApplication
from domain.rules.statuses import PublishCheckResult
from tests.support import IsolatedTestCase


class TestMinimalApiIntegration(IsolatedTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.api = MinimalApiApplication(db_path=self.db_path)

    def test_route_registry_contains_six_core_modules(self):
        route_paths = {(item.method, item.path) for item in self.api.list_routes()}

        expected_paths = {
            ("GET", "/signals"),
            ("GET", "/topics"),
            ("GET", "/contents"),
            ("GET", "/images"),
            ("GET", "/checks"),
            ("GET", "/retros"),
        }
        self.assertTrue(expected_paths.issubset(route_paths))

    def test_main_chain_positive_api_flow(self):
        signal_resp = self.api.handle(
            method="POST",
            path="/signals",
            payload={"source_type": "manual", "title": "api-signal"},
        )
        self.assertTrue(signal_resp["ok"])
        signal_id = signal_resp["data"]["id"]

        topic_resp = self.api.handle(
            method="POST",
            path=f"/signals/{signal_id}/advance-to-topic",
            payload={"title": "api-topic"},
        )
        self.assertTrue(topic_resp["ok"])
        topic_id = topic_resp["data"]["id"]

        content_resp = self.api.handle(
            method="POST",
            path=f"/topics/{topic_id}/advance-to-content",
            payload={
                "variant_type": "post",
                "platform": "xiaohongshu",
                "title": "api pass title",
                "body": "This is a complete body for check.",
            },
        )
        self.assertTrue(content_resp["ok"])
        content_id = content_resp["data"]["id"]

        image_resp = self.api.handle(
            method="POST",
            path=f"/contents/{content_id}/advance-to-image",
            payload={
                "asset_type": "cover",
                "storage_path": "tmp/test-output/api-cover.png",
            },
        )
        self.assertTrue(image_resp["ok"])
        image_id = image_resp["data"]["id"]

        check_resp = self.api.handle(
            method="POST",
            path="/checks/submit",
            payload={
                "content_variant_id": content_id,
                "image_asset_id": image_id,
                "declares_image": True,
                "topic_id": topic_id,
                "platform": "xiaohongshu",
            },
        )
        self.assertTrue(check_resp["ok"])
        self.assertEqual(check_resp["data"]["check"]["result"], PublishCheckResult.PASS.value)
        check_id = check_resp["data"]["check"]["id"]

        retro_resp = self.api.handle(
            method="POST",
            path=f"/checks/{check_id}/advance-to-retro",
            payload={"publish_result_summary": "api retro summary"},
        )
        self.assertTrue(retro_resp["ok"])

    def test_negative_flow_rejects_topic_creation_without_signal(self):
        response = self.api.handle(
            method="POST",
            path="/signals/sig_missing/advance-to-topic",
            payload={"title": "bad-topic"},
        )
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "ENTITY_NOT_FOUND")

    def test_block_check_cannot_advance_to_retro(self):
        signal_resp = self.api.handle(
            method="POST",
            path="/signals",
            payload={"source_type": "manual", "title": "block-signal"},
        )
        signal_id = signal_resp["data"]["id"]

        topic_resp = self.api.handle(
            method="POST",
            path=f"/signals/{signal_id}/advance-to-topic",
            payload={"title": "block-topic"},
        )
        topic_id = topic_resp["data"]["id"]

        content_resp = self.api.handle(
            method="POST",
            path=f"/topics/{topic_id}/advance-to-content",
            payload={
                "variant_type": "post",
                "platform": "xiaohongshu",
                "title": "block-check-title",
                "body": "content exists but image declaration will block",
            },
        )
        content_id = content_resp["data"]["id"]

        check_resp = self.api.handle(
            method="POST",
            path="/checks/submit",
            payload={
                "content_variant_id": content_id,
                "declares_image": True,
                "topic_id": topic_id,
            },
        )
        self.assertTrue(check_resp["ok"])
        self.assertEqual(check_resp["data"]["check"]["result"], PublishCheckResult.BLOCK.value)
        check_id = check_resp["data"]["check"]["id"]

        retro_resp = self.api.handle(
            method="POST",
            path=f"/checks/{check_id}/advance-to-retro",
            payload={"publish_result_summary": "should-fail"},
        )
        self.assertFalse(retro_resp["ok"])
        self.assertEqual(retro_resp["error"]["code"], "GATE_BLOCKED")

    def test_check_submit_requires_content_variant_id(self):
        response = self.api.handle(method="POST", path="/checks/submit", payload={})
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "BAD_REQUEST")

    def test_mark_modified_endpoints_invalidate_old_checks(self):
        signal_resp = self.api.handle(
            method="POST",
            path="/signals",
            payload={"source_type": "manual", "title": "modify-signal"},
        )
        signal_id = signal_resp["data"]["id"]

        topic_resp = self.api.handle(
            method="POST",
            path=f"/signals/{signal_id}/advance-to-topic",
            payload={"title": "modify-topic"},
        )
        topic_id = topic_resp["data"]["id"]

        content_resp = self.api.handle(
            method="POST",
            path=f"/topics/{topic_id}/advance-to-content",
            payload={
                "variant_type": "post",
                "platform": "xiaohongshu",
                "title": "modify title",
                "body": "modify body",
            },
        )
        content_id = content_resp["data"]["id"]

        image_resp = self.api.handle(
            method="POST",
            path=f"/contents/{content_id}/advance-to-image",
            payload={"asset_type": "cover", "storage_path": "tmp/test-output/api-modify.png"},
        )
        image_id = image_resp["data"]["id"]

        check_resp = self.api.handle(
            method="POST",
            path="/checks/submit",
            payload={
                "content_variant_id": content_id,
                "image_asset_id": image_id,
                "declares_image": True,
                "topic_id": topic_id,
                "platform": "xiaohongshu",
            },
        )
        self.assertTrue(check_resp["ok"])

        content_modified = self.api.handle(
            method="POST",
            path=f"/contents/{content_id}/mark-modified",
            payload={"body": "body updated for recheck"},
        )
        self.assertTrue(content_modified["ok"])
        self.assertTrue(content_modified["data"]["requires_recheck"])
        self.assertEqual(content_modified["data"]["invalidated_checks"], 1)

        checks_after_content = self.api.handle(
            method="GET",
            path="/checks",
            query={"content_variant_id": content_id},
        )
        self.assertTrue(checks_after_content["ok"])
        self.assertEqual(checks_after_content["data"]["items"][0]["record_status"], "INVALIDATED")

        check_resp_2 = self.api.handle(
            method="POST",
            path="/checks/submit",
            payload={
                "content_variant_id": content_id,
                "image_asset_id": image_id,
                "declares_image": True,
                "topic_id": topic_id,
                "platform": "xiaohongshu",
            },
        )
        self.assertTrue(check_resp_2["ok"])

        image_modified = self.api.handle(
            method="POST",
            path=f"/images/{image_id}/mark-modified",
            payload={"storage_path": "tmp/test-output/api-modify-v2.png"},
        )
        self.assertTrue(image_modified["ok"])
        self.assertTrue(image_modified["data"]["requires_recheck"])
        self.assertEqual(image_modified["data"]["invalidated_checks"], 1)

    def test_signal_list_supports_source_name_keyword_filter(self):
        created_alpha = self.api.handle(
            method="POST",
            path="/signals",
            payload={
                "source_type": "manual",
                "title": "alpha-signal",
                "source_ref": "wechat-trend",
                "source_url": "https://a.example.com/wechat",
            },
        )
        self.assertTrue(created_alpha["ok"])

        created_beta = self.api.handle(
            method="POST",
            path="/signals",
            payload={
                "source_type": "manual",
                "title": "beta-signal",
                "source_ref": "reddit-hot",
                "source_url": "https://b.example.com/reddit",
            },
        )
        self.assertTrue(created_beta["ok"])

        filtered = self.api.handle(
            method="GET",
            path="/signals",
            query={"source_name": "wechat"},
        )
        self.assertTrue(filtered["ok"])
        items = filtered["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "alpha-signal")
