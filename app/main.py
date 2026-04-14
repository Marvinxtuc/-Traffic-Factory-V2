from __future__ import annotations

import argparse
import errno
import json
import logging
import os
import shutil
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.api.main import MinimalApiApplication
from app.web.action_bridge import WebActionBridge
from app.web.routes import ROUTE_INDEX
from scripts.init_db import initialize_database


LOGGER = logging.getLogger("traffic_factory.app")
VALID_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


@dataclass(frozen=True)
class RuntimeSettings:
    host: str = "127.0.0.1"
    port: int = 8787
    db_path: str | Path | None = "data/runtime/traffic_factory.sqlite3"
    log_level: str = "INFO"
    access_log: bool = False


def _coerce_port(raw: str | int) -> int:
    try:
        port = int(raw)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"TF_PORT/--port 需要是数字，当前为: {raw}") from exc
    if port < 1 or port > 65535:
        raise SystemExit(f"TF_PORT/--port 超出有效范围（1-65535），当前为: {port}")
    return port


def _parse_bool(raw: str | bool | None, *, default: bool = False) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise SystemExit(f"TF_ACCESS_LOG 需要是 true/false，当前为: {raw}")


def load_runtime_settings(environ: dict[str, str] | None = None) -> RuntimeSettings:
    environ = environ or os.environ
    host = environ.get("TF_HOST", "127.0.0.1")
    port = _coerce_port(environ.get("TF_PORT", "8787"))
    db_path = environ.get("TF_DB_PATH", "data/runtime/traffic_factory.sqlite3")
    log_level = environ.get("TF_LOG_LEVEL", "INFO").strip().upper()
    if log_level not in VALID_LOG_LEVELS:
        raise SystemExit(
            f"TF_LOG_LEVEL 必须是 {', '.join(sorted(VALID_LOG_LEVELS))} 之一，当前为: {log_level or '<empty>'}"
        )
    access_log = _parse_bool(environ.get("TF_ACCESS_LOG"), default=False)
    return RuntimeSettings(
        host=host,
        port=port,
        db_path=db_path,
        log_level=log_level,
        access_log=access_log,
    )


def configure_logging(log_level: str) -> None:
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO), format="%(message)s", force=True)


def _normalize_query(request: Request) -> dict[str, str | list[str]]:
    normalized: dict[str, str | list[str]] = {}
    for key in request.query_params:
        values = request.query_params.getlist(key)
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


def _json_response(payload: dict[str, Any]) -> JSONResponse:
    if payload.get("ok"):
        return JSONResponse(status_code=int(HTTPStatus.OK), content=payload)
    error_code = payload.get("error", {}).get("code")
    return JSONResponse(status_code=int(_http_status_from_error(error_code)), content=payload)


def _prepare_db_path(db_path: str | Path | None) -> str | Path | None:
    if db_path is None:
        return None
    if db_path == ":memory:":
        handle = tempfile.NamedTemporaryFile(prefix="traffic_factory_app_", suffix=".sqlite3", delete=False)
        handle.close()
        initialize_database(Path(handle.name))
        return handle.name

    path = Path(db_path)
    initialize_database(path)
    return path


def _check_db_ready(db_path: str | Path | None) -> tuple[str, str | None]:
    if db_path is None:
        return "ok", None
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute("SELECT 1")
    except sqlite3.Error as exc:
        return "error", str(exc)
    return "ok", None


def create_app(*, db_path: str | Path | None = None) -> FastAPI:
    effective_db_path = _prepare_db_path(db_path)
    api_app = MinimalApiApplication(db_path=effective_db_path)
    action_bridge = WebActionBridge(db_path=effective_db_path)
    app = FastAPI(title="Traffic Factory Current Main", version="0.1.0")

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/discovery", status_code=int(HTTPStatus.TEMPORARY_REDIRECT))

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {"ok": True, "service": "traffic-factory", "status": "healthy"}

    @app.get("/readyz")
    async def readyz() -> JSONResponse:
        db_status, db_error = _check_db_ready(db_path)
        payload: dict[str, Any] = {"ok": db_status == "ok", "checks": {"db": db_status}}
        if db_error:
            payload["checks"]["db_error"] = db_error
        status = HTTPStatus.OK if payload["ok"] else HTTPStatus.SERVICE_UNAVAILABLE
        return JSONResponse(status_code=int(status), content=payload)

    @app.api_route("/api/{api_path:path}", methods=["GET", "POST"])
    async def api_entry(api_path: str, request: Request) -> JSONResponse:
        payload = {}
        if request.method != "GET":
            try:
                body = await request.json()
            except Exception:
                body = {}
            payload = body if isinstance(body, dict) else {}
        response = api_app.handle(
            method=request.method,
            path=f"/{api_path}" if api_path else "/",
            payload=payload,
            query=_normalize_query(request),
        )
        return _json_response(response)

    @app.post("/web/actions/{action_code}")
    async def web_action(action_code: str, request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            body = {}
        payload = body if isinstance(body, dict) else {}
        response = action_bridge.run(action_code, payload)
        return _json_response(response)

    @app.get("/{page_path:path}", include_in_schema=False)
    async def page(page_path: str) -> HTMLResponse:
        normalized_path = "/" + page_path.strip("/") if page_path else "/discovery"
        route = ROUTE_INDEX.get(normalized_path)
        if route is None:
            return HTMLResponse(status_code=int(HTTPStatus.NOT_FOUND), content="Page not found")
        try:
            content = route.page_file.read_text(encoding="utf-8")
        except OSError as exc:
            return HTMLResponse(status_code=int(HTTPStatus.INTERNAL_SERVER_ERROR), content=f"Failed to read page: {exc}")
        return HTMLResponse(status_code=int(HTTPStatus.OK), content=content)

    return app


def run_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8787,
    db_path: str | Path | None = None,
    log_level: str = "INFO",
    access_log: bool = False,
) -> None:
    configure_logging(log_level)
    app = create_app(db_path=db_path)
    LOGGER.info(
        json.dumps(
            {
                "event": "server_starting",
                "host": host,
                "port": port,
                "db_path": str(db_path) if db_path is not None else None,
                "log_level": log_level,
                "access_log": access_log,
            },
            ensure_ascii=False,
        )
    )
    try:
        uvicorn.run(app, host=host, port=port, log_level=log_level.lower(), access_log=access_log)
    except OSError as exc:
        raise SystemExit(_format_server_bind_error(host, port, exc)) from exc


def main() -> None:
    settings = load_runtime_settings()
    parser = argparse.ArgumentParser(description="Run Traffic Factory current main ASGI server.")
    parser.add_argument("--host", default=settings.host, help="Bind host")
    parser.add_argument("--port", type=int, default=settings.port, help="Bind port")
    parser.add_argument(
        "--db-path",
        default=settings.db_path,
        help="SQLite path for API and web actions",
    )
    parser.add_argument(
        "--log-level",
        default=settings.log_level,
        choices=sorted(VALID_LOG_LEVELS),
        help="Application and Uvicorn log level",
    )
    parser.add_argument(
        "--access-log",
        dest="access_log",
        action="store_true",
        default=settings.access_log,
        help="Enable Uvicorn access logs",
    )
    parser.add_argument(
        "--no-access-log",
        dest="access_log",
        action="store_false",
        help="Disable Uvicorn access logs",
    )
    args = parser.parse_args()
    run_server(
        host=args.host,
        port=args.port,
        db_path=args.db_path,
        log_level=args.log_level,
        access_log=args.access_log,
    )


if __name__ == "__main__":
    main()
