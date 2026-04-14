# 流量工厂 v2

## 当前状态

本仓已完成一期主线（002-009）与条件修正卡（C01、C02），当前处于收尾清理阶段，目标是达到“一期可交付整理完成”。

一期固定主链路：

`信号 -> 选题 -> 内容版本 -> 图片资产 -> 发布检查记录 -> 复盘记录`

对应模型：

`Signal -> Topic -> ContentVariant -> ImageAsset -> PublishCheck -> RetroRecord`

## 一期固定约束

1. 不允许无信号创建选题。
2. 不允许无选题创建内容版本。
3. 不允许无内容版本创建图片资产。
4. 不允许无发布检查记录创建复盘记录。
5. 不允许跳步。
6. 所有主链对象必须落库。
7. 发布检查是强闸门，不是提示层。
8. 修改内容版本或图片资产后，旧检查记录失效，必须新增发布检查记录，不能覆盖旧记录。

发布检查状态固定为：`通过 / 警告 / 拦截`。

## 当前工程落点

- `app/api/`：最小接口入口与路由（6 个核心模块）。
- `app/web/pages/`：6 个页面骨架与最小动作联动入口。
- `app/web/action_bridge.py`：页面动作到接口的桥接层。
- `domain/`：领域对象、规则与 SQLite 仓储。
- `services/`：主链服务、发布检查服务、能力桥接服务。
- `workflows/`：主链工作流编排。
- `skills/` 与 `adapters/providers/`：技能能力层最小骨架与 provider 占位。
- `tests/`：一期最小测试边界、主链验证、发布检查专项、页面联动验证。

## 事实源

1. `docs/phase1-minimal-system-definition.md`
2. `docs/phase1-implementation-plan.md`
3. `docs/repo-boundaries.md`
4. `stitch/`（仅设计输入资产，不作为运行页面目录）

## 常用命令

```bash
# 显式使用 Python 3.11+（不要直接依赖系统 python3，macOS 上常见为 3.9）
.venv/bin/python --version

# 初始化数据库（默认 data/runtime/traffic_factory.sqlite3）
.venv/bin/python scripts/init_db.py

# 运行全量测试
.venv/bin/python -m unittest discover -s tests -p "test_*.py"

# 直接启动当前主线
.venv/bin/python -m app.main --host 127.0.0.1 --port 8787 --db-path data/runtime/traffic_factory.sqlite3

# 显式指定日志口径启动
.venv/bin/python -m app.main --host 127.0.0.1 --port 8787 --db-path data/runtime/traffic_factory.sqlite3 --log-level INFO --no-access-log
```

## 当前主线可复用重启方案

当前主线入口固定为 `app.main`，仓库 `pyproject.toml` 已声明 `requires-python = ">=3.11"`。

优先使用：

```bash
bash scripts/restart_current_main.sh
```

脚本行为：

1. 优先选择已激活虚拟环境、其次 `.venv/bin/python`、再次 `python3.11`。
2. 启动前强校验 Python 版本，低于 3.11 直接失败，避免再次误用 3.9。
3. 启动前校验 `TF_PORT` 是否为合法端口，并预检查 `TF_HOST:TF_PORT` 是否已被占用；若端口冲突，会优先输出监听进程信息与改端口建议。
4. 自动创建数据库目录、执行 `scripts/init_db.py`，然后以同一解释器启动 `app.main`。
5. 支持环境变量覆写：`TF_PYTHON`、`TF_HOST`、`TF_PORT`、`TF_DB_PATH`、`TF_LOG_LEVEL`、`TF_ACCESS_LOG`。

例如：

```bash
TF_PORT=8788 TF_DB_PATH=data/runtime/traffic_factory.sqlite3 bash scripts/restart_current_main.sh
```

如果要显式打开 access log：

```bash
TF_PORT=8788 TF_LOG_LEVEL=DEBUG TF_ACCESS_LOG=true bash scripts/restart_current_main.sh
```

## 当前主线验活

当前主线启动后，优先使用最小 smoke 脚本做验活：

```bash
.venv/bin/python scripts/current_main_smoke_test.py --base-url http://127.0.0.1:8787
```

若当前实例运行在 8791：

```bash
.venv/bin/python scripts/current_main_smoke_test.py --base-url http://127.0.0.1:8791
```

成功标准：

1. `/healthz` 返回 200，且 JSON 中 `ok=true`
2. `/readyz` 返回 200，且 JSON 中 `ok=true`
3. `/discovery` 返回 200
4. `/api/signals` 返回 200，且 JSON 中 `ok=true`
5. `/api/topics` 返回 200，且 JSON 中 `ok=true`
6. 脚本退出码为 0

如果 smoke 脚本失败，再去检查端口占用、数据库路径和实例日志，不要先入为主地强杀已有健康实例。

更完整的运行/回滚口径见：`docs/current-main-operations.md`

发布前检查单见：`docs/release-checklist.md`

自动化发布检查脚本：
- `.venv/bin/python scripts/release_check.py --env-file deploy/staging.env.example --base-url http://127.0.0.1:8790`

当前版本边界与已知限制见：`docs/current-main-known-limits.md`

环境模板见：
- `deploy/staging.env.example`
- `deploy/prod.env.example`
