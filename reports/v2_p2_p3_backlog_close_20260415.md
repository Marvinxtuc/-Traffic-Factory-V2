# 流量工厂 v2 P2+P3 闭环任务单（已完成）

## 已关闭任务

| 任务ID | 优先级 | 状态 | 交付物 | 验收证据 |
|---|---|---|---|---|
| TASK-REL-P2-001 | P2 | Closed | `scripts/release_check.py` 新增 `--allow-dirty` / `--allow-dirty-reason`、`gate_mode`、`waivers`、`failure_code` | strict(dirty) 阻断；debug_allow_dirty(dirty) 放行；clean(strict) 通过 |
| TASK-REL-P2-002 | P2 | Closed | `tests/test_release_check.py` 新增 4 类回归测试 | `tests.test_release_check` 13/13 OK |
| TASK-OPS-P3-001 | P3 | Closed | 文档口径统一（README + docs + scripts/README） | 参数名、失败码、流程顺序与脚本一致 |
| TASK-OPS-P3-002 | P3 | Closed | 一键 rehearsal 入口（Make + `scripts/release_rehearsal.sh`） | `make v2-release-rehearsal` / `make v2-release-rehearsal-debug` 结果符合预期 |
| TASK-OPS-P3-003 | P3 | Closed | `reports` 留痕策略收口（`.gitignore` + `reports/README.md`） | `git check-ignore` 验证通过 |

## 验收命令（复现）
1. `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`
2. `TF_PORT=8793 TF_DB_PATH=data/runtime/traffic_factory_qa.sqlite3 make v2-release-rehearsal`（预期阻断）
3. `TF_PORT=8794 TF_DB_PATH=data/runtime/traffic_factory_qa.sqlite3 make v2-release-rehearsal-debug ALLOW_DIRTY_REASON='local debug verify waiver'`（预期通过）
4. clean(strict) 场景：在 clean worktree 执行 `scripts/release_check.py`（预期通过）

## 残留事项（非阻断）
- 当前主仓库存在既有未提交改动，strict 模式下仍会触发 `GIT_DIRTY_BLOCKED`，这是门禁预期行为。
- 如需正式发布，需先做发布分支的工作区收敛与 clean 验证。

## 建议下一步
1. 在发布候选分支执行一次 `make v2-release-rehearsal`（strict，clean 工作区）。
2. 将本报告与 `v2_p2_p3_remediation_report_20260415.md` 一并提交审阅。
