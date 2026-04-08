from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WebRoute:
    path: str
    module_name: str
    page_title: str
    page_file: Path
    actions: tuple[str, ...] = ()


_PAGES_ROOT = Path(__file__).resolve().parent / "pages"

ROUTES: tuple[WebRoute, ...] = (
    WebRoute(
        "/discovery",
        "discovery",
        "发现台",
        _PAGES_ROOT / "discovery" / "index.html",
        actions=("discovery_to_topic",),
    ),
    WebRoute(
        "/topics",
        "topic_pool",
        "选题池",
        _PAGES_ROOT / "topic-pool" / "index.html",
        actions=("topic_to_content",),
    ),
    WebRoute(
        "/contents",
        "content_lab",
        "内容工坊",
        _PAGES_ROOT / "content-lab" / "index.html",
        actions=("content_to_image", "content_precheck", "content_mark_modified"),
    ),
    WebRoute(
        "/images",
        "image_lab",
        "图片工坊",
        _PAGES_ROOT / "image-lab" / "index.html",
        actions=("image_submit_check", "image_mark_modified"),
    ),
    WebRoute(
        "/checks",
        "quality_gate",
        "发布检查",
        _PAGES_ROOT / "quality-gate" / "index.html",
        actions=("check_recheck", "check_rollback", "check_to_retro"),
    ),
    WebRoute(
        "/retros",
        "retrospective",
        "复盘台",
        _PAGES_ROOT / "retrospective" / "index.html",
        actions=("retro_create",),
    ),
)


ROUTE_INDEX: dict[str, WebRoute] = {route.path: route for route in ROUTES}
