# Scripts Boundary

本目录用于放置初始化、校验和维护脚本。

当前已提供：

- `init_db.py`：主工程数据库初始化。
- `init_v1_db.py`：V1 底座数据库初始化。
- `seed_v1_demo.py`：V1 示例数据注入。
- `check_ui_language.py`：V1 前端英文 UI 文案残留检查。
- `runtime_smoke_test.py`：V1 运行态最小回归测试（服务需先启动）。
  - `--cleanup`：清理 `smoke_test/runtime_smoke` 标记数据。
  - `--use-temp-db`：使用临时 SQLite 执行并自动删除。

推荐执行顺序：

1. `python3 scripts/check_ui_language.py`
2. `python3 scripts/runtime_smoke_test.py --base-url http://127.0.0.1:8788 --cleanup`

统一入口（仓库根目录）：

- `make v1-check-ui-language`
- `make v1-runtime-smoke`
- `make v1-preflight`
