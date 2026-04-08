# 《流量工厂一期实施方案（项目版）》

## 1. 新仓目录骨架

```text
repo-root/
├─ app/
│  ├─ api/
│  ├─ web/
│  └─ main.py
├─ domain/
│  ├─ models/
│  ├─ repositories/
│  └─ rules/
├─ services/
├─ skills/
├─ adapters/
├─ workflows/
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ e2e/
├─ data/
│  ├─ seeds/
│  ├─ testdata/
│  └─ runtime/
├─ runtime/
├─ reports/
├─ artifacts/
├─ scripts/
├─ docs/
├─ README.md
├─ .gitignore
└─ pyproject.toml
```

### 1.1 目录原则
1. 代码、数据、运行态、报告、产物必须物理分离。
2. 页面骨架与业务逻辑分层，避免后续 Stitch 页面实现和后端接口耦死。
3. 一期不继承旧仓目录，不复制旧模块。

## 2. 第一批文件

### 2.1 初始化文件
- `pyproject.toml`
- `.gitignore`
- `README.md`
- `docs/phase1-minimal-system-definition.md`
- `docs/phase1-implementation-plan.md`

### 2.2 领域与数据文件
- `domain/models/signal.py`
- `domain/models/topic.py`
- `domain/models/content_variant.py`
- `domain/models/image_asset.py`
- `domain/models/publish_check.py`
- `domain/models/retro_record.py`
- `domain/models/publish_check_item.py`
- `domain/models/execution_record.py`
- `domain/repositories/*.py`
- `scripts/init_db.py`

### 2.3 服务与流程文件
- `services/discovery_service.py`
- `services/topic_service.py`
- `services/content_service.py`
- `services/image_service.py`
- `services/check_service.py`
- `services/retro_service.py`
- `workflows/main_chain.py`
- `workflows/check_gate.py`

### 2.4 页面与接口骨架
- `app/main.py`
- `app/api/routes/discovery.py`
- `app/api/routes/topic.py`
- `app/api/routes/content.py`
- `app/api/routes/image.py`
- `app/api/routes/check.py`
- `app/api/routes/retro.py`
- `app/web/pages/discovery.*`
- `app/web/pages/topic.*`
- `app/web/pages/content.*`
- `app/web/pages/image.*`
- `app/web/pages/check.*`
- `app/web/pages/retro.*`

### 2.5 skills 能力层文件
- `skills/registry.py`
- `skills/router.py`
- `skills/fallback.py`
- `adapters/providers/*.py`

## 3. 实施顺序

### 3.1 第 0 阶段：边界先行
1. 建仓目录、`.gitignore`、运行边界。
2. 确认 SQLite 文件位置、测试数据位置、产物输出位置。
3. 先写文档和初始化脚本，不直接进入业务大实现。

### 3.2 第 1 阶段：对象先行
1. 定义六个核心对象和两个支撑对象的数据库表。
2. 明确状态机和上游外键，其中 `publish_check` 以 `content_variant_id` 为必填外键，`image_asset_id` 为条件必填外键。
3. 实现最薄仓储层，保证“所有对象必须落库”。

### 3.3 第 2 阶段：主链路服务先行
1. `discovery_service` 落地 `signal`
2. `topic_service` 完成 `signal -> topic`
3. `content_service` 完成 `topic -> content_variant`
4. `image_service` 完成 `content_variant -> image_asset`
5. `check_service` 完成 `publish_check` 与 gate 决策
6. `retro_service` 完成 `publish_check -> retro_record`

### 3.4 第 3 阶段：页面与接口骨架
1. 先做 6 个工作台页面和 6 组接口，不做复杂视觉稿。
2. 页面统一采用“左导航 + 主工作区 + 右侧详情/状态区”。
3. 页面按钮和接口都按主链路约束控制可用性，并严格对应 `Discovery -> Topic Pool -> Content Lab -> Image Lab -> Quality Gate -> Retrospective`。

