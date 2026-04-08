from __future__ import annotations

import copy

from domain.models.content_variant import ContentVariant
from domain.models.image_asset import ImageAsset
from domain.models.publish_check import PublishCheck
from domain.rules.statuses import (
    ContentVariantStatus,
    ImageAssetStatus,
    PublishCheckRecordStatus,
    PublishCheckResult,
)
from services.errors import GateBlockedError
from tests.support import IsolatedTestCase


class TestPublishCheckServiceIntegration(IsolatedTestCase):
    def test_publish_check_returns_pass_for_complete_package(self):
        workflow = self.make_workflow()
        chain = self.create_chain(workflow, content_case="pass", create_image=True)

        check, items = workflow.advance_to_publish_check(
            content_variant_id=chain["content_variant"].id,
            image_asset_id=chain["image_asset"].id,
            declares_image=True,
            topic_id=chain["topic"].id,
            platform=chain["content_variant"].platform,
        )

        self.assertEqual(check.result, PublishCheckResult.PASS)
        self.assertIsNone(check.risk_note)
        self.assertEqual(check.record_status, PublishCheckRecordStatus.ACTIVE)
        self.assertTrue(any(item.result == PublishCheckResult.PASS for item in items))

    def test_publish_check_returns_warn_and_allows_retro(self):
        workflow = self.make_workflow()
        chain = self.create_chain(workflow, content_case="warn", create_image=True)

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
        )

        self.assertEqual(check.result, PublishCheckResult.WARN)
        self.assertIsNotNone(check.risk_note)
        self.assertTrue(any(item.result == PublishCheckResult.WARN for item in items))
        self.assertEqual(retro.publish_check_id, check.id)

    def test_publish_check_returns_block_for_empty_content_and_blocks_retro(self):
        workflow = self.make_workflow()
        chain = self.create_chain(workflow, content_case="block", create_image=False)

        check, items = workflow.advance_to_publish_check(
            content_variant_id=chain["content_variant"].id,
            declares_image=False,
            topic_id=chain["topic"].id,
            platform=chain["content_variant"].platform,
        )

        self.assertEqual(check.result, PublishCheckResult.BLOCK)
        self.assertTrue(any(item.result == PublishCheckResult.BLOCK for item in items))
        with self.assertRaisesRegex(GateBlockedError, "BLOCK publish checks cannot create retrospective records"):
            workflow.advance_to_retro(publish_check_id=check.id, publish_result_summary="blocked")

    def test_publish_check_blocks_when_image_binding_is_wrong(self):
        workflow = self.make_workflow()
        first_chain = self.create_chain(workflow, content_case="pass", create_image=True)

        second_variant = workflow.advance_topic_to_content(
            topic_id=first_chain["topic"].id,
            **copy.deepcopy(self.case_data["content_cases"]["pass"]),
        )

        check, items = workflow.advance_to_publish_check(
            content_variant_id=second_variant.id,
            image_asset_id=first_chain["image_asset"].id,
            declares_image=True,
            topic_id=first_chain["topic"].id,
            platform=second_variant.platform,
        )

        self.assertEqual(check.result, PublishCheckResult.BLOCK)
        self.assertTrue(any(item.rule_code == "relation.image_belongs_to_content" for item in items))

    def test_content_recheck_invalidates_previous_record_and_appends_new_one(self):
        self._assert_recheck_invalidation(change_target="content")

    def test_image_recheck_invalidates_previous_record_and_appends_new_one(self):
        self._assert_recheck_invalidation(change_target="image")

    def _assert_recheck_invalidation(self, *, change_target: str) -> None:
        workflow = self.make_workflow()
        repository = workflow.discovery_service.repository
        chain = self.create_chain(workflow, content_case="pass", create_image=True)
        first_check, _ = workflow.advance_to_publish_check(
            content_variant_id=chain["content_variant"].id,
            image_asset_id=chain["image_asset"].id,
            declares_image=True,
            topic_id=chain["topic"].id,
            platform=chain["content_variant"].platform,
        )

        variant = repository.get(ContentVariant, chain["content_variant"].id)
        image = repository.get(ImageAsset, chain["image_asset"].id)
        self.assertIsNotNone(variant)
        self.assertIsNotNone(image)

        if change_target == "content":
            variant.body = "Updated body for a second check cycle."
            repository.update(variant)
            invalidated = workflow.invalidate_checks_for_content_change(content_variant_id=variant.id)
            self.assertEqual(repository.get(ContentVariant, variant.id).status, ContentVariantStatus.READY_FOR_IMAGE)
        else:
            image.storage_path = "tmp/test-output/cover-v2.png"
            repository.update(image)
            invalidated = workflow.invalidate_checks_for_image_change(image_asset_id=image.id)
            self.assertEqual(repository.get(ImageAsset, image.id).status, ImageAssetStatus.READY_FOR_CHECK)

        second_check, _ = workflow.advance_to_publish_check(
            content_variant_id=chain["content_variant"].id,
            image_asset_id=chain["image_asset"].id,
            declares_image=True,
            topic_id=chain["topic"].id,
            platform=chain["content_variant"].platform,
        )

        checks = repository.list(
            PublishCheck,
            where={"content_variant_id": chain["content_variant"].id},
            order_by="check_version ASC",
        )
        self.assertEqual(invalidated, 1)
        self.assertEqual(len(checks), 2)
        self.assertEqual(checks[0].id, first_check.id)
        self.assertEqual(checks[0].record_status, PublishCheckRecordStatus.INVALIDATED)
        self.assertIsNotNone(checks[0].invalidated_at)
        self.assertEqual(checks[1].id, second_check.id)
        self.assertEqual(checks[1].record_status, PublishCheckRecordStatus.ACTIVE)
        self.assertEqual(checks[1].check_version, 2)
