from __future__ import annotations

import unittest

from domain.models.content_variant import ContentVariant
from domain.models.image_asset import ImageAsset
from domain.rules.publish_check_rules import (
    aggregate_publish_check_result,
    evaluate_minimal_publish_check,
    summarize_outcomes,
)
from domain.rules.statuses import PublishCheckResult


def make_variant(*, title: str, body: str, variant_id: str = "cnt_case") -> ContentVariant:
    return ContentVariant(
        id=variant_id,
        topic_id="top_case",
        variant_type="post",
        platform="xiaohongshu",
        title=title,
        body=body,
    )


def make_image(*, content_variant_id: str) -> ImageAsset:
    return ImageAsset(
        id="img_case",
        content_variant_id=content_variant_id,
        asset_type="cover",
        storage_path="tmp/test-output/cover.png",
    )


class TestPublishCheckRules(unittest.TestCase):
    def test_publish_check_rules_return_pass_for_complete_package(self):
        outcomes = evaluate_minimal_publish_check(
            content_variant=make_variant(title="long enough title", body="complete body"),
            image_asset=make_image(content_variant_id="cnt_case"),
            declares_image=True,
            image_exists=True,
        )
        problem_summary, suggested_action, risk_note = summarize_outcomes(outcomes)

        self.assertEqual(aggregate_publish_check_result(outcomes), PublishCheckResult.PASS)
        self.assertIsNone(problem_summary)
        self.assertIsNone(suggested_action)
        self.assertIsNone(risk_note)

    def test_publish_check_rules_return_warn_for_short_title(self):
        outcomes = evaluate_minimal_publish_check(
            content_variant=make_variant(title="short", body="complete body"),
            image_asset=None,
            declares_image=False,
            image_exists=False,
        )
        problem_summary, suggested_action, risk_note = summarize_outcomes(outcomes)

        self.assertEqual(aggregate_publish_check_result(outcomes), PublishCheckResult.WARN)
        self.assertIsNotNone(problem_summary)
        self.assertIn("8", problem_summary)
        self.assertIsNotNone(suggested_action)
        self.assertIsNotNone(risk_note)

    def test_publish_check_rules_return_block_for_missing_content_and_wrong_image_binding(self):
        outcomes = evaluate_minimal_publish_check(
            content_variant=make_variant(title="", body=""),
            image_asset=make_image(content_variant_id="cnt_other"),
            declares_image=True,
            image_exists=True,
        )
        problem_summary, suggested_action, risk_note = summarize_outcomes(outcomes)

        self.assertEqual(aggregate_publish_check_result(outcomes), PublishCheckResult.BLOCK)
        self.assertIsNotNone(problem_summary)
        self.assertIsNotNone(suggested_action)
        self.assertIsNone(risk_note)
