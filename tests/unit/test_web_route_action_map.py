from __future__ import annotations

import unittest

from app.web.action_bridge import SUPPORTED_ACTIONS
from app.web.routes import ROUTE_INDEX


class TestWebRouteActionMap(unittest.TestCase):
    def test_each_page_route_has_expected_action_binding(self):
        expected = {
            "/discovery": {"discovery_to_topic"},
            "/topics": {"topic_to_content"},
            "/contents": {"content_to_image", "content_precheck", "content_mark_modified"},
            "/images": {"image_submit_check", "image_mark_modified"},
            "/checks": {"check_recheck", "check_rollback", "check_to_retro"},
            "/retros": {"retro_create"},
        }
        for route_path, expected_actions in expected.items():
            self.assertIn(route_path, ROUTE_INDEX)
            self.assertEqual(set(ROUTE_INDEX[route_path].actions), expected_actions)

    def test_route_actions_are_supported_by_bridge(self):
        supported = set(SUPPORTED_ACTIONS)
        for route in ROUTE_INDEX.values():
            for action in route.actions:
                self.assertIn(action, supported)
