from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class TestWebPagesLinkage(unittest.TestCase):
    def test_pages_use_web_action_endpoint(self):
        pages = {
            "discovery": REPO_ROOT / "app" / "web" / "pages" / "discovery" / "index.html",
            "topic-pool": REPO_ROOT / "app" / "web" / "pages" / "topic-pool" / "index.html",
            "content-lab": REPO_ROOT / "app" / "web" / "pages" / "content-lab" / "index.html",
            "image-lab": REPO_ROOT / "app" / "web" / "pages" / "image-lab" / "index.html",
            "quality-gate": REPO_ROOT / "app" / "web" / "pages" / "quality-gate" / "index.html",
            "retrospective": REPO_ROOT / "app" / "web" / "pages" / "retrospective" / "index.html",
        }
        for page_name, page_path in pages.items():
            content = page_path.read_text(encoding="utf-8")
            self.assertIn("/web/actions/${action}", content, msg=f"{page_name} page has no action bridge call")

    def test_required_action_codes_are_present_in_pages(self):
        expected_actions = {
            "discovery_to_topic",
            "topic_to_content",
            "content_to_image",
            "content_precheck",
            "content_mark_modified",
            "image_submit_check",
            "image_mark_modified",
            "check_recheck",
            "check_rollback",
            "check_to_retro",
            "retro_create",
        }
        page_root = REPO_ROOT / "app" / "web" / "pages"
        bundled = "\n".join(path.read_text(encoding="utf-8") for path in page_root.rglob("index.html"))
        for action in expected_actions:
            self.assertIn(f'"{action}"', bundled)

    def test_quality_gate_page_contains_structured_status_fields(self):
        page = (REPO_ROOT / "app" / "web" / "pages" / "quality-gate" / "index.html").read_text(encoding="utf-8")
        self.assertIn("检查版本号", page)
        self.assertIn("记录状态", page)
        self.assertIn("风险说明（警告时必看）", page)
        self.assertIn("是否最新有效检查记录", page)
