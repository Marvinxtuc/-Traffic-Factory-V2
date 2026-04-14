from __future__ import annotations

import errno
import unittest
from unittest import mock

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

    def test_run_server_raises_friendly_message_when_host_is_not_bindable(self) -> None:
        bind_error = OSError(errno.EADDRNOTAVAIL, "Can't assign requested address")

        with mock.patch.object(app_main, "ThreadingHTTPServer", side_effect=bind_error):
            with self.assertRaises(SystemExit) as ctx:
                app_main.run_server(host="192.0.2.10", port=8787, db_path=":memory:")

        self.assertIn("本机不存在可绑定地址 192.0.2.10", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
