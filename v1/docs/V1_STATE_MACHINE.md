# 状态机说明

## 1. `signal.status`

枚举值：
- `new`
- `reviewed`
- `converted`
- `archived`

迁移规则：
- `new -> reviewed/converted/archived`
- `reviewed -> converted/archived`
- `converted -> archived`
- 其余迁移不允许

当前落地点：
- 新建信号（manual/rss/web）默认 `new`
- `POST /topics/from-signal/{signal_id}` 成功后，信号状态迁移到 `converted`

## 2. `topic_pool.status`

枚举值：
- `pending`
- `in_progress`
- `done`
- `dropped`

迁移规则：
- `pending -> in_progress/done/dropped`
- `in_progress -> done/dropped`
- `done/dropped` 为终态

当前落地点：
- 创建选题默认 `pending`
- 本轮未开放审批/归档接口，但迁移规则已在契约中冻结

## 3. `content_jobs.status`

枚举值：
- `queued`
- `generating`
- `completed`
- `failed`

迁移规则：
- `queued -> generating/failed`
- `generating -> completed/failed`
- `completed/failed` 为终态

当前落地点：
- `POST /content/generate` 内部按 `queued -> generating -> completed` 执行
- 非法迁移返回冲突错误（409）

## 4. 约束实现点

- 应用层：`v1/contracts.py` 统一枚举与迁移校验函数
- 持久层：`v1/db.py` 用 SQL `CHECK` 约束状态字段
- 运行层：`v1/repository.py` 在关键写路径执行迁移校验
