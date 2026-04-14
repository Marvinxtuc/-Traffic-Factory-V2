from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "release_check.py"
SPEC = importlib.util.spec_from_file_location("release_check", SCRIPT_PATH)
release_check = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(release_check)


class TestReleaseCheck(unittest.TestCase):
    def test_load_env_file_parses_required_release_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / "staging.env"
            env_path.write_text(
                "\n".join(
                    [
                        "TF_HOST=127.0.0.1",
                        "TF_PORT=8790",
                        "TF_DB_PATH=data/runtime/traffic_factory_staging.sqlite3",
                        "TF_LOG_LEVEL=DEBUG",
                        "TF_ACCESS_LOG=true",
                    ]
                ),
                encoding="utf-8",
            )

            payload = release_check.load_env_file(env_path)

        self.assertEqual(payload["TF_HOST"], "127.0.0.1")
        self.assertEqual(payload["TF_PORT"], "8790")
        self.assertEqual(payload["TF_DB_PATH"], "data/runtime/traffic_factory_staging.sqlite3")
        self.assertEqual(payload["TF_LOG_LEVEL"], "DEBUG")
        self.assertEqual(payload["TF_ACCESS_LOG"], "true")

    def test_run_release_check_reports_success_when_tests_env_and_smoke_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / "staging.env"
            env_path.write_text(
                "\n".join(
                    [
                        "TF_HOST=127.0.0.1",
                        "TF_PORT=8790",
                        "TF_DB_PATH=data/runtime/traffic_factory_staging.sqlite3",
                        "TF_LOG_LEVEL=DEBUG",
                        "TF_ACCESS_LOG=true",
                    ]
                ),
                encoding="utf-8",
            )

            smoke_result = {
                "ok": True,
                "base_url": "http://127.0.0.1:8790",
                "checks": [{"path": "/healthz", "ok": True, "status": 200}],
            }

            with mock.patch.object(release_check, "run_command", return_value={"ok": True, "exit_code": 0, "stdout": "", "stderr": ""}) as run_command_mock, \
                 mock.patch.object(release_check, "is_port_listening", return_value=True), \
                 mock.patch.object(release_check.smoke_test, "run_checks", return_value=smoke_result):
                result = release_check.run_release_check(env_path=env_path, base_url="http://127.0.0.1:8790")

        self.assertTrue(result["ok"])
        self.assertEqual(
            [item["name"] for item in result["checks"]],
            ["env_file", "git_status", "test_suite", "port_listening", "smoke"],
        )
        self.assertTrue(all(item["ok"] for item in result["checks"]))
        self.assertEqual(run_command_mock.call_count, 2)
        self.assertEqual(run_command_mock.call_args.kwargs["command"], release_check.TEST_COMMAND)

    def test_run_release_check_fails_when_required_env_key_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / "broken.env"
            env_path.write_text(
                "\n".join(
                    [
                        "TF_HOST=127.0.0.1",
                        "TF_PORT=8790",
                        "TF_DB_PATH=data/runtime/traffic_factory_staging.sqlite3",
                        "TF_LOG_LEVEL=DEBUG",
                    ]
                ),
                encoding="utf-8",
            )

            result = release_check.run_release_check(env_path=env_path, base_url="http://127.0.0.1:8790", run_tests=False)

        self.assertFalse(result["ok"])
        failed = [item for item in result["checks"] if not item["ok"]]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["name"], "env_file")
        self.assertIn("TF_ACCESS_LOG", failed[0]["error"])

    def test_run_release_check_fails_when_env_host_port_do_not_match_base_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / "staging.env"
            env_path.write_text(
                "\n".join(
                    [
                        "TF_HOST=127.0.0.1",
                        "TF_PORT=8790",
                        "TF_DB_PATH=data/runtime/traffic_factory_staging.sqlite3",
                        "TF_LOG_LEVEL=DEBUG",
                        "TF_ACCESS_LOG=true",
                    ]
                ),
                encoding="utf-8",
            )

            result = release_check.run_release_check(env_path=env_path, base_url="http://127.0.0.1:8792", run_tests=False)

        self.assertFalse(result["ok"])
        failed = [item for item in result["checks"] if not item["ok"]]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["name"], "env_file")
        self.assertIn("base_url", failed[0]["error"])

    def test_run_release_check_reports_failure_when_git_status_is_dirty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / "staging.env"
            log_path = Path(tmpdir) / "current-main.log"
            env_path.write_text(
                "\n".join(
                    [
                        "TF_HOST=127.0.0.1",
                        "TF_PORT=8790",
                        "TF_DB_PATH=data/runtime/traffic_factory_staging.sqlite3",
                        "TF_LOG_LEVEL=INFO",
                        "TF_ACCESS_LOG=false",
                    ]
                ),
                encoding="utf-8",
            )
            log_path.write_text(
                '{"event": "server_starting", "host": "127.0.0.1", "port": 8790, "db_path": "data/runtime/traffic_factory_staging.sqlite3", "log_level": "INFO", "access_log": false}\n',
                encoding="utf-8",
            )

            with mock.patch.object(release_check, "run_command") as run_command_mock, \
                 mock.patch.object(release_check, "is_port_listening", return_value=True), \
                 mock.patch.object(release_check.smoke_test, "run_checks", return_value={"ok": True, "checks": []}):
                run_command_mock.side_effect = [
                    {"ok": False, "exit_code": 1, "stdout": " M README.md\n", "stderr": ""},
                    {"ok": True, "exit_code": 0, "stdout": "OK", "stderr": ""},
                ]
                result = release_check.run_release_check(
                    env_path=env_path,
                    base_url="http://127.0.0.1:8790",
                    startup_log_path=log_path,
                )

        self.assertFalse(result["ok"])
        failed = [item for item in result["checks"] if not item["ok"]]
        self.assertEqual(failed[0]["name"], "git_status")
        self.assertIn("README.md", failed[0]["stdout"])

    def test_run_release_check_reports_failure_when_target_port_is_not_listening(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / "staging.env"
            log_path = Path(tmpdir) / "current-main.log"
            env_path.write_text(
                "\n".join(
                    [
                        "TF_HOST=127.0.0.1",
                        "TF_PORT=8790",
                        "TF_DB_PATH=data/runtime/traffic_factory_staging.sqlite3",
                        "TF_LOG_LEVEL=INFO",
                        "TF_ACCESS_LOG=false",
                    ]
                ),
                encoding="utf-8",
            )
            log_path.write_text(
                '{"event": "server_starting", "host": "127.0.0.1", "port": 8790, "db_path": "data/runtime/traffic_factory_staging.sqlite3", "log_level": "INFO", "access_log": false}\n',
                encoding="utf-8",
            )

            with mock.patch.object(release_check, "run_command") as run_command_mock, \
                 mock.patch.object(release_check, "is_port_listening", return_value=False), \
                 mock.patch.object(release_check.smoke_test, "run_checks", return_value={"ok": True, "checks": []}):
                run_command_mock.side_effect = [
                    {"ok": True, "exit_code": 0, "stdout": "", "stderr": ""},
                    {"ok": True, "exit_code": 0, "stdout": "OK", "stderr": ""},
                ]
                result = release_check.run_release_check(
                    env_path=env_path,
                    base_url="http://127.0.0.1:8790",
                    startup_log_path=log_path,
                )

        self.assertFalse(result["ok"])
        failed = [item for item in result["checks"] if not item["ok"]]
        self.assertEqual(failed[0]["name"], "port_listening")
        self.assertIn("127.0.0.1:8790", failed[0]["error"])

    def test_run_release_check_reports_failure_when_startup_log_mismatches_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / "staging.env"
            log_path = Path(tmpdir) / "current-main.log"
            env_path.write_text(
                "\n".join(
                    [
                        "TF_HOST=127.0.0.1",
                        "TF_PORT=8790",
                        "TF_DB_PATH=data/runtime/traffic_factory_staging.sqlite3",
                        "TF_LOG_LEVEL=INFO",
                        "TF_ACCESS_LOG=false",
                    ]
                ),
                encoding="utf-8",
            )
            log_path.write_text(
                '{"event": "server_starting", "host": "127.0.0.1", "port": 8790, "db_path": "data/runtime/other.sqlite3", "log_level": "INFO", "access_log": false}\n',
                encoding="utf-8",
            )

            with mock.patch.object(release_check, "run_command") as run_command_mock, \
                 mock.patch.object(release_check, "is_port_listening", return_value=True), \
                 mock.patch.object(release_check.smoke_test, "run_checks", return_value={"ok": True, "checks": []}):
                run_command_mock.side_effect = [
                    {"ok": True, "exit_code": 0, "stdout": "", "stderr": ""},
                    {"ok": True, "exit_code": 0, "stdout": "OK", "stderr": ""},
                ]
                result = release_check.run_release_check(
                    env_path=env_path,
                    base_url="http://127.0.0.1:8790",
                    startup_log_path=log_path,
                )

        self.assertFalse(result["ok"])
        failed = [item for item in result["checks"] if not item["ok"]]
        self.assertEqual(failed[0]["name"], "startup_log")
        self.assertIn("db_path", failed[0]["error"])

    def test_main_prints_json_and_uses_exit_code(self) -> None:
        payload = {"ok": True, "checks": []}
        with mock.patch.object(release_check, "run_release_check", return_value=payload), \
             mock.patch("sys.argv", ["release_check.py", "--env-file", "deploy/staging.env.example", "--base-url", "http://127.0.0.1:8790", "--startup-log", "logs/current-main.log"]), \
             mock.patch("builtins.print") as print_mock:
            with self.assertRaises(SystemExit) as ctx:
                release_check.main()

        self.assertEqual(ctx.exception.code, 0)
        printed = print_mock.call_args.args[0]
        self.assertEqual(json.loads(printed), payload)


if __name__ == "__main__":
    unittest.main()
