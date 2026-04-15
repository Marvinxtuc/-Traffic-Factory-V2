# 流量工厂 v2 P0+P1 修复完成报告（2026-04-15）

## 1. 结论
- P0 已修复：`scripts/restart_current_main.sh` 在仓库路径含空格场景可正常启动。
- P1 已收口：发布流程文档已明确 `release_check.py` 的 git clean 严格前置条件与失败判定口径。
- 回归验证通过：`unittest` 全绿，`restart_current_main.sh + smoke` 全绿，`release_check` 在 non-clean 阻断、在 clean 场景通过。

## 2. 已确认事实（含证据）

### 2.1 P0 脚本修复
- 文件：`scripts/restart_current_main.sh`
- 变更：
  - `ensure_port_available` 中未加引号调用已修复：
    - 旧：`$($PYTHON_BIN - "$host" "$port" <<'PY' ...)`
    - 新：`$("$PYTHON_BIN" - "$host" "$port" <<'PY' ...)`
- 影响：避免 `PYTHON_BIN` 含空格时被拆词导致命令执行失败。

### 2.2 P1 文档收口
- 文件：
  - `docs/current-main-operations.md`
  - `docs/release-checklist.md`
  - `README.md`
- 收口内容：
  - 固定发布前顺序：`unittest -> git clean 校验 -> 启动并留日志 -> release_check`
  - 明确 non-clean 被阻断是“预期失败”，不是脚本异常。
  - 明确 `git status --porcelain` 为空为硬前置条件。

### 2.3 回归测试补齐
- 文件：`tests/test_restart_current_main_script.py`
- 新增用例：
  - 通过“临时目录+带空格软链接路径”执行 `restart_current_main.sh`
  - 验证脚本不会在端口检查阶段因路径拆词失败
  - 验证执行后端口可再次绑定（无残留进程）

## 3. 执行命令与结果

### 3.1 全量单测
- 命令：
  - `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`
- 结果：
  - `Ran 56 tests ... OK`

### 3.2 启动脚本 + smoke
- 命令：
  - `TF_DB_PATH=data/runtime/traffic_factory_qa.sqlite3 TF_PORT=8788 bash scripts/restart_current_main.sh`
  - `.venv/bin/python scripts/current_main_smoke_test.py --base-url http://127.0.0.1:8788`
- 结果：
  - `/healthz` 正常
  - smoke 5 个检查项全通过（`ok=true`）

### 3.3 release_check 双场景

#### 非 clean 场景（当前工作区）
- 结果：**阻断（符合预期）**
- 关键证据：
  - `git_status.ok=false`
  - `error="git working tree is not clean"`
  - 脚本退出码 `1`

#### clean 场景（临时 clean worktree）
- 结果：**通过（符合预期）**
- 关键证据：
  - `git_status.ok=true`
  - `test_suite.ok=true`
  - `smoke.ok=true`
  - 脚本退出码 `0`

## 4. 风险与边界
- 本轮未修改 API、状态机、数据模型。
- `release_check.py` 仍保持严格阻断 non-clean，未引入跳过开关（符合约束）。
- 当前主仓库存在大量既有未提交改动，属于本轮外部背景，不在本次修复范围内。

## 5. 回滚方式

### 5.1 代码回滚（最小）
1. 回滚脚本与测试文档改动到修复前提交。
2. 重新执行：
   - `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`
   - 启动脚本与 smoke

### 5.2 运行回滚
1. 停止当前实例。
2. 回到上一个已验证 commit。
3. 用 `bash scripts/restart_current_main.sh` 重新拉起。
4. 再跑 smoke 验证。
