from __future__ import annotations

import errno
import json
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from app import main as app_main


class TestAppMainStartupGuards(unittest.TestCase):
    def test_format_server_bind_error_includes_port_conflict_hint_and_processes(self) -> None:
        exc = OSError(errno.EADDRINUSE, "Address already in use")

        with mock.patch.object(app_main, "_list_listening_processes", return_value=["Python 1234 user 10u IPv4 *:8787 (LISTEN)"]):
            message = app_main._format_server_bind_error("127.0.0.1", 8787, exc)

        self.assertIn("127.0.0.1:8787 已被占用", message)
        self.assertIn("当前占用该端口的监听进程", message)
        self.assertIn("Python 1234", message)
        self.assertIn("TF_PORT", message)

    def test_create_app_exposes_healthz_readyz_and_existing_routes(self) -> None:
        app = app_main.create_app(db_path=":memory:")
        client = TestClient(app)

        health = client.get("/healthz")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["ok"], True)

        ready = client.get("/readyz")
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json()["ok"], True)
        self.assertEqual(ready.json()["checks"]["db"], "ok")

        discovery = client.get("/discovery")
        self.assertEqual(discovery.status_code, 200)
        self.assertIn("text/html", discovery.headers["content-type"])

        signals = client.get("/api/signals")
        self.assertEqual(signals.status_code, 200)
        self.assertEqual(signals.json()["ok"], True)

    def test_load_runtime_settings_reads_env_and_normalizes_types(self) -> None:
        settings = app_main.load_runtime_settings(
            {
                "TF_HOST": "0.0.0.0",
                "TF_PORT": "8899",
                "TF_DB_PATH": "data/runtime/prod.sqlite3",
                "TF_LOG_LEVEL": "debug",
                "TF_ACCESS_LOG": "true",
            }
        )

        self.assertEqual(settings.host, "0.0.0.0")
        self.assertEqual(settings.port, 8899)
        self.assertEqual(str(settings.db_path), "data/runtime/prod.sqlite3")
        self.assertEqual(settings.log_level, "DEBUG")
        self.assertEqual(settings.access_log, True)

    def test_run_server_uses_uvicorn_with_fastapi_app(self) -> None:
        with mock.patch.object(app_main, "create_app", return_value=object()) as create_app_mock, \
             mock.patch.object(app_main, "configure_logging") as configure_logging_mock, \
             mock.patch.object(app_main.LOGGER, "info") as logger_info, \
             mock.patch.object(app_main.uvicorn, "run") as uvicorn_run:
            app_main.run_server(
                host="127.0.0.1",
                port=8787,
                db_path=":memory:",
                log_level="DEBUG",
                access_log=True,
            )

        create_app_mock.assert_called_once_with(db_path=":memory:")
        configure_logging_mock.assert_called_once_with("DEBUG")
        logger_info.assert_called_once()
        event = json.loads(logger_info.call_args.args[0])
        self.assertEqual(event["event"], "server_starting")
        self.assertEqual(event["host"], "127.0.0.1")
        self.assertEqual(event["port"], 8787)
        self.assertEqual(event["db_path"], ":memory:")
        self.assertEqual(event["log_level"], "DEBUG")
        self.assertEqual(event["access_log"], True)
        uvicorn_run.assert_called_once()
        call_args = uvicorn_run.call_args
        self.assertIs(call_args.args[0], create_app_mock.return_value)
        self.assertEqual(call_args.kwargs["host"], "127.0.0.1")
        self.assertEqual(call_args.kwargs["port"], 8787)
        self.assertEqual(call_args.kwargs["log_level"], "debug")
        self.assertEqual(call_args.kwargs["access_log"], True)

    def test_run_server_raises_friendly_message_when_host_is_not_bindable(self) -> None:
        bind_error = OSError(errno.EADDRNOTAVAIL, "Can't assign requested address")

        with mock.patch.object(app_main.LOGGER, "info"), mock.patch.object(app_main.uvicorn, "run", side_effect=bind_error):
            with self.assertRaises(SystemExit) as ctx:
                app_main.run_server(host="192.0.2.10", port=8787, db_path=":memory:")

        self.assertIn("本机不存在可绑定地址 192.0.2.10", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
