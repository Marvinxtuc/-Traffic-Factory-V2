from __future__ import annotations

from domain.models.base import utc_now
from domain.models.content_variant import ContentVariant
from domain.models.topic import Topic
from domain.rules.statuses import ContentVariantStatus, TopicStatus
from services.base import BaseService
from services.errors import EntityNotFoundError


class ContentService(BaseService):
    """Content generation skeleton.

    Input: topic_id plus content fields
    Preconditions: the topic must exist
    Output: persisted ContentVariant
    State change: Topic -> IN_CONTENT, ContentVariant -> READY_FOR_IMAGE
    Failure: missing topic
    Next step: the created content variant may create image assets
    """

    def create_variant(
        self,
        *,
        topic_id: str,
        variant_type: str,
        platform: str,
        title: str,
        body: str,
        style_profile: str | None = None,
    ) -> ContentVariant:
        topic = self.repository.get(Topic, topic_id)
        if topic is None:
            raise EntityNotFoundError(f"Topic not found: {topic_id}")

        variant = ContentVariant(
            topic_id=topic.id,
            variant_type=variant_type,
            platform=platform,
            title=title,
            body=body,
            style_profile=style_profile,
            status=ContentVariantStatus.READY_FOR_IMAGE,
        )
        created = self.repository.add(variant)

        topic.status = TopicStatus.IN_CONTENT
        topic.updated_at = utc_now()
        self.repository.update(topic)
        return created

    def mark_modified(
        self,
        *,
        content_variant_id: str,
        title: str | None = None,
        body: str | None = None,
        style_profile: str | None = None,
    ) -> tuple[ContentVariant, int]:
        variant = self.repository.get(ContentVariant, content_variant_id)
        if variant is None:
            raise EntityNotFoundError(f"ContentVariant not found: {content_variant_id}")

        if title is not None:
            variant.title = title
        if body is not None:
            variant.body = body
        if style_profile is not None:
            variant.style_profile = style_profile

        variant.revision_no += 1
        variant.updated_at = utc_now()
        self.repository.update(variant)

        from services.check_service import PublishCheckService

        invalidated = PublishCheckService(db_path=self.repository.db_path).invalidate_for_content_variant_change(
            content_variant_id
        )
        refreshed = self.repository.get(ContentVariant, content_variant_id)
        if refreshed is None:
            raise EntityNotFoundError(f"ContentVariant not found: {content_variant_id}")
        return refreshed, invalidated
