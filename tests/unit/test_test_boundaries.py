from __future__ import annotations

from services.discovery_service import DiscoveryService
from tests.support import IsolatedTestCase, REPO_ROOT


class TestTestBoundaries(IsolatedTestCase):
    def test_default_service_database_comes_from_injected_test_path(self):
        service = DiscoveryService()

        self.assertEqual(service.repository.db_path, self.db_path)
        self.assertIn(self.temp_root, service.repository.db_path.parents)

    def test_runtime_database_access_is_blocked(self):
        service = DiscoveryService(db_path=REPO_ROOT / "data" / "runtime" / "traffic_factory.sqlite3")

        with self.assertRaisesRegex(AssertionError, "SQLite access outside the injected test temp directory"):
            service.create_signal(source_type="manual", title="should-fail")

    def test_runtime_and_artifact_reads_are_blocked(self):
        with self.assertRaisesRegex(AssertionError, "Protected path access is forbidden during tests"):
            (REPO_ROOT / "runtime" / ".gitkeep").read_text(encoding="utf-8")

        with self.assertRaisesRegex(AssertionError, "Protected path access is forbidden during tests"):
            (REPO_ROOT / "reports" / ".gitkeep").read_text(encoding="utf-8")

        with self.assertRaisesRegex(AssertionError, "Protected path access is forbidden during tests"):
            (REPO_ROOT / "artifacts" / ".gitkeep").read_text(encoding="utf-8")

        with self.assertRaisesRegex(AssertionError, "Protected path access is forbidden during tests"):
            (REPO_ROOT / "data" / "runtime" / ".gitkeep").read_text(encoding="utf-8")

    def test_runtime_report_and_artifact_writes_are_blocked(self):
        with self.assertRaisesRegex(AssertionError, "Protected path access is forbidden during tests"):
            (REPO_ROOT / "runtime" / "forbidden.txt").write_text("blocked", encoding="utf-8")

        with self.assertRaisesRegex(AssertionError, "Protected path access is forbidden during tests"):
            (REPO_ROOT / "reports" / "forbidden.txt").write_text("blocked", encoding="utf-8")

        with self.assertRaisesRegex(AssertionError, "Protected path access is forbidden during tests"):
            (REPO_ROOT / "artifacts" / "forbidden.txt").write_text("blocked", encoding="utf-8")

        with self.assertRaisesRegex(AssertionError, "Protected path access is forbidden during tests"):
            (REPO_ROOT / "data" / "runtime" / "forbidden.txt").write_text("blocked", encoding="utf-8")
