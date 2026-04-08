from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.api.base import JsonDict, error_response, success_response
from app.api.main import MinimalApiApplication


@dataclass(frozen=True, slots=True)
class PageActionSpec:
    code: str
    page: str
    summary: str


ACTION_SPECS: tuple[PageActionSpec, ...] = (
    PageActionSpec("discovery_to_topic", "/discovery", "发现台转入选题"),
    PageActionSpec("topic_to_content", "/topics", "选题池开始写稿"),
    PageActionSpec("content_to_image", "/contents", "内容工坊配套图片"),
    PageActionSpec("content_precheck", "/contents", "内容工坊送检前置检查"),
    PageActionSpec("content_mark_modified", "/contents", "内容工坊标记修改并触发重检"),
    PageActionSpec("image_submit_check", "/images", "图片工坊提交检查"),
    PageActionSpec("image_mark_modified", "/images", "图片工坊标记修改并触发重检"),
    PageActionSpec("check_recheck", "/checks", "发布检查重新检查"),
    PageActionSpec("check_rollback", "/checks", "发布检查回退修改"),
    PageActionSpec("check_to_retro", "/checks", "发布检查通过或警告后进入复盘"),
    PageActionSpec("retro_create", "/retros", "复盘台创建复盘记录"),
)

SUPPORTED_ACTIONS: tuple[str, ...] = tuple(spec.code for spec in ACTION_SPECS)


