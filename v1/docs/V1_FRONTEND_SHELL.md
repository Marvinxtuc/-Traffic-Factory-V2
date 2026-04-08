# 前端承接骨架升级说明

## 1. 设计目标

- 保持极简，不做最终视觉设计。
- 提供稳定 DOM 分层，便于 Stitch 后续替换样式与组件。
- 每页固定承接区块，按任务卡冻结分区语义。

## 2. 发现台（`/web/discovery`）

结构图：

```text
Header/Nav
└─ Main[data-page=discovery]
   ├─ Section#discovery-filters    [data-slot=filters]
   ├─ Section#discovery-list       [data-slot=list]
   └─ Section#discovery-detail     [data-slot=detail]
```

职责：
- `filters`：筛选控件与采集动作
- `list`：signal 列表
- `detail`：选中 signal + 操作结果

## 3. 选题池（`/web/topics`）

结构图：

```text
Header/Nav
└─ Main[data-page=topics]
   ├─ Section#topics-stats         [data-slot=stats]
   ├─ Section#topics-list          [data-slot=list]
   └─ Section#topics-guidance      [data-slot=guidance]
```

职责：
- `stats`：选题池聚合指标（总量与状态分布）
- `list`：topic_pool 列表
- `guidance`：指导区与预留说明

## 4. 内容工坊（`/web/content`）

结构图：

```text
Header/Nav
└─ Main[data-page=content]
   ├─ Section#content-input-association [data-slot=input-association]
   ├─ Section#content-output            [data-slot=output]
   └─ Section#content-versions          [data-slot=versions]
```

职责：
- `input-association`：选题关联与输入参数
- `output`：当前生成结果
- `versions`：版本区预留（本轮提供轻量占位）

## 5. Stitch 对接预留点

- 页面级锚点：`main[data-page=...]`
- 区块级锚点：`section[data-slot=...]`（按页面语义固定）
- 关键内容容器：
  - 列表体：`tbody` 固定 ID
  - 详情区：`pre` 固定 ID
  - 操作区：输入与按钮固定 ID

对接建议：
- Stitch 后续仅替换样式与组件结构，不改变区块 ID 与 data-slot 语义。
