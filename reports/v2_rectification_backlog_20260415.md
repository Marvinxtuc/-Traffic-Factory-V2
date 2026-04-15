# 流量工厂 v2 整改任务单（基于 2026-04-15 全流程测试）

- 来源报告：`reports/v2_full_flow_test_report_20260415.md`
- 任务口径：按模块、严重级别、可执行可验证可回滚

| 任务ID | 来源问题ID | 优先级 | Owner 类型 | 改动边界 | 任务说明 | 验证命令 | 完成标准 |
|---|---|---|---|---|---|---|---|
| TASK-OPS-001 | TFV2-OPS-P0-001 | P0 | 后端工程/运维脚本 | 仅 `scripts/restart_current_main.sh` | 修复路径含空格时 `$PYTHON_BIN` 调用失败问题（命令替换中的未加引号变量）。 | `TF_DB_PATH=data/runtime/traffic_factory_qa.sqlite3 bash scripts/restart_current_main.sh`；`./.venv/bin/python scripts/current_main_smoke_test.py --base-url http://127.0.0.1:8787` | 在包含空格路径中可稳定启动；healthz/readyz/smoke 全绿。 |
| TASK-OPS-002 | TFV2-OPS-P0-001 | P1 | 测试工程 | `tests/`（新增脚本级回归） | 增加“路径含空格”场景回归（至少覆盖 restart 脚本调用路径）。 | `./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'` | 新增用例可在当前仓路径复现并覆盖问题场景。 |
| TASK-REL-001 | TFV2-REL-P1-001 | P1 | 发布流程 owner | `docs/` + `README`（文档层） | 固化发布前流程：`git clean` 作为 release_check 必选前置步骤，避免误判“脚本失败”。 | 人工复核文档 + `./.venv/bin/python scripts/release_check.py --env-file <env> --base-url <url> --startup-log <log>` | 文档清晰描述阻断条件；团队按流程执行时不再把非 clean 阻断误判为系统故障。 |
| TASK-REL-002 | TFV2-REL-P1-001 | P2 | 发布工具 owner | `scripts/release_check.py`（可选） | 评估是否引入受控参数（仅本地调试跳过 git_status），默认仍严格阻断。 | `./.venv/bin/python scripts/release_check.py ...`（含/不含新参数） | 默认行为不变；调试场景可控放宽且不影响正式发布口径。 |

## 备注

1. 本轮测试中业务主链与门禁逻辑整体通过，整改应优先聚焦运行入口与发布流程收口。
2. 整改完成后建议复测顺序：
   1. `make current-main-test`
   2. `make current-main-smoke`
   3. `scripts/release_check.py` 全项