class WebActionBridge:
    """Minimal page-action bridge that reuses existing API entries."""

    def __init__(self, *, db_path: str | Path | None = None):
        self.api = MinimalApiApplication(db_path=db_path)
        self._handlers = {
            "discovery_to_topic": self._discovery_to_topic,
            "topic_to_content": self._topic_to_content,
            "content_to_image": self._content_to_image,
            "content_precheck": self._content_precheck,
            "content_mark_modified": self._content_mark_modified,
            "image_submit_check": self._image_submit_check,
            "image_mark_modified": self._image_mark_modified,
            "check_recheck": self._check_recheck,
            "check_rollback": self._check_rollback,
            "check_to_retro": self._check_to_retro,
            "retro_create": self._retro_create,
        }

    def list_actions(self) -> tuple[PageActionSpec, ...]:
        return ACTION_SPECS

    def run(self, action: str, payload: JsonDict | None = None) -> JsonDict:
        action_key = (action or "").strip()
        if not action_key:
            return error_response("BAD_REQUEST", "Action code is required.")
        handler = self._handlers.get(action_key)
        if handler is None:
            return error_response("ACTION_NOT_FOUND", f"Unsupported page action: {action_key}")

        try:
            return handler(dict(payload or {}))
        except Exception as exc:  # pragma: no cover - defensive guard
            return error_response("WEB_ACTION_ERROR", f"Unhandled web action error: {exc}")

    def _discovery_to_topic(self, payload: JsonDict) -> JsonDict:
        missing = self._missing_fields(payload, "signal_id", "title")
        if missing:
            return self._missing_field_error(missing)
        return self.api.handle(
            method="POST",
            path=f"/signals/{payload['signal_id']}/advance-to-topic",
            payload={
                "title": payload["title"],
                "angle": payload.get("angle"),
                "priority": payload.get("priority", "P1"),
                "target_platform": payload.get("target_platform"),
                "decision_note": payload.get("decision_note"),
            },
        )

    def _topic_to_content(self, payload: JsonDict) -> JsonDict:
        missing = self._missing_fields(payload, "topic_id", "variant_type", "platform", "title", "body")
        if missing:
            return self._missing_field_error(missing)
        return self.api.handle(
            method="POST",
            path=f"/topics/{payload['topic_id']}/advance-to-content",
            payload={
                "variant_type": payload["variant_type"],
                "platform": payload["platform"],
                "title": payload["title"],
                "body": payload["body"],
                "style_profile": payload.get("style_profile"),
            },
        )

    def _content_to_image(self, payload: JsonDict) -> JsonDict:
        missing = self._missing_fields(payload, "content_variant_id", "asset_type", "storage_path")
        if missing:
            return self._missing_field_error(missing)
        return self.api.handle(
            method="POST",
            path=f"/contents/{payload['content_variant_id']}/advance-to-image",
            payload={
                "asset_type": payload["asset_type"],
                "storage_path": payload["storage_path"],
                "template_id": payload.get("template_id"),
                "prompt_snapshot": payload.get("prompt_snapshot"),
                "width": payload.get("width"),
                "height": payload.get("height"),
            },
        )

    def _content_precheck(self, payload: JsonDict) -> JsonDict:
        missing = self._missing_fields(payload, "content_variant_id")
        if missing:
            return self._missing_field_error(missing)

        images = self.api.handle(
            method="GET",
            path="/images",
            query={"content_variant_id": payload["content_variant_id"]},
        )
        if not images.get("ok"):
            return images

        items = images["data"]["items"]
        if not items:
            return error_response("PRECHECK_FAILED", "当前内容版本暂无图片资产，不能提交发布检查。")

        return success_response(
            {
                "content_variant_id": payload["content_variant_id"],
                "image_asset_id": items[0]["id"],
                "image_count": len(items),
            },
            message="送检前置检查通过。",
        )

    def _image_submit_check(self, payload: JsonDict) -> JsonDict:
        missing = self._missing_fields(payload, "content_variant_id")
        if missing:
            return self._missing_field_error(missing)

        image_asset_id = payload.get("image_asset_id")
        declares_image = self._as_bool(payload.get("declares_image"), default=image_asset_id is not None)
        return self.api.handle(
            method="POST",
            path="/checks/submit",
            payload={
                "content_variant_id": payload["content_variant_id"],
                "image_asset_id": image_asset_id,
                "declares_image": declares_image,
                "topic_id": payload.get("topic_id"),
                "platform": payload.get("platform"),
            },
        )

    def _content_mark_modified(self, payload: JsonDict) -> JsonDict:
        missing = self._missing_fields(payload, "content_variant_id")
        if missing:
            return self._missing_field_error(missing)
        return self.api.handle(
            method="POST",
            path=f"/contents/{payload['content_variant_id']}/mark-modified",
            payload={
                "title": payload.get("title"),
                "body": payload.get("body"),
                "style_profile": payload.get("style_profile"),
            },
        )

    def _image_mark_modified(self, payload: JsonDict) -> JsonDict:
        missing = self._missing_fields(payload, "image_asset_id")
        if missing:
            return self._missing_field_error(missing)
        return self.api.handle(
            method="POST",
            path=f"/images/{payload['image_asset_id']}/mark-modified",
            payload={
                "storage_path": payload.get("storage_path"),
                "prompt_snapshot": payload.get("prompt_snapshot"),
                "template_id": payload.get("template_id"),
                "width": payload.get("width"),
                "height": payload.get("height"),
            },
        )

    def _check_recheck(self, payload: JsonDict) -> JsonDict:
        missing = self._missing_fields(payload, "check_id")
        if missing:
            return self._missing_field_error(missing)

        current = self.api.handle(method="GET", path=f"/checks/{payload['check_id']}")
        if not current.get("ok"):
            return current

        check = current["data"]["check"]
        return self.api.handle(
            method="POST",
            path="/checks/submit",
            payload={
                "content_variant_id": check["content_variant_id"],
                "image_asset_id": check.get("image_asset_id"),
                "declares_image": check.get("image_asset_id") is not None,
                "topic_id": check.get("topic_id"),
                "platform": check.get("platform"),
            },
        )

    def _check_rollback(self, payload: JsonDict) -> JsonDict:
        missing = self._missing_fields(payload, "check_id")
        if missing:
            return self._missing_field_error(missing)

        detail = self.api.handle(method="GET", path=f"/checks/{payload['check_id']}")
        if not detail.get("ok"):
            return detail

        check = detail["data"]["check"]
        result = check["result"]
        if result != "BLOCK":
            return success_response(
                {
                    "check_id": check["id"],
                    "check_result": result,
                    "requires_rework": False,
                    "rollback_route": "/checks",
                    "content_variant_id": check.get("content_variant_id"),
                    "image_asset_id": check.get("image_asset_id"),
                },
                message="当前检查不是拦截状态，无需强制回退。",
            )

        items = detail["data"]["items"]
        relation_block = any(
            item.get("rule_category") == "关联性" or "image" in str(item.get("rule_code", ""))
            for item in items
        )
        rollback_route = "/images" if relation_block else "/contents"
        return success_response(
            {
                "check_id": check["id"],
                "check_result": result,
                "requires_rework": True,
                "rollback_route": rollback_route,
                "content_variant_id": check.get("content_variant_id"),
                "image_asset_id": check.get("image_asset_id"),
            },
            message="拦截状态下必须回退修改，页面已提供回退路由。",
        )

    def _check_to_retro(self, payload: JsonDict) -> JsonDict:
        missing = self._missing_fields(payload, "check_id")
        if missing:
            return self._missing_field_error(missing)
        return self.api.handle(
            method="POST",
            path=f"/checks/{payload['check_id']}/advance-to-retro",
            payload={
                "publish_result_summary": payload.get("publish_result_summary", "来自发布检查页面的复盘记录"),
                "insight": payload.get("insight"),
                "next_action": payload.get("next_action"),
                "metrics_json": payload.get("metrics_json"),
            },
        )

    def _retro_create(self, payload: JsonDict) -> JsonDict:
        missing = self._missing_fields(payload, "publish_check_id")
        if missing:
            return self._missing_field_error(missing)
        return self.api.handle(
            method="POST",
            path="/retros",
            payload={
                "publish_check_id": payload["publish_check_id"],
                "publish_result_summary": payload.get("publish_result_summary", "来自复盘台动作创建"),
                "insight": payload.get("insight"),
                "next_action": payload.get("next_action"),
                "metrics_json": payload.get("metrics_json"),
            },
        )

    @staticmethod
    def _missing_fields(payload: JsonDict, *fields: str) -> list[str]:
        return [field for field in fields if payload.get(field) in (None, "")]

    @staticmethod
    def _missing_field_error(missing: list[str]) -> JsonDict:
        return error_response("BAD_REQUEST", f"Missing required fields: {', '.join(missing)}")

    @staticmethod
    def _as_bool(value: Any, *, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
        return bool(value)
