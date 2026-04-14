from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "current_main_smoke_test.py"
SPEC = importlib.util.spec_from_file_location("current_main_smoke_test", SCRIPT_PATH)
smoke = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(smoke)


class _FakeResponse:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self._payload = json.dumps(payload).encode("utf-8")
        self.status = status

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class TestCurrentMainSmokeTest(unittest.TestCase):
    def test_run_checks_reports_all_core_endpoints_healthy(self) -> None:
        payloads = {
            "http://127.0.0.1:8791/discovery": _FakeResponse({"html": True}),
            "http://127.0.0.1:8791/api/signals": _FakeResponse({"ok": True, "items": []}),
            "http://127.0.0.1:8791/api/topics": _FakeResponse({"ok": True, "items": []}),
        }

        def fake_urlopen(request, timeout=5):
            url = request.full_url if hasattr(request, "full_url") else request
            if url not in payloads:
                raise AssertionError(f"unexpected url: {url}")
            return payloads[url]

        with mock.patch.object(smoke.request, "urlopen", side_effect=fake_urlopen):
            result = smoke.run_checks("http://127.0.0.1:8791")

        self.assertTrue(result["ok"])
        self.assertEqual([item["path"] for item in result["checks"]], [
            "/discovery",
            "/api/signals",
            "/api/topics",
        ])
        self.assertTrue(all(item["ok"] for item in result["checks"]))

    def test_run_checks_marks_failure_when_api_returns_not_ok(self) -> None:
        payloads = {
            "http://127.0.0.1:8791/discovery": _FakeResponse({"html": True}),
            "http://127.0.0.1:8791/api/signals": _FakeResponse({"ok": False, "items": []}),
            "http://127.0.0.1:8791/api/topics": _FakeResponse({"ok": True, "items": []}),
        }

        def fake_urlopen(request, timeout=5):
            url = request.full_url if hasattr(request, "full_url") else request
            return payloads[url]

        with mock.patch.object(smoke.request, "urlopen", side_effect=fake_urlopen):
            result = smoke.run_checks("http://127.0.0.1:8791")

        self.assertFalse(result["ok"])
        failed = [item for item in result["checks"] if not item["ok"]]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["path"], "/api/signals")


if __name__ == "__main__":
    unittest.main()
