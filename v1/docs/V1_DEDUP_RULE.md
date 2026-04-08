# 去重规则说明

## 1. 当前规则目标

- 提供稳定、可复核、低复杂度的去重键。
- 本轮不引入复杂语义近似去重，只做基础标准化与一致性判定。

## 2. dedup_key 生成位置

- 规则模块：`v1/dedup.py`
- 调用位置：`v1/ingestion.py -> normalize_signal -> build_dedup_key`

## 3. 生成字段

`dedup_key = sha256(seed)`，其中 `seed` 由以下字段拼接：

1. `source_type`
2. `source_name`
3. `locator`（定位键）
4. `normalized_title`
5. `published_day`（`published_at` 的日期部分）

说明：
- 明确包含 `source_type/source_name` 维度，避免跨源误判。

## 4. locator 规则（URL 缺失处理）

优先级：
1. 若 `canonical_url` 存在：`locator = url:{canonical_url}`
2. 若 `canonical_url` 缺失且 `external_id` 存在：`locator = external:{external_id}`
3. 二者都缺失：`locator = title:{normalized_title}`

## 5. title 标准化与近似重复口径

- 标题先做基础标准化：
  - 小写
  - 去除标点和多余空白
- 本轮不做语义近似匹配（如 embedding 或编辑距离聚类）。
- 因此“语义近似但文本差异明显”的重复，当前不会合并。

## 6. 冲突策略

- `trend_signals.dedup_key` 为唯一键。
- 入库冲突时不覆盖旧记录，返回已有记录 ID，并标记 `inserted=false`。
