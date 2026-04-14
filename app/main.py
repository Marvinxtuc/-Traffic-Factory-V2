from __future__ import annotations

import argparse
import errno
import json
import shutil
import subprocess
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.api.main import MinimalApiApplication
from app.web.action_bridge import WebActionBridge
from app.web.routes import ROUTE_INDEX


def _normalize_query(parsed_query: str) -> dict[str, str | list[str]]:
    normalized: dict[str, str | list[str]] = {}
    for key, values in parse_qs(parsed_query, keep_blank_values=False).items():
        normalized[key] = values[0] if len(values) == 1 else values
    return normalized


def _http_status_from_error(code: str | None) -> HTTPStatus:
    if code in {"ENTITY_NOT_FOUND", "ROUTE_NOT_FOUND", "ACTION_NOT_FOUND"}:
        return HTTPStatus.NOT_FOUND
    if code in {"BAD_REQUEST", "PRECHECK_FAILED"}:
        return HTTPStatus.BAD_REQUEST
    if code in {"GATE_BLOCKED", "CONSTRAINT_VIOLATION"}:
        return HTTPStatus.CONFLICT
    return HTTPStatus.INTERNAL_SERVER_ERROR


def _list_listening_processes(port: int) -> list[str]:
    if shutil.which("lsof") is None:
        return []

    try:
        completed = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError:
        return []

    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if len(lines) <= 1:
        return []
    return lines[1:]


def _format_server_bind_error(host: str, port: int, exc: OSError) -> str:
    if exc.errno == errno.EADDRINUSE:
        details = [f"无法启动 app.main：{host}:{port} 已被占用。"]
        listeners = _list_listening_processes(port)
        if listeners:
            details.append("当前占用该端口的监听进程：")
            details.extend(f"- {line}" for line in listeners[:5])
        details.append("请先停止占用进程，或改用 --port / TF_PORT 指定其他端口后重试。")
        return "\n".join(details)

    if exc.errno == errno.EACCES:
        return f"无法启动 app.main：没有权限绑定 {host}:{port}。请改用更高位端口或检查系统权限。"

    if exc.errno == errno.EADDRNOTAVAIL:
        return f"无法启动 app.main：本机不存在可绑定地址 {host}。请检查 --host / TF_HOST 设置。"

    return f"无法启动 app.main：绑定 {host}:{port} 失败（{exc}）。"


class TrafficFactoryRequestHandler(BaseHTTPRequestHandler):
    api_app: MinimalApiApplication
    action_bridge: WebActionBridge

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._serve_page("/discovery")
            return
        if parsed.path.startswith("/api/"):
            self._handle_api("GET")
            return
        self._serve_page(parsed.path)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handle_api("POST")
            return
        if parsed.path.startswith("/web/actions/"):
            action_code = parsed.path[len("/web/actions/") :].strip("/")
            payload = self._read_json_body()
            response = self.action_bridge.run(action_code, payload)
            self._send_json_response(response)
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": {"code": "ROUTE_NOT_FOUND", "message": "Not found"}})

    def _serve_page(self, path: str) -> None:
        route = ROUTE_INDEX.get(path)
        if route is None:
            self.send_error(HTTPStatus.NOT_FOUND, "Page not found")
            return
        try:
            content = route.page_file.read_text(encoding="utf-8")
        except OSError as exc:  # pragma: no cover - defensive guard
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Failed to read page: {exc}")
            return

        body = content.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_api(self, method: str) -> None:
        parsed = urlparse(self.path)
        api_path = parsed.path[len("/api") :] or "/"
        payload = self._read_json_body() if method == "POST" else {}
        query = _normalize_query(parsed.query)
        response = self.api_app.handle(method=method, path=api_path, payload=payload, query=query)
        self._send_json_response(response)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
        return {}

    def _send_json_response(self, payload: dict[str, Any]) -> None:
        if payload.get("ok"):
            self._send_json(HTTPStatus.OK, payload)
            return
        error_code = payload.get("error", {}).get("code")
        self._send_json(_http_status_from_error(error_code), payload)

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:  # pragma: no cover - keep output clean
        return


def _build_handler(*, db_path: str | Path | None = None) -> type[TrafficFactoryRequestHandler]:
    class _Handler(TrafficFactoryRequestHandler):
        api_app = MinimalApiApplication(db_path=db_path)
        action_bridge = WebActionBridge(db_path=db_path)

    return _Handler


def run_server(*, host: str = "127.0.0.1", port: int = 8787, db_path: str | Path | None = None) -> None:
    try:
        server = ThreadingHTTPServer((host, port), _build_handler(db_path=db_path))
    except OSError as exc:
        raise SystemExit(_format_server_bind_error(host, port, exc)) from exc
    print(f"Traffic Factory app running at http://{host}:{port}")
    print("Use /discovery /topics /contents /images /checks /retros for web pages.")
    print("Use /api/* and /web/actions/* for minimal API/Web action calls.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run minimal Traffic Factory app server.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8787, help="Bind port")
    parser.add_argument(
        "--db-path",
        default="data/runtime/traffic_factory.sqlite3",
        help="SQLite path for API and web actions",
    )
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, db_path=args.db_path)


if __name__ == "__main__":
    main()
