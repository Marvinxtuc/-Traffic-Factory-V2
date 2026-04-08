from __future__ import annotations

from domain.models.base import utc_now
from domain.models.content_variant import ContentVariant
from domain.models.image_asset import ImageAsset
from domain.models.publish_check import PublishCheck
from domain.models.publish_check_item import PublishCheckItem
from domain.rules.publish_check_rules import (
    CheckRuleOutcome,
    aggregate_publish_check_result,
    choose_rework_target,
    count_outcomes,
    evaluate_minimal_publish_check,
    summarize_outcomes,
)
from domain.rules.statuses import (
    ContentVariantStatus,
    ImageAssetStatus,
    PublishCheckRecordStatus,
    PublishCheckResult,
)
from services.base import BaseService
from services.errors import EntityNotFoundError


class PublishCheckService(BaseService):
    """Quality-gate skeleton.

    Input: content_variant_id, optional image_asset_id and image declaration flag
    Preconditions: content variant must exist
    Output: append-only PublishCheck plus optional PublishCheckItems
    State change: previous active checks become INVALIDATED, new check becomes ACTIVE
    Failure: missing content variant
    Next step: PASS/WARN allow retrospective creation; BLOCK forces revision
    """

    def create_check(
        self,
        *,
        content_variant_id: str,
        image_asset_id: str | None = None,
        declares_image: bool = False,
        topic_id: str | None = None,
        platform: str | None = None,
    ) -> tuple[PublishCheck, list[PublishCheckItem]]:
        variant = self.repository.get(ContentVariant, content_variant_id)
        if variant is None:
            raise EntityNotFoundError(f"ContentVariant not found: {content_variant_id}")

        declares_image = declares_image or image_asset_id is not None
        image_exists = False
        bound_image_asset_id: str | None = None
        if image_asset_id is not None:
            image = self.repository.get(ImageAsset, image_asset_id)
            if image is not None:
                image_exists = True
                bound_image_asset_id = image.id
        else:
            image = None

        outcomes = evaluate_minimal_publish_check(
            content_variant=variant,
            image_asset=image,
            declares_image=declares_image,
            image_exists=image_exists,
        )
        result = aggregate_publish_check_result(outcomes)
        problem_summary, suggested_action, risk_note = summarize_outcomes(outcomes)
        pass_count, warn_count, block_count = count_outcomes(outcomes)

        self.invalidate_for_content_variant_change(content_variant_id)

        next_version = (
            self.repository.scalar(
                "SELECT COALESCE(MAX(check_version), 0) + 1 FROM publish_checks WHERE content_variant_id = ?",
                (content_variant_id,),
            )
            or 1
        )

        check = PublishCheck(
            content_variant_id=content_variant_id,
            image_asset_id=bound_image_asset_id,
            topic_id=topic_id,
            platform=platform,
            result=result,
            problem_summary=problem_summary,
            suggested_action=suggested_action,
            risk_note=risk_note,
            check_version=int(next_version),
            record_status=PublishCheckRecordStatus.ACTIVE,
            block_count=block_count,
            warn_count=warn_count,
            pass_count=pass_count,
        )
        created = self.repository.add(check)

        item_records: list[PublishCheckItem] = []
        for item in outcomes:
            record = PublishCheckItem(
                publish_check_id=created.id,
                rule_code=item.rule_code,
                rule_category=item.rule_category,
                severity=item.severity,
                result=item.result,
                message=item.message,
                suggestion=item.suggestion,
            )
            self.repository.add(record)
            item_records.append(record)

        if result == PublishCheckResult.BLOCK:
            rework_target = choose_rework_target(outcomes, image_context_present=declares_image)
            if rework_target == "image" and image is not None:
                image.status = ImageAssetStatus.NEEDS_REVISION
                image.updated_at = utc_now()
                self.repository.update(image)
            else:
                variant.status = (
                    ContentVariantStatus.READY_FOR_IMAGE
                    if rework_target == "image"
                    else ContentVariantStatus.NEEDS_REVISION
                )
                variant.updated_at = utc_now()
                self.repository.update(variant)
        else:
            variant.status = ContentVariantStatus.IN_CHECK
            variant.updated_at = utc_now()
            self.repository.update(variant)

        return created, item_records

    def invalidate_for_content_variant_change(self, content_variant_id: str) -> int:
        variant = self.repository.get(ContentVariant, content_variant_id)
        if variant is None:
            raise EntityNotFoundError(f"ContentVariant not found: {content_variant_id}")

        variant.status = ContentVariantStatus.READY_FOR_IMAGE
        variant.updated_at = utc_now()
        self.repository.update(variant)
        return self.repository.execute(
            """
            UPDATE publish_checks
               SET record_status = ?, invalidated_at = ?
             WHERE content_variant_id = ? AND record_status = ?
            """,
            (
                PublishCheckRecordStatus.INVALIDATED.value,
                utc_now().isoformat(),
                content_variant_id,
                PublishCheckRecordStatus.ACTIVE.value,
            ),
        )

    def invalidate_for_image_asset_change(self, image_asset_id: str) -> int:
        image = self.repository.get(ImageAsset, image_asset_id)
        if image is None:
            raise EntityNotFoundError(f"ImageAsset not found: {image_asset_id}")

        image.status = ImageAssetStatus.READY_FOR_CHECK
        image.updated_at = utc_now()
        self.repository.update(image)
        return self.repository.execute(
            """
            UPDATE publish_checks
               SET record_status = ?, invalidated_at = ?
             WHERE image_asset_id = ? AND record_status = ?
            """,
            (
                PublishCheckRecordStatus.INVALIDATED.value,
                utc_now().isoformat(),
                image_asset_id,
                PublishCheckRecordStatus.ACTIVE.value,
            ),
        )
