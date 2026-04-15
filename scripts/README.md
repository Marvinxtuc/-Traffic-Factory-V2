# Scripts Boundary

本目录用于放置初始化、校验和维护脚本。

当前已提供：

- `init_db.py`：主工程数据库初始化。
- `restart_current_main.sh`：当前主线统一重启脚本。
- `current_main_smoke_test.py`：当前主线最小验活脚本。
- `release_check.py`：发布前检查与演练脚本。

推荐执行顺序：

1. `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`
2. `git status --porcelain`（必须无输出）
3. `mkdir -p logs && TF_PORT=8790 TF_DB_PATH=data/runtime/traffic_factory_staging.sqlite3 bash scripts/restart_current_main.sh > logs/current-main.log 2>&1 &`
4. `.venv/bin/python scripts/release_check.py --env-file <env-file> --base-url <base-url> --startup-log <log-path>`

`release_check.py` 门禁口径：

- 默认 `strict`，发布和 CI 不允许放宽。
- `debug_allow_dirty` 仅允许本地调试，且必须显式传入 `--allow-dirty --allow-dirty-reason "<reason>"`。
- `--allow-dirty` 只豁免 `git_status`，不会豁免测试、端口、启动日志和 smoke。
- 分类码 `GIT_DIRTY_BLOCKED`：预期失败（门禁生效）。
- 分类码 `TEST_SUITE_FAILED`、`PORT_NOT_LISTENING`、`STARTUP_LOG_INVALID`、`SMOKE_FAILED`：异常失败（需排障）。

统一入口（仓库根目录）：

- `make current-main-run`
- `make current-main-smoke`
- `make current-main-test`
- `make current-main-preflight`
