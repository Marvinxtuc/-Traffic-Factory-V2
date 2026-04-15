from __future__ import annotations

import os
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _can_bind_port(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


class TestRestartCurrentMainScript(unittest.TestCase):
    def test_restart_script_handles_repo_path_with_spaces(self) -> None:
        port = _pick_free_port()

        with tempfile.TemporaryDirectory(prefix="tf restart script ") as tmpdir:
            link_root = Path(tmpdir) / "repo with spaces"
            os.symlink(REPO_ROOT, link_root, target_is_directory=True)
            script_path = link_root / "scripts" / "restart_current_main.sh"

            env = os.environ.copy()
            env.pop("TF_PYTHON", None)
            env.pop("VIRTUAL_ENV", None)
            env["TF_HOST"] = "127.0.0.1"
            env["TF_PORT"] = str(port)
            # 让脚本在端口检查通过后于 mkdir 阶段可预期失败，
            # 避免真实启动服务导致残留进程。
            env["TF_DB_PATH"] = "/dev/null/traffic_factory_qa.sqlite3"

            result = subprocess.run(
                ["bash", str(script_path)],
                cwd=str(link_root),
                env=env,
                text=True,
                capture_output=True,
                timeout=20,
            )

        self.assertNotEqual(
            result.returncode,
            0,
            msg="测试需要脚本在受控条件下失败，以避免真实启动服务。",
        )
        self.assertIn(
            "/dev/null",
            result.stderr,
            msg=f"stderr={result.stderr}",
        )
        self.assertNotIn(
            "启动前端口检查失败",
            result.stderr,
            msg=f"脚本不应在端口检查阶段失败。stderr={result.stderr}",
        )
        self.assertTrue(
            _can_bind_port(port),
            msg=f"端口 {port} 在脚本执行后应可再次绑定，避免残留监听进程。",
        )


if __name__ == "__main__":
    unittest.main()
