# 评分接口说明

## 1. 目标

冻结三分结构接口：
- `quality_score`
- `freshness_score`
- `business_score`

本轮仍使用轻量规则，但结构已改为可替换接口。

## 2. 模块与替换点

- 评分契约模块：`v1/scoring.py`
- 接口类型：`ScoreProvider`（Protocol）
- 默认实现：`DefaultRuleScoreProvider`
- 调用入口：`score_signal(payload, provider=None)`
- 接入点：`normalize_signal(..., score_provider=...)`

替换方式：
- 自定义实现一个 `ScoreProvider`（实现 `score(self, payload)`）
- 在 `normalize_signal` 调用时注入 `score_provider`

## 3. 输入契约（ScoreInput）

| 字段 | 类型 | 说明 |
|---|---|---|
| source_type | str | 来源类型 |
| title | str | 标题 |
| summary | str | 摘要（清洗后） |
| content_raw | str | 正文（清洗后） |
| published_at_iso | str \| None | 发布时间 |
| collected_at_iso | str | 采集时间 |
| tags | list[str] | 标签列表 |

## 4. 输出契约（ScoreOutput）

| 字段 | 类型 | 范围 |
|---|---|---|
| quality_score | float | `[0, 1]` |
| freshness_score | float | `[0, 1]` |
| business_score | float | `[0, 1]` |

## 5. 默认实现规则

- `quality_score`：基于 `summary/content_raw` 长度的线性占位规则。
- `freshness_score`：基于发布时间距当前时间的衰减规则；缺失时间默认 `0.5`。
- `business_score`：当前固定基线 `0.5`，预留业务策略替换。

## 6. 异常值处理

- NaN -> 使用默认值（quality=0.0, freshness=0.5, business=0.5）
- 小于 0 -> 截断为 0
- 大于 1 -> 截断为 1
- 最终统一保留 3 位小数
