#!/usr/bin/env python3
"""V1 runtime smoke test.

Default mode does not start server.
Start server first:
  python3 -m uvicorn v1.app:app --host 127.0.0.1 --port 8788

Optional isolation mode:
  --use-temp-db will run against an in-process app bound to a temporary SQLite DB.
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

SMOKE_SOURCE_NAME = "smoke_test"
SMOKE_TAG = "runtime_smoke"
SMOKE_TOPIC_PREFIX = "[SMOKE_TEST]"
SMOKE_ANGLE_MARK = "__runtime_smoke__"
SMOKE_PLATFORM_MARK = "runtime_smoke"
SMOKE_INPUT_MARKER_KEY = "runtime_smoke"

DEFAULT_DB_PATH = Path("data/runtime/traffic_factory_v1.sqlite3")


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str = ""


class Transport:
    def request(self, method: str, path: str, *, json_payload: dict[str, Any] | None = None) -> Any:
        raise NotImplementedError

    def close(self) -> None:
        return None


class HttpTransport(Transport):
    def __init__(self, base_url: str, timeout: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def request(self, method: str, path: str, *, json_payload: dict[str, Any] | None = None) -> requests.Response:
        return self.session.request(
            method=method,
            url=f"{self.base_url}{path}",
            json=json_payload,
            timeout=self.timeout,
        )

    def close(self) -> None:
        self.session.close()


class InProcessTransport(Transport):
    def __init__(self, db_path: Path) -> None:
        os.environ["TF_V1_DB_PATH"] = str(db_path)
        from fastapi.testclient import TestClient
        from v1.app import app

        self._context = TestClient(app)
        self.client = self._context.__enter__()

    def request(self, method: str, path: str, *, json_payload: dict[str, Any] | None = None) -> Any:
        return self.client.request(method=method, url=path, json=json_payload)

    def close(self) -> None:
        self._context.__exit__(None, None, None)


def fail(step: str, detail: str) -> StepResult:
    return StepResult(name=step, ok=False, detail=detail)


def ok(step: str, detail: str = "") -> StepResult:
    return StepResult(name=step, ok=True, detail=detail)


def sql_in_clause(column: str, values: list[int]) -> tuple[str, tuple[Any, ...]]:
    placeholders = ", ".join(["?"] * len(values))
    return f"{column} IN ({placeholders})", tuple(values)


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def cleanup_smoke_data(db_path: Path) -> dict[str, int]:
    if not db_path.exists():
        return {
            "content_versions_deleted": 0,
            "content_jobs_deleted": 0,
            "topic_pool_deleted": 0,
            "trend_signals_deleted": 0,
        }

    counts = {
        "content_versions_deleted": 0,
        "content_jobs_deleted": 0,
        "topic_pool_deleted": 0,
        "trend_signals_deleted": 0,
    }

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        if not table_exists(conn, "trend_signals"):
            return counts
        if not table_exists(conn, "topic_pool"):
            return counts
        if not table_exists(conn, "content_jobs"):
            return counts

        signal_rows = conn.execute(
            """
            SELECT id
            FROM trend_signals
            WHERE source_name = ?
               OR tags_json LIKE ?
            """,
            (SMOKE_SOURCE_NAME, f"%{SMOKE_TAG}%"),
        ).fetchall()
        signal_ids = [int(row[0]) for row in signal_rows]

        topic_ids: list[int] = []
        if signal_ids:
            where_sql, where_params = sql_in_clause("signal_id", signal_ids)
            topic_rows = conn.execute(
                f"""
                SELECT id
                FROM topic_pool
                WHERE {where_sql}
                   OR angle = ?
                   OR topic_title LIKE ?
                   OR target_platform LIKE ?
                """,
                (*where_params, SMOKE_ANGLE_MARK, f"{SMOKE_TOPIC_PREFIX}%", f"%{SMOKE_PLATFORM_MARK}%"),
            ).fetchall()
            topic_ids = [int(row[0]) for row in topic_rows]
        else:
            topic_rows = conn.execute(
                """
                SELECT id
                FROM topic_pool
                WHERE angle = ?
                   OR topic_title LIKE ?
                   OR target_platform LIKE ?
                """,
                (SMOKE_ANGLE_MARK, f"{SMOKE_TOPIC_PREFIX}%", f"%{SMOKE_PLATFORM_MARK}%"),
            ).fetchall()
            topic_ids = [int(row[0]) for row in topic_rows]

        if table_exists(conn, "content_versions"):
            if topic_ids:
                where_sql, where_params = sql_in_clause("topic_id", topic_ids)
                cur = conn.execute(
                    f"""
                    DELETE FROM content_versions
                    WHERE {where_sql}
                       OR meta_json LIKE ?
                    """,
                    (*where_params, f"%{SMOKE_TAG}%"),
                )
            else:
                cur = conn.execute(
                    "DELETE FROM content_versions WHERE meta_json LIKE ?",
                    (f"%{SMOKE_TAG}%",),
                )
            counts["content_versions_deleted"] = int(cur.rowcount or 0)

        if topic_ids:
            where_sql, where_params = sql_in_clause("topic_id", topic_ids)
            cur = conn.execute(
                f"""
                DELETE FROM content_jobs
                WHERE {where_sql}
                   OR input_payload_json LIKE ?
                """,
                (*where_params, f"%{SMOKE_INPUT_MARKER_KEY}%"),
            )
        else:
            cur = conn.execute(
                "DELETE FROM content_jobs WHERE input_payload_json LIKE ?",
                (f"%{SMOKE_INPUT_MARKER_KEY}%",),
            )
        counts["content_jobs_deleted"] = int(cur.rowcount or 0)

        if topic_ids:
            where_sql, where_params = sql_in_clause("id", topic_ids)
            cur = conn.execute(f"DELETE FROM topic_pool WHERE {where_sql}", where_params)
            counts["topic_pool_deleted"] = int(cur.rowcount or 0)

        if signal_ids:
            where_sql, where_params = sql_in_clause("id", signal_ids)
            cur = conn.execute(f"DELETE FROM trend_signals WHERE {where_sql}", where_params)
            counts["trend_signals_deleted"] = int(cur.rowcount or 0)

        conn.commit()

    return counts


def resolve_db_path(raw_db_path: str | None, use_temp_db: bool) -> tuple[Path, Path | None]:
    if use_temp_db:
        temp_dir = Path(tempfile.mkdtemp(prefix="tf_v1_smoke_"))
        return temp_dir / "traffic_factory_v1_smoke.sqlite3", temp_dir

    if raw_db_path:
        return Path(raw_db_path), None

    env_db_path = os.environ.get("TF_V1_DB_PATH")
    if env_db_path:
        return Path(env_db_path), None

    return DEFAULT_DB_PATH, None


def assert_page_quality(path: str, body: str) -> str | None:
    lowered = body.lower()
    if "<html" not in lowered:
        return f"{path} 响应不是 HTML"
    if re.search(r">\s*undefined\s*<", lowered):
        return f"{path} 出现 undefined"
    if re.search(r">\s*null\s*<", lowered):
        return f"{path} 出现 null 字符串渲染"
    if "internal server error" in lowered or "traceback" in lowered:
        return f"{path} 疑似错误页"
    return None


def run_smoke(transport: Transport) -> tuple[int, list[StepResult]]:
    results: list[StepResult] = []

    try:
        health = transport.request("GET", "/health")
    except requests.RequestException as exc:
        print(f"[FAIL] 无法连接服务: {exc}")
        print("请先启动服务: python3 -m uvicorn v1.app:app --host 127.0.0.1 --port 8788")
        return 1, results

    if health.status_code != 200:
        results.append(fail("GET /health", f"状态码 {health.status_code}"))
    else:
        results.append(ok("GET /health", "状态码 200"))

    page_checks = [
        ("/web/discovery", "data-i18n=\"NAV.DISCOVERY\""),
        ("/web/topics", "data-i18n=\"NAV.TOPICS\""),
        ("/web/content", "data-i18n=\"NAV.CONTENT\""),
    ]

    for path, expected_key in page_checks:
        step = f"GET {path}"
        try:
            resp = transport.request("GET", path)
        except requests.RequestException as exc:
            results.append(fail(step, f"请求异常: {exc}"))
            continue

        if resp.status_code != 200:
            results.append(fail(step, f"状态码 {resp.status_code}"))
            continue

        body = resp.text
        if not body.strip():
            results.append(fail(step, "响应为空"))
            continue

        quality_error = assert_page_quality(path, body)
        if quality_error:
            results.append(fail(step, quality_error))
            continue

        if "/web/assets/i18n_zh.js" not in body:
            results.append(fail(step, "未接入 i18n_zh.js"))
            continue

        if expected_key not in body:
            results.append(fail(step, f"缺少关键 i18n 锚点: {expected_key}"))
            continue

        results.append(ok(step, "页面可访问且结构正常"))

    try:
        i18n_resp = transport.request("GET", "/web/assets/i18n_zh.js")
        if i18n_resp.status_code != 200:
            results.append(fail("GET /web/assets/i18n_zh.js", f"状态码 {i18n_resp.status_code}"))
        else:
            i18n_body = i18n_resp.text
            required_cn_terms = ["发现台", "选题池", "内容工坊", "转入选题", "执行生成"]
            missing_terms = [term for term in required_cn_terms if term not in i18n_body]
            if missing_terms:
                results.append(fail("i18n 中文文案检查", f"缺失术语: {', '.join(missing_terms)}"))
            else:
                results.append(ok("i18n 中文文案检查", "关键中文术语齐全"))
    except requests.RequestException as exc:
        results.append(fail("GET /web/assets/i18n_zh.js", f"请求异常: {exc}"))

    signal_id: int | None = None
    topic_id: int | None = None

    try:
        manual_payload = {
            "source_name": SMOKE_SOURCE_NAME,
            "title": f"运行态验证信号-{int(time.time())}",
            "summary": "运行态验证自动插入",
            "content_raw": "用于回归测试的手动信号",
            "lang": "zh",
            "tags": [SMOKE_TAG],
        }
        signal_resp = transport.request("POST", "/signals/manual", json_payload=manual_payload)
        if signal_resp.status_code != 200:
            results.append(fail("POST /signals/manual", f"状态码 {signal_resp.status_code}, body={signal_resp.text[:200]}"))
        else:
            signal_data = signal_resp.json()
            signal = signal_data.get("signal") or {}
            signal_id = signal.get("id")
            if not isinstance(signal_id, int):
                results.append(fail("POST /signals/manual", "响应缺少 signal.id"))
            else:
                results.append(ok("POST /signals/manual", f"signal_id={signal_id}"))
    except requests.RequestException as exc:
        results.append(fail("POST /signals/manual", f"请求异常: {exc}"))

    if signal_id is not None:
        try:
            topic_payload = {
                "topic_title": f"{SMOKE_TOPIC_PREFIX} 信号-{signal_id}",
                "angle": SMOKE_ANGLE_MARK,
                "target_platform": SMOKE_PLATFORM_MARK,
                "commercial_value": 0.0,
            }
            topic_resp = transport.request("POST", f"/topics/from-signal/{signal_id}", json_payload=topic_payload)
            if topic_resp.status_code != 200:
                results.append(fail("POST /topics/from-signal/{id}", f"状态码 {topic_resp.status_code}, body={topic_resp.text[:200]}"))
            else:
                topic_data = topic_resp.json()
                topic = topic_data.get("topic") or {}
                topic_id = topic.get("id")
                if not isinstance(topic_id, int):
                    results.append(fail("POST /topics/from-signal/{id}", "响应缺少 topic.id"))
                else:
                    results.append(ok("POST /topics/from-signal/{id}", f"topic_id={topic_id}"))
        except requests.RequestException as exc:
            results.append(fail("POST /topics/from-signal/{id}", f"请求异常: {exc}"))

    if topic_id is not None:
        try:
            content_payload = {
                "topic_id": topic_id,
                "content_type": "wechat_article",
                "input_payload": {
                    "tone": "科普",
                    SMOKE_INPUT_MARKER_KEY: True,
                },
            }
            content_resp = transport.request("POST", "/content/generate", json_payload=content_payload)
            if content_resp.status_code != 200:
                results.append(fail("POST /content/generate", f"状态码 {content_resp.status_code}, body={content_resp.text[:200]}"))
            else:
                data = content_resp.json()
                headline = ((data.get("result") or {}).get("headline") or "").strip()
                if not headline:
                    results.append(fail("POST /content/generate", "响应缺少 result.headline"))
                else:
                    results.append(ok("POST /content/generate", f"headline={headline}"))
        except requests.RequestException as exc:
            results.append(fail("POST /content/generate", f"请求异常: {exc}"))

    failed = [item for item in results if not item.ok]
    for item in results:
        prefix = "PASS" if item.ok else "FAIL"
        detail = f" - {item.detail}" if item.detail else ""
        print(f"[{prefix}] {item.name}{detail}")

    if failed:
        print("运行态验证失败")
        return 1, results

    print("运行态验证通过")
    return 0, results


def main() -> int:
    parser = argparse.ArgumentParser(description="V1 运行态最小回归验证")
    parser.add_argument("--base-url", default="http://127.0.0.1:8788", help="服务地址，默认 http://127.0.0.1:8788")
    parser.add_argument("--db-path", default=None, help="清理模式使用的数据库路径，默认读取 TF_V1_DB_PATH 或 data/runtime/traffic_factory_v1.sqlite3")
    parser.add_argument("--cleanup", action="store_true", help="测试结束后清理所有 smoke 标记数据")
    parser.add_argument("--use-temp-db", action="store_true", help="使用临时 SQLite 数据库并在结束后自动删除")
    args = parser.parse_args()

    db_path, temp_dir = resolve_db_path(args.db_path, args.use_temp_db)

    transport: Transport
    if args.use_temp_db:
        transport = InProcessTransport(db_path)
    else:
        transport = HttpTransport(args.base_url)

    exit_code = 1
    try:
        exit_code, _ = run_smoke(transport)
    finally:
        transport.close()

        if args.cleanup:
            counts = cleanup_smoke_data(db_path)
            print(
                "cleanup 完成: "
                f"content_versions={counts['content_versions_deleted']}, "
                f"content_jobs={counts['content_jobs_deleted']}, "
                f"topic_pool={counts['topic_pool_deleted']}, "
                f"trend_signals={counts['trend_signals_deleted']}"
            )

        if temp_dir is not None:
            try:
                if db_path.exists():
                    db_path.unlink()
                temp_dir.rmdir()
            except OSError:
                pass

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
