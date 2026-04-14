from __future__ import annotations

import argparse
import importlib.util
import json
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ENV_KEYS = (
    "TF_HOST",
    "TF_PORT",
    "TF_DB_PATH",
    "TF_LOG_LEVEL",
    "TF_ACCESS_LOG",
)
TEST_DISCOVER_ARGS = "-m unittest discover -s tests -p 'test_*.py'"
GIT_STATUS_COMMAND = "git status --short"

_SMOKE_PATH = Path(__file__).resolve().parent / "current_main_smoke_test.py"
_SMOKE_SPEC = importlib.util.spec_from_file_location("current_main_smoke_test", _SMOKE_PATH)
smoke_test = importlib.util.module_from_spec(_SMOKE_SPEC)
assert _SMOKE_SPEC is not None and _SMOKE_SPEC.loader is not None
_SMOKE_SPEC.loader.exec_module(smoke_test)


def load_env_file(path: str | Path) -> dict[str, str]:
    env_path = Path(path)
    payload: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        payload[key.strip()] = value.strip()
    return payload


def run_command(*, command: str, workdir: str | Path) -> dict[str, Any]:
    completed = subprocess.run(command, shell=True, cwd=str(workdir), text=True, capture_output=True, check=False)
    return {
        "ok": completed.returncode == 0,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def get_test_command() -> str:
    venv_python = REPO_ROOT / ".venv" / "bin" / "python"
    if venv_python.exists():
        return f'"{venv_python}" {TEST_DISCOVER_ARGS}'
    return f'"{sys.executable}" {TEST_DISCOVER_ARGS}'


def _check_env_file(env_path: str | Path, *, base_url: str) -> dict[str, Any]:
    try:
        payload = load_env_file(env_path)
    except Exception as exc:
        return {"name": "env_file", "ok": False, "error": str(exc)}

    missing = [key for key in REQUIRED_ENV_KEYS if key not in payload]
    if missing:
        return {"name": "env_file", "ok": False, "error": f"missing required keys: {', '.join(missing)}"}
    parsed = urlparse(base_url)
    expected_host = parsed.hostname or ""
    expected_port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if payload["TF_HOST"] != expected_host or payload["TF_PORT"] != str(expected_port):
        return {
            "name": "env_file",
            "ok": False,
            "error": (
                "env file does not match base_url: "
                f"TF_HOST={payload['TF_HOST']} TF_PORT={payload['TF_PORT']} vs {base_url}"
            ),
        }
    return {"name": "env_file", "ok": True, "env": payload}


def _check_git_status() -> dict[str, Any]:
    result = run_command(command=GIT_STATUS_COMMAND, workdir=REPO_ROOT)
    is_clean = result["ok"] and not result["stdout"].strip()
    return {
        "name": "git_status",
        **result,
        "ok": is_clean,
        "error": None if is_clean else "git working tree is not clean",
    }


def _check_test_suite() -> dict[str, Any]:
    result = run_command(command=get_test_command(), workdir=REPO_ROOT)
    return {"name": "test_suite", **result}


def _parse_base_url(base_url: str) -> tuple[str, int]:
    parsed = urlparse(base_url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return host, port


def is_port_listening(host: str, port: int, timeout_seconds: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def _check_port_listening(base_url: str) -> dict[str, Any]:
    host, port = _parse_base_url(base_url)
    is_listening = is_port_listening(host, port)
    return {
        "name": "port_listening",
        "ok": is_listening,
        "host": host,
        "port": port,
        "error": None if is_listening else f"target port is not listening: {host}:{port}",
    }


def _coerce_access_log(raw_value: str) -> bool:
    return raw_value.strip().lower() == "true"


def _load_startup_event(log_path: str | Path) -> dict[str, Any]:
    lines = Path(log_path).read_text(encoding="utf-8").splitlines()
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("event") == "server_starting":
            return payload
    raise ValueError("startup log does not contain a valid server_starting JSON event")


def _check_startup_log(startup_log_path: str | Path, *, env_payload: dict[str, str], base_url: str) -> dict[str, Any]:
    host, port = _parse_base_url(base_url)
    expected = {
        "host": env_payload["TF_HOST"],
        "port": int(env_payload["TF_PORT"]),
        "db_path": env_payload["TF_DB_PATH"],
        "log_level": env_payload["TF_LOG_LEVEL"],
        "access_log": _coerce_access_log(env_payload["TF_ACCESS_LOG"]),
    }
    if expected["host"] != host or expected["port"] != port:
        return {
            "name": "startup_log",
            "ok": False,
            "log_path": str(startup_log_path),
            "error": "env payload does not match base_url for startup log validation",
        }

    try:
        event = _load_startup_event(startup_log_path)
    except Exception as exc:
        return {"name": "startup_log", "ok": False, "log_path": str(startup_log_path), "error": str(exc)}

    mismatches = []
    for key, expected_value in expected.items():
        if event.get(key) != expected_value:
            mismatches.append(f"{key}: expected {expected_value!r}, got {event.get(key)!r}")

    return {
        "name": "startup_log",
        "ok": not mismatches,
        "log_path": str(startup_log_path),
        "event": event,
        "error": None if not mismatches else "; ".join(mismatches),
    }


def _check_smoke(base_url: str) -> dict[str, Any]:
    result = smoke_test.run_checks(base_url)
    return {"name": "smoke", **result}


def run_release_check(
    *, env_path: str | Path, base_url: str, startup_log_path: str | Path | None = None, run_tests: bool = True
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    env_check = _check_env_file(env_path, base_url=base_url)
    checks.append(env_check)

    if env_check["ok"]:
        checks.append(_check_git_status())
        if run_tests:
            checks.append(_check_test_suite())
        port_check = _check_port_listening(base_url)
        checks.append(port_check)
        if startup_log_path is not None:
            checks.append(_check_startup_log(startup_log_path, env_payload=env_check["env"], base_url=base_url))
        if port_check["ok"]:
            checks.append(_check_smoke(base_url))

    return {
        "ok": all(item.get("ok") is True for item in checks),
        "env_path": str(env_path),
        "base_url": base_url,
        "startup_log_path": None if startup_log_path is None else str(startup_log_path),
        "checks": checks,
        "known_limits": "docs/current-main-known-limits.md",
        "rollback_guide": "docs/current-main-operations.md",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Automate the current-main release checklist.")
    parser.add_argument("--env-file", required=True, help="Path to staging/prod env template or target env file")
    parser.add_argument("--base-url", required=True, help="Base URL of the running current-main instance")
    parser.add_argument("--startup-log", required=True, help="Path to startup log file containing server_starting JSON")
    parser.add_argument("--skip-tests", action="store_true", help="Skip the full unittest suite")
    args = parser.parse_args()
    result = run_release_check(
        env_path=args.env_file,
        base_url=args.base_url,
        startup_log_path=args.startup_log,
        run_tests=not args.skip_tests,
    )
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
