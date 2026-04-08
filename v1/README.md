# Traffic Factory V1 Base

This directory contains the Round 2 contract-hardened foundation:

- FastAPI backend
- SQLite schema with enum/check constraints
- Signal ingestion pipeline (RSS / web extraction / manual)
- Frozen state semantics and transitions
- Replaceable scoring interface
- Explicit SSL fallback policy switch
- Structured frontend handoff shells for Stitch

## Directory

- `v1/app.py`: FastAPI entry and routes.
- `v1/db.py`: SQLite schema and init helpers.
- `v1/ingestion.py`: `Collect -> Clean -> Normalize -> Enrich` utility methods.
- `v1/repository.py`: DB read/write helpers.
- `v1/web/*.html`: Discovery / Topic Pool / Content structured containers.
- `scripts/init_v1_db.py`: initialize database.
- `scripts/seed_v1_demo.py`: insert sample data.

## Run

```bash
python3 scripts/init_v1_db.py
python3 scripts/seed_v1_demo.py
python3 -m uvicorn v1.app:app --host 127.0.0.1 --port 8788
```

Open:

- `http://127.0.0.1:8788/web/discovery`
- `http://127.0.0.1:8788/web/topics`
- `http://127.0.0.1:8788/web/content`

## Required APIs Implemented

- `GET /signals`
- `POST /signals/manual`
- `POST /signals/{signal_id}/review`
- `POST /signals/ingest/rss`
- `POST /signals/ingest/web`
- `POST /topics/from-signal/{signal_id}`
- `GET /topics`
- `POST /topics/{topic_id}/start`
- `POST /topics/{topic_id}/complete`
- `POST /topics/{topic_id}/drop`
- `POST /content/generate`
- `GET /content/versions`
- `GET /content/versions/{version_id}`

## Round 2 Contract Documents

- `v1/docs/V1_DATA_CONTRACT.md`
- `v1/docs/V1_STATE_MACHINE.md`
- `v1/docs/V1_SCORING_INTERFACE.md`
- `v1/docs/V1_DEDUP_RULE.md`
- `v1/docs/V1_INGEST_SECURITY.md`
- `v1/docs/V1_FRONTEND_SHELL.md`
- `v1/docs/V1_UI_CN_STANDARD.md`
- `v1/docs/V1_UI_LANGUAGE_GATE.md`

## UI Chinese Enforcement

- `v1/web/assets/i18n_zh.js` 是前端可见文案唯一入口。
- `v1/web/discovery.html`、`v1/web/topics.html`、`v1/web/content.html` 必须通过 `data-i18n` 或 `TFUI.t(...)` 引用术语。
- 英文回流检查命令：`python3 scripts/check_ui_language.py`。

## 依赖安装

```bash
source .venv/bin/activate
python -m pip install -r v1/requirements.txt
```

说明：macOS Homebrew Python 可能启用 PEP 668（禁止系统级 pip 安装），建议始终在虚拟环境中执行。

## 运行态验证

1. 启动服务：

```bash
python3 -m uvicorn v1.app:app --host 127.0.0.1 --port 8788
```

2. 执行运行态回归脚本（新终端）：

```bash
python3 scripts/runtime_smoke_test.py --base-url http://127.0.0.1:8788 --cleanup
```

临时数据库隔离运行（推荐本地自检）：

```bash
python3 scripts/runtime_smoke_test.py --use-temp-db --cleanup
```

验证通过标准：
- `GET /health` 返回 200。
- `/web/discovery`、`/web/topics`、`/web/content` 返回 200 且为 HTML。
- 页面包含 i18n 接入锚点，且不出现 `undefined` / `null` 渲染异常。
- 最小闭环 API 可走通：`signals/manual -> topics/from-signal -> content/generate`。
- 脚本最终输出：`运行态验证通过`。

常见错误：
- 端口占用：更换端口或停止占用进程。
- 依赖缺失：重新执行 `python3 -m pip install -r v1/requirements.txt`。

## Smoke 测试数据标记与清理

- `runtime_smoke_test.py` 写入数据统一标记：
  - `trend_signals.source_name = "smoke_test"`
  - `trend_signals.tags_json` 包含 `runtime_smoke`
  - `topic_pool` 使用 `angle="__runtime_smoke__"` 且标题前缀 `[SMOKE_TEST]`
  - `content_jobs.input_payload_json` 包含 `"runtime_smoke": true`
- 清理命令：

```bash
python3 scripts/runtime_smoke_test.py --base-url http://127.0.0.1:8788 --cleanup
```

- `--cleanup` 会按顺序清理标记数据：`content_versions -> content_jobs -> topic_pool -> trend_signals`。

## 提交前强制流程

前端文案相关改动必须按以下顺序执行：

1. 先更新 `v1/web/assets/i18n_zh.js`。
2. 页面与脚本只引用 key，不得硬编码文案。
3. 执行中文门禁：

```bash
python3 scripts/check_ui_language.py
```

4. 服务启动后执行运行态验证：

```bash
python3 scripts/runtime_smoke_test.py --base-url http://127.0.0.1:8788 --cleanup
```

统一命令入口（仓库根目录）：

```bash
make v1-check-ui-language
make v1-runtime-smoke
make v1-preflight
```

## SSL Fallback Switch

- Default behavior: SSL verification failure aborts web ingestion.
- Optional fallback (explicit opt-in): set `TF_V1_ALLOW_INSECURE_SSL_FALLBACK=1`.
- Risk note: when fallback is enabled, HTTPS certificate verification is bypassed on SSL-error retry.
