# 流量工厂 v2 P2+P3 整改完成报告（2026-04-15）

## 1. 结论
- P2 已完成：`release_check.py` 新增受控调试放宽（`--allow-dirty` + `--allow-dirty-reason`），默认 strict 行为保持不变。
- P3 已完成：失败分类码与文档口径收口、一键 rehearsal 入口落地、`reports` 留痕策略收口。
- 验收通过：单测、strict(dirty) 阻断、debug_allow_dirty(dirty) 放行、clean(strict) 通过均满足预期。

## 2. 改动清单（按模块）

### 2.1 P2：release_check 核心逻辑
- `scripts/release_check.py`
  - 新增参数：`--allow-dirty`、`--allow-dirty-reason`
  - 新增顶层输出：`gate_mode`、`waivers`
  - 新增检查输出字段：`failure_code`
  - 门禁规则：
    - strict（默认）：dirty => `GIT_DIRTY_BLOCKED`
    - debug_allow_dirty：仅豁免 `git_status`，不豁免 tests/port/startup_log/smoke

### 2.2 P2：测试补齐
- `tests/test_release_check.py`
  - 新增 dirty+strict 阻断断言
  - 新增 dirty+allow-dirty+reason 放行断言（含 waivers）
  - 新增缺少 reason 参数报错断言
  - 新增 clean+strict 兼容断言

### 2.3 P3：文档收口
- `README.md`
- `docs/current-main-operations.md`
- `docs/release-checklist.md`
- `scripts/README.md`
  - 补齐 strict/debug_allow_dirty 边界
  - 补齐失败分类码到处理动作对照
  - 固化执行顺序与“预期失败/异常失败”判定口径

### 2.4 P3：入口与留痕策略
- `Makefile`
  - 新增：`v2-release-rehearsal`
  - 新增：`v2-release-rehearsal-debug`（要求 `ALLOW_DIRTY_REASON`）
- `scripts/release_rehearsal.sh`（新增）
  - 一键串联：启动实例 -> smoke -> release_check
  - 默认 strict；显式 reason 才进入 debug_allow_dirty
- `.gitignore`
  - 放开：`reports/v2_*.md`、`reports/README.md`
- `reports/README.md`（新增）
  - 约束报告命名规则与最小模板字段

## 3. 执行与验证证据

### 3.1 单测
- 命令：
  - `.venv/bin/python -m unittest tests.test_release_check -v`
  - `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`
- 结果：
  - `tests.test_release_check`: 13/13 通过
  - 全量：60/60 通过

### 3.2 strict 场景（dirty 工作区）
- 命令：
  - `TF_PORT=8793 TF_DB_PATH=data/runtime/traffic_factory_qa.sqlite3 make v2-release-rehearsal`
- 结果：
  - 命令阻断（符合预期）
  - `gate_mode=strict`
  - `git_status.failure_code=GIT_DIRTY_BLOCKED`
  - 其余检查（tests/port/startup_log/smoke）可见为通过

### 3.3 debug_allow_dirty 场景（dirty 工作区）
- 命令：
  - `TF_PORT=8794 TF_DB_PATH=data/runtime/traffic_factory_qa.sqlite3 make v2-release-rehearsal-debug ALLOW_DIRTY_REASON='local debug verify waiver'`
- 结果：
  - 命令通过
  - `gate_mode=debug_allow_dirty`
  - `waivers` 含 `{"check":"git_status","reason":"local debug verify waiver"}`

### 3.4 clean(strict) 场景（新补丁 clean 基线）
- 方法：临时 clone + 应用本轮关键补丁 + 本地提交，形成 clean worktree 后执行 strict release_check。
- 结果：
  - 退出码 `0`
  - `gate_mode=strict`
  - `waivers=[]`
  - checks 全通过

### 3.5 入口与策略附加验证
- `make v2-release-rehearsal-debug`（未传 `ALLOW_DIRTY_REASON`）=> 退出码 `2`（符合预期）
- `git check-ignore -v reports/v2_example.md reports/README.md reports/other_note.md`
  - `v2_example.md`、`reports/README.md` 放行
  - `other_note.md` 继续忽略

## 4. 边界与非目标确认
- 未改 API、状态机、数据模型。
- 未引入新服务、CI 重构或新前端框架。
- 发布/CI strict 规则保持。

## 5. 回滚方式（最小）
1. 回滚以下文件到本轮前：
   - `scripts/release_check.py`
   - `tests/test_release_check.py`
   - `README.md`
   - `docs/current-main-operations.md`
   - `docs/release-checklist.md`
   - `scripts/README.md`
   - `Makefile`
   - `scripts/release_rehearsal.sh`
   - `.gitignore`
   - `reports/README.md`
2. 验证回滚后行为：
   - strict 仍阻断 dirty
   - 不再提供 `allow-dirty` 与 rehearsal 新入口
