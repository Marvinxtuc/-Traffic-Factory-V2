from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    name: str
    description: str


class SkillRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, CapabilityDefinition] = {}

    def register(self, *, name: str, description: str) -> CapabilityDefinition:
        definition = CapabilityDefinition(name=name, description=description)
        self._definitions[name] = definition
        return definition

    def require(self, capability_name: str) -> CapabilityDefinition:
        if capability_name not in self._definitions:
            raise ValueError(f"Capability not registered: {capability_name}")
        return self._definitions[capability_name]

    def list_capabilities(self) -> list[CapabilityDefinition]:
        return list(self._definitions.values())


def build_default_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(name="content_generation", description="内容生成能力（最小占位）")
    registry.register(name="image_generation", description="图片生成能力（最小占位）")
    registry.register(name="publish_check_enhancement", description="发布检查增强能力（最小占位）")
    return registry
