# 当前主线运行与回滚手册

## 1. 目标

给当前主线 `app.main` 提供统一的启动、验活、排障与最小回滚口径，避免现场靠记忆操作。

## 2. 配置来源

当前主线优先使用以下环境变量：

- `TF_HOST`：绑定地址，默认 `127.0.0.1`
- `TF_PORT`：监听端口，默认 `8787`
- `TF_DB_PATH`：SQLite 路径，默认 `data/runtime/traffic_factory.sqlite3`
- `TF_LOG_LEVEL`：日志级别，支持 `DEBUG/INFO/WARNING/ERROR/CRITICAL`，默认 `INFO`
- `TF_ACCESS_LOG`：是否开启 Uvicorn access log，支持 `true/false`，默认 `false`

CLI 参数会覆盖环境变量；环境变量会覆盖代码默认值。

## 3. 推荐启动方式

优先使用：

```bash
bash scripts/restart_current_main.sh
```

带显式配置启动：

```bash
TF_PORT=8790 \
TF_DB_PATH=data/runtime/traffic_factory_prod.sqlite3 \
TF_LOG_LEVEL=INFO \
TF_ACCESS_LOG=false \
bash scripts/restart_current_main.sh
```

直接调用入口也可以：

```bash
.venv/bin/python -m app.main \
  --host 127.0.0.1 \
  --port 8790 \
  --db-path data/runtime/traffic_factory_prod.sqlite3 \
  --log-level INFO \
  --no-access-log
```

## 4. 成功启动信号

启动后应能看到一条 JSON 结构化日志，至少包含：

- `event=server_starting`
- `host`
- `port`
- `db_path`
- `log_level`
- `access_log`

这条日志用于托管环境和本地排障快速确认运行参数。

## 5. 验活

启动后执行：

```bash
.venv/bin/python scripts/current_main_smoke_test.py --base-url http://127.0.0.1:8790
```

推荐执行顺序（发布前）：

1. 先跑本地自检：`.venv/bin/python -m unittest discover -s tests -p "test_*.py"`
2. 再确认工作区为 clean：`git status --porcelain` 必须无输出
3. 启动待检实例并落启动日志
4. 最后执行 `scripts/release_check.py`

说明：
- `release_check.py` 默认是 `strict` 模式；发布和 CI 必须使用 strict，不可放宽。
- 若因工作区不干净导致失败，属于**预期失败**，不是脚本异常。
- 仅本地调试可用 `--allow-dirty`，且必须提供 `--allow-dirty-reason`。
- `--allow-dirty` 只豁免 `git_status`，其余检查仍按 strict 执行。

如果想把 env 配置校验、工作树干净检查、端口监听确认、启动日志核对、全量测试与 smoke 合并为一次自动检查，可执行：

```bash
mkdir -p logs
TF_PORT=8790 TF_DB_PATH=data/runtime/traffic_factory_staging.sqlite3 bash scripts/restart_current_main.sh > logs/current-main.log 2>&1 &
.venv/bin/python scripts/release_check.py --env-file deploy/staging.env.example --base-url http://127.0.0.1:8790 --startup-log logs/current-main.log
```

本地调试放宽示例（非发布流程）：

```bash
.venv/bin/python scripts/release_check.py --env-file deploy/staging.env.example --base-url http://127.0.0.1:8790 --startup-log logs/current-main.log --allow-dirty --allow-dirty-reason "local debug: temporary dirty tree"
```

必须同时满足：

1. `/healthz` 返回 200 且 `ok=true`
2. `/readyz` 返回 200 且 `checks.db=ok`
3. `/discovery` 返回 200
4. `/api/signals` 返回 200 且 `ok=true`
5. `/api/topics` 返回 200 且 `ok=true`
6. smoke 退出码为 0

如果 `release_check.py` 因以下原因失败，判定口径如下：

- 分类码为 `GIT_DIRTY_BLOCKED`：**预期失败（阻断发布）**
- 分类码为 `TEST_SUITE_FAILED`、`PORT_NOT_LISTENING`、`STARTUP_LOG_INVALID`、`SMOKE_FAILED`：**异常失败（需排障）**

失败分类码与处理动作：

| 分类码 | 场景 | 处理动作 |
|---|---|---|
| `GIT_DIRTY_BLOCKED` | strict 模式 + 工作区 non-clean | 清理工作区后重跑 |
| `TEST_SUITE_FAILED` | unittest 未通过 | 修复测试后重跑 |
| `PORT_NOT_LISTENING` | 目标端口未监听 | 检查进程/端口冲突后重跑 |
| `STARTUP_LOG_INVALID` | 启动日志缺失或参数不匹配 | 修正日志路径/启动参数后重跑 |
| `SMOKE_FAILED` | smoke 任一检查失败 | 按 smoke 输出定位并修复后重跑 |

## 6. 常见失败与处理

### 6.1 端口被占用

现象：
- `启动前检查失败：127.0.0.1:8788 已被占用。`

处理：
- 不要先入为主强杀已有实例
- 先确认占用该端口的进程是否就是健康实例
- 若只是本次临时验活，直接切换端口，例如 `TF_PORT=8790`

### 6.2 Python 版本不对

现象：
- 当前解释器低于 Python 3.11

处理：
- 优先激活 `.venv`
- 或设置 `TF_PYTHON=.venv/bin/python`

### 6.3 readyz 失败

现象：
- `/readyz` 非 200
- `checks.db=error`

处理：
- 检查 `TF_DB_PATH`
- 检查数据库目录是否可写
- 手动运行 `scripts/init_db.py --db-path <path>` 复核初始化是否正常

### 6.4 release_check 因工作区 non-clean 失败

现象：
- `scripts/release_check.py` 返回非 0
- 输出包含工作区不干净（tracked 修改、未跟踪文件等）

处理：
- 这是发布门禁的预期行为，不是脚本故障
- 先整理工作区（提交、暂存或清理本次不发布内容）后再重跑
- 在未 clean 前，不应继续推进发布动作

## 7. 最小回滚

如果当前主线新改动验活失败，最小回滚口径是：

1. 保留数据库文件，不先删库
2. 回到上一个已验证 commit
3. 重跑 `bash scripts/restart_current_main.sh`
4. 重新执行 smoke
5. 只有 smoke 全绿后，才视为回滚完成

## 8. 发布前最小检查单

1. 运行全量测试：
   - `.venv/bin/python -m unittest discover -s tests -p "test_*.py"`
2. 用独立端口启动待发布实例
3. 跑 smoke 并确认 `/healthz` `/readyz` `/discovery` `/api/signals` `/api/topics` 全绿
4. 确认启动日志里的 `host/port/db_path/log_level/access_log` 与预期一致
5. 验证完成后清理临时实例
