# 流量工厂 v2 全业务流程测试报告（本地基线）

- 报告日期：2026-04-15
- 测试范围：本地全链路 + 关键 UI 手测
- 基线：当前工作区（含未提交改动）
- 测试库：`data/runtime/traffic_factory_qa.sqlite3`
- 服务入口：`app.main`（不使用 v1）

## 一、执行摘要

### 1) 结论

1. 业务主链（Signal -> Topic -> Content -> Image -> Check -> Retro）可跑通。
2. 关键跑不通点集中在运行入口脚本与发布前流程前置条件，而非主业务逻辑。
3. 当前阻断上线的首要问题：`scripts/restart_current_main.sh` 在项目路径包含空格时启动失败。

### 2) 通过/失败总览

| Phase | 内容 | 结果 |
|---|---|---|
| A | 环境与入口稳定性 | 部分失败（A1 失败，A2/A3 通过） |
| B | API 全链路正向 | 通过 |
| C | 关键负向与门禁 | 通过 |
| D | 关键 UI 手测（最小） | 通过（含预期失败分支） |
| E | 发布前脚本链路 | 失败（git clean 阻断） |

## 二、按 Phase 执行结果

## Phase A：环境与入口稳定性

### A1 启动路径测试

- 命令：

```bash
TF_HOST=127.0.0.1 TF_PORT=8787 TF_DB_PATH=data/runtime/traffic_factory_qa.sqlite3 bash scripts/restart_current_main.sh
```

- 实际结果：失败，退出码 `1`
- 关键输出：

```text
scripts/restart_current_main.sh: line 77: /Users/marvin.x/Desktop/流量工厂: No such file or directory
启动前端口检查失败：127.0.0.1:8787 无法绑定（errno=）。
```

### A2 健康检查

- 启动方式：

```bash
./.venv/bin/python -m app.main --host 127.0.0.1 --port 8787 --db-path data/runtime/traffic_factory_qa.sqlite3
```

- `GET /healthz`：200
- `GET /readyz`：200（`checks.db=ok`）

### A3 基础 smoke

- 命令：

```bash
./.venv/bin/python scripts/current_main_smoke_test.py --base-url http://127.0.0.1:8787
```

- 结果：通过（5/5）

## Phase B：API 全链路正向

已完成并通过：

1. `POST /api/signals`
2. `POST /api/signals/{id}/advance-to-topic`
3. `POST /api/topics/{id}/advance-to-content`
4. `POST /api/contents/{id}/advance-to-image`
5. `POST /api/checks/submit`
6. `POST /api/checks/{id}/advance-to-retro`（PASS 路径）

结果：全链路通过。

## Phase C：关键负向与门禁

### C1 缺失上游对象

- 缺失 signal 推 topic：返回 404 + `ENTITY_NOT_FOUND`
- 缺失 topic 推 content：返回 404 + `ENTITY_NOT_FOUND`

结果：符合预期。

### C2 BLOCK 禁止复盘推进

- 构造 `declares_image=true` 且无图片资产
- 检查结果为 `BLOCK`
- 调用 `advance-to-retro` 返回 409 + `GATE_BLOCKED`

结果：符合预期。

### C3 修改后旧检查失效

- `mark-modified` 后旧检查记录 `record_status` 变更为 `INVALIDATED`
- 重新送检生成新 `check_version`
- 图片修改后再次触发失效

结果：符合预期。

### C4 Discovery 信息源筛选

- `source_name=wechat`：命中
- `source_type=manual + source_name=qa-wechat`：命中
- `source_name=no-such-source-xyz`：返回空

结果：符合预期。

## Phase D：关键 UI 手测（最小）

### D1~D5 页面可访问与关键 DOM 锚点

- `/discovery` `/topics` `/contents` `/checks` `/retros` 均返回 200
- 关键按钮/输入锚点均存在（筛选、推进、重检、回退、复盘）

### 动作桥接联调（`/web/actions/*`）

- `discovery_to_topic`：通过
- `topic_to_content`：通过
- `content_precheck`：无图片时返回 `PRECHECK_FAILED`（预期），有图片时通过
- `image_submit_check`：通过
- `check_recheck`：通过
- `check_rollback`：PASS 场景返回无需强制回退（预期）

补充：
- 对“已失效检查记录”调用 `check_to_retro` 会返回 409 `CONSTRAINT_VIOLATION`，对“最新 ACTIVE 检查记录”调用可通过。

## Phase E：发布前脚本链路

### E1 `release_check.py` 全项

- 命令：

```bash
./.venv/bin/python scripts/release_check.py \
  --env-file /tmp/tf_phaseE.env \
  --base-url http://127.0.0.1:8787 \
  --startup-log /tmp/tf_phaseE_start.log
```

- 结果：失败（退出码 1）
- 失败原因：`git_status` 检查不通过（工作区非 clean）
- 其他检查：`test_suite`、`port_listening`、`startup_log`、`smoke` 均通过

### E2 分离结论

1. 脚本可用性：可执行，逻辑正常。
2. 流程依赖：要求发布前必须 `git clean`，否则硬阻断。

## 三、问题清单（按模块+严重级别）

## 问题 ID：TFV2-OPS-P0-001

- 模块：运行入口（restart 脚本）
- 严重级别：P0
- 复现步骤：
  1. 在路径包含空格的项目目录执行 `bash scripts/restart_current_main.sh`
  2. 使用任意有效 `TF_DB_PATH`
- 实际结果：脚本失败，服务无法启动。
- 预期结果：脚本应正常启动服务。
- 影响范围：本地运行、联调、验收、预发布演练入口。
- 定位证据：
  - 报错指向 `scripts/restart_current_main.sh` line 77
  - 当前脚本在命令替换中使用未加引号的 `$PYTHON_BIN`
- 整改建议：
  1. 将 line 62 的 `$PYTHON_BIN` 改为 `"$PYTHON_BIN"`
  2. 补充“路径含空格”回归测试
- 验收标准：
  1. 路径含空格时 `restart_current_main.sh` 启动成功
  2. `/healthz`、`/readyz`、smoke 全绿
- 回滚提示：回滚该脚本单文件改动即可。

## 问题 ID：TFV2-REL-P1-001

- 模块：发布前检查（release_check）
- 严重级别：P1
- 复现步骤：
  1. 工作区存在未提交变更
  2. 执行 `scripts/release_check.py`
- 实际结果：`git_status` 阻断，脚本整体返回失败。
- 预期结果：按当前设计应阻断（这是机制性阻断，不是代码异常）。
- 影响范围：发布演练、验收流程。
- 定位证据：`error: git working tree is not clean`
- 整改建议：
  1. 将该规则明确写入验收 SOP（先 clean 再 release_check）
  2. 若确有需要，可新增受控参数（例如仅本地调试时跳过）
- 验收标准：
  1. clean 工作区执行 `release_check` 全绿
  2. 非 clean 工作区阻断行为保持一致
- 回滚提示：若新增“跳过开关”，可通过移除该开关回滚到严格模式。

## 四、通过项清单（本轮无需整改）

1. API 主链正向闭环可用。
2. 上下游缺失、BLOCK 阻断、重检失效链路行为正确。
3. Discovery 信息源筛选能力（`source_type + source_name`）可用。
4. 关键页面可访问，动作桥接核心链路可用。

## 五、测试结论

1. 当前“业务功能跑不通”不是主问题，主问题在“运行入口稳定性 + 发布流程前置条件”。
2. 若先修复 `TFV2-OPS-P0-001`，再按 clean 工作区执行发布流程，当前版本具备进入整改后复测与验收的条件。