### 3.5 第 4 阶段：能力层接入
1. 接入最小来源抓取能力
2. 接入最小内容生成能力
3. 接入最小图片生成能力
4. 统一执行记录和回退策略

### 3.6 第 5 阶段：测试和验收
1. 主链路集成测试
2. 发布检查专项测试
3. 页面流转端到端测试
4. 验收脚本与报告

## 4. 第一批代码骨架

### 4.1 数据定义顺序
1. `signal`
2. `topic`
3. `content_variant`
4. `image_asset`
5. `publish_check`
6. `publish_check_item`
7. `retro_record`
8. `execution_record`

### 4.2 页面与路由顺序
1. `/discovery` 对应 `Discovery`
2. `/topics` 对应 `Topic Pool`
3. `/contents` 对应 `Content Lab`
4. `/images` 对应 `Image Lab`
5. `/checks` 对应 `Quality Gate`
6. `/retros` 对应 `Retrospective`

### 4.3 每页最小骨架要求
- 列表区：显示当前阶段对象列表
- 详情区：显示当前对象核心字段、状态和上下游引用
- 操作区：仅展示允许进入下一步的动作
- 状态区：展示 gate、提示和回退信息

### 4.4 发布检查模块落地顺序
1. 定义检查分类与规则编码
2. 实现 `publish_check` 头记录
3. 实现 `publish_check_item` 明细记录
4. 实现 `PASS / WARN / BLOCK` 聚合逻辑
5. 实现 `WARN` 风险记录落库
6. 实现对象变更后的检查失效机制，并确保新检查新增记录、不覆盖旧记录
7. 将 gate 接入页面按钮和服务层接口

### 4.5 强 gate 实施方式
1. 页面层：未满足条件时不展示或禁用下游动作。
2. 服务层：统一校验检查状态，不允许绕开前端直接调用；`PASS/WARN` 可继续，`BLOCK` 必须阻断。
3. 工作流层：状态推进前再次验证 gate。
4. 数据层：保存 `publish_check` 有效性标记，避免历史检查误用。

## 5. 第一批测试

### 5.1 单元测试
- 对象状态推进测试
- 仓储落库测试
- 发布检查结果聚合测试
- `WARN` 风险记录与 `BLOCK` 阻断行为测试

### 5.2 集成测试
- `signal -> topic -> content_variant -> image_asset -> publish_check -> retro_record` 最小闭环测试
- 上游变更导致检查失效测试
- 修改后新增 `publish_check` 记录且旧记录保留测试
- 所有主链对象落库验证测试

### 5.3 页面与流程测试
- 不允许跳过页面流转测试
- 发布检查页面按钮状态测试
- `BLOCK` 时返回上游修改测试

## 6. 第一批验收点

1. 可从发现台创建 `signal` 并在选题池生成 `topic`。
2. 可基于 `topic` 生成至少 2 个 `content_variant`。
3. 可基于选中内容生成至少 1 个 `image_asset`。
4. 可在发布检查页得到 `PASS / WARN / BLOCK` 结果和问题清单。
5. `BLOCK` 时系统必须阻断继续流转。
6. `WARN` 时必须保留风险记录后才能继续。
7. 可在复盘台创建 `retro_record` 并回看完整链路。

## 7. 本轮不做事项

1. 不做多平台自动分发。
2. 不做复杂调度和任务编排系统。
3. 不做大型 BI 看板。
4. 不做细粒度权限体系。
5. 不做复杂多模态分析和推荐系统。
6. 不做旧仓模块迁移或整块复制。

## 8. 风险与控制

### 8.1 主要风险
- 若对象关系定义过松，后续页面和审计链会失真。
- 若发布检查不是强 gate，主链路会被旁路破坏。
- 若对象未全部落库，复盘和验收无法成立。

### 8.2 控制措施
1. 先锁表结构和外键，再写页面和服务。
2. 先实现 `check_gate`，再开放复盘入口。
3. 先实现测试夹具目录，再写集成测试。
