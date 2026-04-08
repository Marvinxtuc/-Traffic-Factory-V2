# V1 数据契约说明

## 1. 总体边界

- `trend_signals`：采集与标准化后的“信号事实层”，只存事实与基础评估，不存选题决策过程。
- `topic_pool`：从信号到选题的“决策层”，只存选题字段与状态，不回写信号正文。
- `content_jobs`：内容生成“执行层”，只存任务输入输出与执行状态，不承担选题决策。

## 2. 表结构与字段说明

### 2.1 `sources`

| 字段 | 类型 | 必填 | 可空 | 说明 |
|---|---|---|---|---|
| id | INTEGER | 是 | 否 | 主键 |
| source_type | TEXT | 是 | 否 | 来源类型，枚举：`rss/web/manual` |
| source_name | TEXT | 是 | 否 | 来源显示名 |
| source_url | TEXT | 否 | 是 | 来源 URL（manual 可为空） |
| is_active | INTEGER | 是 | 否 | 是否启用（0/1） |
| created_at | TEXT | 是 | 否 | 创建时间（UTC ISO8601） |
| updated_at | TEXT | 是 | 否 | 更新时间（UTC ISO8601） |

### 2.2 `trend_signals`

| 字段 | 类型 | 必填 | 可空 | 说明 |
|---|---|---|---|---|
| id | INTEGER | 是 | 否 | 主键 |
| source_id | INTEGER | 否 | 是 | 关联 `sources.id` |
| source_type | TEXT | 是 | 否 | 来源类型，枚举：`rss/web/manual` |
| source_name | TEXT | 是 | 否 | 来源名 |
| external_id | TEXT | 否 | 是 | 外部系统 ID |
| title | TEXT | 是 | 否 | 信号标题 |
| summary | TEXT | 否 | 是 | 摘要 |
| content_raw | TEXT | 否 | 是 | 正文原始文本 |
| canonical_url | TEXT | 否 | 是 | 规范 URL |
| author | TEXT | 否 | 是 | 作者 |
| published_at | TEXT | 否 | 是 | 发布时刻（UTC ISO8601） |
| collected_at | TEXT | 是 | 否 | 采集时刻（UTC ISO8601） |
| lang | TEXT | 否 | 是 | 语言标签 |
| tags_json | TEXT | 是 | 否 | 标签 JSON 数组字符串 |
| quality_score | REAL | 是 | 否 | 质量分，范围 `[0,1]` |
| freshness_score | REAL | 是 | 否 | 时效分，范围 `[0,1]` |
| business_score | REAL | 是 | 否 | 商业分，范围 `[0,1]` |
| dedup_key | TEXT | 是 | 否 | 去重键（唯一） |
| status | TEXT | 是 | 否 | 状态枚举：`new/reviewed/converted/archived` |
| created_at | TEXT | 是 | 否 | 创建时间 |
| updated_at | TEXT | 是 | 否 | 更新时间 |

### 2.3 `topic_pool`

| 字段 | 类型 | 必填 | 可空 | 说明 |
|---|---|---|---|---|
| id | INTEGER | 是 | 否 | 主键 |
| signal_id | INTEGER | 是 | 否 | 关联 `trend_signals.id`（唯一，单信号单选题） |
| topic_title | TEXT | 是 | 否 | 选题标题 |
| angle | TEXT | 否 | 是 | 选题角度 |
| target_platform | TEXT | 否 | 是 | 目标平台 |
| commercial_value | REAL | 是 | 否 | 商业价值占位分值 |
| status | TEXT | 是 | 否 | 状态枚举：`pending/in_progress/done/dropped` |
| created_at | TEXT | 是 | 否 | 创建时间 |
| updated_at | TEXT | 是 | 否 | 更新时间 |

### 2.4 `content_jobs`

| 字段 | 类型 | 必填 | 可空 | 说明 |
|---|---|---|---|---|
| id | INTEGER | 是 | 否 | 主键 |
| topic_id | INTEGER | 是 | 否 | 关联 `topic_pool.id` |
| content_type | TEXT | 是 | 否 | 生成类型（article/post/script 等） |
| input_payload_json | TEXT | 是 | 否 | 输入契约 JSON |
| output_payload_json | TEXT | 否 | 是 | 输出契约 JSON |
| status | TEXT | 是 | 否 | 状态枚举：`queued/generating/completed/failed` |
| created_at | TEXT | 是 | 否 | 创建时间 |
| updated_at | TEXT | 是 | 否 | 更新时间 |

## 3. 必填与可空规则（接口侧）

- 手动信号最小必填：`source_name + title`。
- RSS 入库最小必填：`source_name + source_url`。
- 网页入库最小必填：`source_url`。
- 内容生成最小必填：`topic_id + content_type`。

## 4. 默认值规则

- `trend_signals.status` 默认：`new`
- `topic_pool.status` 默认：`pending`
- `content_jobs.status` 默认：`queued`
- `trend_signals.tags_json` 默认：`[]`
- `quality_score/freshness_score/business_score` 默认由评分模块产出（异常回退到固定默认值）

## 5. API 字段命名统一规则

- 所有 API 字段统一使用 `snake_case`。
- 列表接口统一返回：`{ "items": [...], "count": <int> }`。
- 单动作接口统一返回主实体对象，例如：`signal/topic/job/result`。
- JSON 字段落库时使用明确后缀：`*_json`（如 `tags_json`、`input_payload_json`）。

## 6. 契约冻结结论

- 字段职责已按“事实层 / 决策层 / 执行层”分离。
- 状态字段已枚举化并入库约束。
- 分数字段、去重键字段、输入输出 JSON 字段已固定为本轮契约基线。
