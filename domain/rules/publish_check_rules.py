from __future__ import annotations

from dataclasses import dataclass

from domain.models.content_variant import ContentVariant
from domain.models.image_asset import ImageAsset
from domain.rules.statuses import CheckItemSeverity, PublishCheckResult


CHECK_CATEGORY_INTEGRITY = "完整性"
CHECK_CATEGORY_RELATION = "关联性"
CHECK_CATEGORY_QUALITY = "基础质量"

TITLE_WARN_THRESHOLD = 8


@dataclass(slots=True)
class CheckRuleOutcome:
    rule_code: str
    rule_category: str
    severity: CheckItemSeverity
    result: PublishCheckResult
    message: str
    suggestion: str | None = None


def evaluate_minimal_publish_check(
    *,
    content_variant: ContentVariant,
    image_asset: ImageAsset | None,
    declares_image: bool,
    image_exists: bool,
) -> list[CheckRuleOutcome]:
    outcomes: list[CheckRuleOutcome] = []
    title = content_variant.title.strip()
    body = content_variant.body.strip()

    outcomes.append(
        CheckRuleOutcome(
            rule_code="integrity.content_variant_exists",
            rule_category=CHECK_CATEGORY_INTEGRITY,
            severity=CheckItemSeverity.INFO,
            result=PublishCheckResult.PASS,
            message="内容版本存在，可进入最小发布检查。",
        )
    )

    if not body:
        outcomes.append(
            CheckRuleOutcome(
                rule_code="integrity.content_body_non_empty",
                rule_category=CHECK_CATEGORY_INTEGRITY,
                severity=CheckItemSeverity.BLOCK,
                result=PublishCheckResult.BLOCK,
                message="内容正文为空，不能进入发布。",
                suggestion="补全文案正文后重新检查。",
            )
        )
    else:
        outcomes.append(
            CheckRuleOutcome(
                rule_code="integrity.content_body_non_empty",
                rule_category=CHECK_CATEGORY_INTEGRITY,
                severity=CheckItemSeverity.INFO,
                result=PublishCheckResult.PASS,
                message="内容正文存在。",
            )
        )

    if not title:
        outcomes.append(
            CheckRuleOutcome(
                rule_code="integrity.title_required",
                rule_category=CHECK_CATEGORY_INTEGRITY,
                severity=CheckItemSeverity.BLOCK,
                result=PublishCheckResult.BLOCK,
                message="标题为空，不能进入发布。",
                suggestion="补充标题后重新检查。",
            )
        )
    else:
        outcomes.append(
            CheckRuleOutcome(
                rule_code="integrity.title_required",
                rule_category=CHECK_CATEGORY_INTEGRITY,
                severity=CheckItemSeverity.INFO,
                result=PublishCheckResult.PASS,
                message="标题存在。",
            )
        )

    if title and len(title) < TITLE_WARN_THRESHOLD:
        outcomes.append(
            CheckRuleOutcome(
                rule_code="quality.title_min_length",
                rule_category=CHECK_CATEGORY_QUALITY,
                severity=CheckItemSeverity.WARN,
                result=PublishCheckResult.WARN,
                message=f"标题长度小于 {TITLE_WARN_THRESHOLD}，建议补强。",
                suggestion="扩充标题信息量，避免过短表达。",
            )
        )
    else:
        outcomes.append(
            CheckRuleOutcome(
                rule_code="quality.title_min_length",
                rule_category=CHECK_CATEGORY_QUALITY,
                severity=CheckItemSeverity.INFO,
                result=PublishCheckResult.PASS,
                message="标题长度满足最小要求。",
            )
        )

    if declares_image and not image_exists:
        outcomes.append(
            CheckRuleOutcome(
                rule_code="relation.image_required_when_declared",
                rule_category=CHECK_CATEGORY_RELATION,
                severity=CheckItemSeverity.BLOCK,
                result=PublishCheckResult.BLOCK,
                message="送检声明带图，但图片资产不存在。",
                suggestion="先在图片工坊生成并选择图片资产。",
            )
        )
    else:
        outcomes.append(
            CheckRuleOutcome(
                rule_code="relation.image_required_when_declared",
                rule_category=CHECK_CATEGORY_RELATION,
                severity=CheckItemSeverity.INFO,
                result=PublishCheckResult.PASS,
                message="图片声明与资产存在情况一致。",
            )
        )

    if image_asset is not None and image_asset.content_variant_id != content_variant.id:
        outcomes.append(
            CheckRuleOutcome(
                rule_code="relation.image_belongs_to_content",
                rule_category=CHECK_CATEGORY_RELATION,
                severity=CheckItemSeverity.BLOCK,
                result=PublishCheckResult.BLOCK,
                message="图片资产不属于当前内容版本。",
                suggestion="返回图片工坊重新绑定正确资产。",
            )
        )
    else:
        outcomes.append(
            CheckRuleOutcome(
                rule_code="relation.image_belongs_to_content",
                rule_category=CHECK_CATEGORY_RELATION,
                severity=CheckItemSeverity.INFO,
                result=PublishCheckResult.PASS,
                message="图片资产与内容版本关联正确。",
            )
        )

    return outcomes


def aggregate_publish_check_result(outcomes: list[CheckRuleOutcome]) -> PublishCheckResult:
    if any(item.result == PublishCheckResult.BLOCK for item in outcomes):
        return PublishCheckResult.BLOCK
    if any(item.result == PublishCheckResult.WARN for item in outcomes):
        return PublishCheckResult.WARN
    return PublishCheckResult.PASS


def summarize_outcomes(outcomes: list[CheckRuleOutcome]) -> tuple[str | None, str | None, str | None]:
    problems = [item.message for item in outcomes if item.result != PublishCheckResult.PASS]
    suggestions = [item.suggestion for item in outcomes if item.suggestion]
    risks = [item.message for item in outcomes if item.result == PublishCheckResult.WARN]
    problem_summary = " | ".join(problems) if problems else None
    suggested_action = " | ".join(suggestions) if suggestions else None
    risk_note = " | ".join(risks) if risks else None
    return problem_summary, suggested_action, risk_note


def count_outcomes(outcomes: list[CheckRuleOutcome]) -> tuple[int, int, int]:
    pass_count = sum(1 for item in outcomes if item.result == PublishCheckResult.PASS)
    warn_count = sum(1 for item in outcomes if item.result == PublishCheckResult.WARN)
    block_count = sum(1 for item in outcomes if item.result == PublishCheckResult.BLOCK)
    return pass_count, warn_count, block_count


def choose_rework_target(outcomes: list[CheckRuleOutcome], *, image_context_present: bool) -> str:
    relation_block = any(
        item.result == PublishCheckResult.BLOCK and item.rule_category == CHECK_CATEGORY_RELATION
        for item in outcomes
    )
    if relation_block or image_context_present:
        return "image"
    return "content"
