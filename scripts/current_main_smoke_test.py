from __future__ import annotations

import argparse
import json
from typing import Any
from urllib import request


CHECKS = (
    {"path": "/healthz", "kind": "json_ok"},
    {"path": "/readyz", "kind": "json_ok"},
    {"path": "/discovery", "kind": "page"},
    {"path": "/api/signals", "kind": "json_ok"},
    {"path": "/api/topics", "kind": "json_ok"},
)


def _fetch_json(url: str, timeout: int = 5) -> tuple[int, dict[str, Any]]:
    req = request.Request(url, headers={"User-Agent": "traffic-factory-smoke-test/1.0"})
    with request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        payload = json.loads(raw.decode("utf-8")) if raw else {}
        if not isinstance(payload, dict):
            raise ValueError(f"{url} did not return a JSON object")
        return getattr(resp, "status", 200), payload


def _fetch_status(url: str, timeout: int = 5) -> int:
    req = request.Request(url, headers={"User-Agent": "traffic-factory-smoke-test/1.0"})
    with request.urlopen(req, timeout=timeout) as resp:
        resp.read()
        return getattr(resp, "status", 200)


def run_checks(base_url: str) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    checks: list[dict[str, Any]] = []

    for item in CHECKS:
        url = f"{base_url}{item['path']}"
        try:
            if item["kind"] == "page":
                status = _fetch_status(url)
                ok = status == 200
                detail = {"status": status}
            else:
                status, payload = _fetch_json(url)
                ok = status == 200 and payload.get("ok") is True
                detail = {"status": status, "ok": payload.get("ok")}
        except Exception as exc:  # pragma: no cover - exercised via CLI/runtime
            ok = False
            detail = {"error": str(exc)}

        checks.append({
            "path": item["path"],
            "ok": ok,
            **detail,
        })

    return {
        "ok": all(item["ok"] for item in checks),
        "base_url": base_url,
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test the current Traffic Factory main instance.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8787", help="Base URL of the running app.main instance")
    args = parser.parse_args()
    result = run_checks(args.base_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
