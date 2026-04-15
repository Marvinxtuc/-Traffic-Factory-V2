# 当前主线发布检查单

## 1. 目标

把“准备发布”从口头判断变成一份可重复执行的检查单，避免上线动作依赖临场记忆。

## 2. 适用范围

适用于当前主线 `app.main` 的 staging / prod 发布前检查。

## 3. 发布前检查

推荐执行顺序（必须遵守）：
1. 本地自检（unittest）
2. 工作区 clean 校验（`git status --porcelain`）
3. 启动待发布实例并保留启动日志
4. 执行 `scripts/release_check.py`
5. 仅在 release_check 通过后继续发布

门禁模式口径：
- 默认 `strict`，发布/CI 一律使用 strict。
- `debug_allow_dirty` 仅允许本地调试，且必须显式传入 `--allow-dirty --allow-dirty-reason`。
- 放宽仅豁免 `git_status`，不豁免测试、端口、启动日志和 smoke。

### A. 代码与测试

1. 运行全量测试：

```bash
.venv/bin/python -m unittest discover -s tests -p "test_*.py"
```

2. 确认工作树干净，避免把临时文件一起带进发布。
   - 执行：`git status --porcelain`
   - 判定：无输出才算 clean
   - 约束：non-clean 必须阻断，不能跳过

或直接运行自动化检查脚本：

```bash
mkdir -p logs
TF_PORT=8790 TF_DB_PATH=data/runtime/traffic_factory_staging.sqlite3 bash scripts/restart_current_main.sh > logs/current-main.log 2>&1 &
.venv/bin/python scripts/release_check.py --env-file deploy/staging.env.example --base-url http://127.0.0.1:8790 --startup-log logs/current-main.log
```

成功标准：
- 退出码为 0
- 工作树干净
- 目标端口处于监听状态
- 启动日志中存在匹配当前配置的 `server_starting` JSON 事件
- 不允许跳过已知关键测试
- 若使用 GitHub 仓库流程，`.github/workflows/current-main-gate.yml` 中的对应门禁也应为通过状态

失败判定口径：
- 分类码 `GIT_DIRTY_BLOCKED`：**预期失败**（门禁生效）
- 分类码 `TEST_SUITE_FAILED`、`PORT_NOT_LISTENING`、`STARTUP_LOG_INVALID`、`SMOKE_FAILED`：**异常失败**（需排障）
- 未先完成 clean 校验直接执行发布：**流程违规**

失败分类码 -> 处理动作：

| 分类码 | 处理动作 |
|---|---|
| `GIT_DIRTY_BLOCKED` | 清理工作区后重跑 release_check |
| `TEST_SUITE_FAILED` | 修复测试失败后重跑 |
| `PORT_NOT_LISTENING` | 检查实例监听和端口冲突后重跑 |
| `STARTUP_LOG_INVALID` | 修复启动日志路径/参数匹配后重跑 |
| `SMOKE_FAILED` | 按 smoke 输出定位接口问题后重跑 |

### B. 配置确认

至少确认以下参数与目标环境一致：
- `TF_HOST`
- `TF_PORT`
- `TF_DB_PATH`
- `TF_LOG_LEVEL`
- `TF_ACCESS_LOG`

建议：
- staging 使用独立端口与独立 DB 文件
- prod 不要沿用临时 smoke 的数据库路径

模板参考：
- `deploy/staging.env.example`
- `deploy/prod.env.example`

### C. 独立启动验证

优先用独立端口拉起待发布实例：

```bash
TF_PORT=8790 TF_DB_PATH=data/runtime/traffic_factory_staging.sqlite3 bash scripts/restart_current_main.sh
```

成功标准：
- 启动脚本未报 Python 版本错误
- 未报端口占用错误
- 进程成功监听目标端口
- 启动日志输出 `server_starting` JSON 事件

### D. smoke 验活

```bash
.venv/bin/python scripts/current_main_smoke_test.py --base-url http://127.0.0.1:8790
```

必须同时满足：
1. `/healthz` 200 且 `ok=true`
2. `/readyz` 200 且 `checks.db=ok`
3. `/discovery` 200
4. `/api/signals` 200 且 `ok=true`
5. `/api/topics` 200 且 `ok=true`
6. 脚本退出码为 0

### E. 日志与回滚确认

1. 确认启动日志中的 `host / port / db_path / log_level / access_log` 符合预期。
2. 确认当前已知限制不会影响本次发布场景：
   - 参考 `docs/current-main-known-limits.md`
3. 确认回滚口径可执行：
   - 回到上一个已验证 commit
   - 重跑 `bash scripts/restart_current_main.sh`
   - 重跑 smoke

## 4. 发布后最小检查

1. 再次访问：
   - `/healthz`
   - `/readyz`
2. 查看启动日志是否与预期一致。
3. 若发现异常，不要先删库；先按 `docs/current-main-operations.md` 的最小回滚步骤处理。

## 5. 不通过条件

出现以下任一项，本次发布直接判定为不通过：
- 全量测试失败
- 工作区 non-clean（包括 tracked 改动或未跟踪文件）
- smoke 任一核心端点失败
- 端口/数据库配置与目标环境不一致
- 无法说明回滚路径
- 依赖尚未记录在 known limits 但已知会影响使用
