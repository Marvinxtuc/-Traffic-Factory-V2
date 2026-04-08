# 《流量工厂一期最小系统定义（项目版）》

## 1. 一期目标

### 1.1 一期目标
一期只建立一条可运行、可验收、可回滚的最小内容生产闭环，目标不是做全平台运营系统，而是把以下主链路稳定落地：

`发现 -> 选题 -> 内容 -> 图片 -> 发布检查 -> 复盘`

该闭环必须满足四个项目级结果：

1. 每一步都有明确输入、输出、状态和责任对象。
2. 每一个领域对象都必须落库，不能依赖仅存在于内存或临时文件中的中间结果进入下一步。
3. 发布检查必须作为强 gate 实现，不能被页面跳过，也不能被接口绕过。
4. 后续 Stitch 页面、Codex 工程实现、测试验收都围绕这条主链路展开，不额外引入平行链路。

### 1.2 最终系统约束对齐

#### 已确认事实
- 本地 PRD 已确认一期核心能力为发现、选题、内容、图片、发布检查、复盘。
- Codex 启动执行包已确认一期固定主链路为 `发现 -> 选题 -> 内容 -> 图片 -> 发布检查 -> 复盘`。
- Stitch 启动执行包已确认页面对象流必须可追踪为 `signal -> topic -> content_variant -> image_asset -> publish_check -> retro_record`。
- PRD 与启动执行包都已确认发布检查必须具备 `PASS / WARN / BLOCK` 结果，并与内容、图片、平台适配和复盘有关联。
- 已收到《流量工厂｜最终系统约束补充 #001》，并以该约束作为一期正式收敛口径。

#### 本版判断
- 一期项目版以 `signal -> topic -> content_variant -> image_asset -> publish_check -> retro_record` 作为唯一有效对象主链。
- 一期不单独建设复杂“分发系统”，外部平台发布动作先视为系统外人工执行；系统内只负责“发布准备完成”和“发布后复盘记录”。
- 为满足“所有对象必须落库”的硬约束，主链上的每一个对象都必须有独立表和主键，不允许仅通过日志文件或缓存承接下游流程。

#### 待验证事项
- 当前无新增待验证事项；后续若出现新约束，应以《最终系统约束补充》编号版本覆盖。

### 1.3 强制规则
1. 不允许跳过主链路。任一页面和任一接口都不得直接从 `signal` 跳到 `content_variant`，或从 `content_variant` 跳过 `image_asset` 直接进入复盘。
2. 所有对象必须落库。只有已持久化对象才能成为下一步输入。
3. 发布检查是强 gate。未形成有效 `publish_check` 记录的内容包不得进入“可发布”状态。
4. 所有页面必须服务主链路。页面入口、CTA、状态栏和详情区都必须能说明“当前对象、当前状态、下一步动作”。
5. 所有对象关系必须可审计。下游对象必须能回溯到其直接上游和主链源头。

## 2. 主链路定义

### 2.1 主链路步骤

| 步骤 | 输入 | 输出 | 落库对象 | 进入下一步条件 |
| --- | --- | --- | --- | --- |
| 发现 | 外部来源抓取结果、人工录入线索 | 结构化 `signal` | `signals` | `signal.status = READY_FOR_TOPIC` |
| 选题 | 已落库 `signal` | 已确认 `topic` | `topics` | `topic.status = READY_FOR_CONTENT` |
| 内容 | 已落库 `topic` | 至少一个 `content_variant` | `content_variants` | 存在 `content_variant.status = READY_FOR_IMAGE` |
| 图片 | 已落库 `content_variant` | 至少一个 `image_asset` | `image_assets` | 存在 `image_asset.status = READY_FOR_CHECK` |
| 发布检查 | 已落库 `content_variant`，若存在图片则附已落库 `image_asset` | `publish_check` 和检查明细 | `publish_checks`、`publish_check_items` | `publish_check.result in (PASS, WARN)` |
| 复盘 | 已通过 gate 的 `publish_check`，以及人工录入的发布结果 | `retro_record` | `retro_records` | `retro_record.status = CLOSED` |

### 2.2 主链路对象关系

| 上游对象 | 下游对象 | 一期关系 | 说明 |
| --- | --- | --- | --- |
| `signal` | `topic` | 1:N | 一个信号可以演化出多个选题，但每个 `topic` 必须来源于一个已落库 `signal` |
| `topic` | `content_variant` | 1:N | 一个选题至少可生成多个内容版本，每个 `content_variant` 只能归属于一个 `topic` |
| `content_variant` | `image_asset` | 1:N | 一个内容版本可对应多个图片资产，每个 `image_asset` 只能归属于一个 `content_variant` |
| `content_variant` | `publish_check` | 1:N | 每次送检都必须绑定一个 `content_variant`，不允许脱离内容版本单独创建检查 |
| `image_asset` | `publish_check` | 1:0..N | 当内容版本存在图片资产时，检查记录应同时绑定该 `image_asset` |
| `publish_check` | `retro_record` | 1:0..1 | 一期默认一次有效发布检查对应一条复盘记录；多平台多次发布放到后续阶段扩展 |

### 2.3 页面流转规则
1. `Discovery（Signal）` 只能从 `signal` 发起“转为 Topic”。
2. `Topic Pool（Topic）` 只能从 `topic` 发起“进入 Content Lab”。
3. `Content Lab（ContentVariant）` 只能基于已选中的 `content_variant` 发起“进入 Image Lab”。
4. `Image Lab（ImageAsset）` 只能基于已选中的 `image_asset` 发起“送检”。
5. `Quality Gate（PublishCheck）` 只能基于已落库的 `content_variant` 执行；若存在图片，则需同时绑定 `image_asset`。
6. `Retrospective（RetroRecord）` 只能针对 `PASS` 或 `WARN` 的 `publish_check` 创建 `retro_record`。

### 2.4 状态推进规则
1. 主链每一步都必须有显式状态字段，状态推进只能前移或回退到直接上游，不能跨级跳转。
2. 下游对象创建成功后，上游对象状态要同步更新为“已流转”或“待回修”。
3. `BLOCK` 检查结果只能让流程回退到内容或图片，不允许继续前推。
4. `WARN` 检查结果允许继续前推，但必须同步落库风险记录和建议动作。
5. `retro_record` 创建后，主链视为一次完整闭环完成。

## 3. 核心领域对象

### 3.1 `signal`
- 核心字段：`id`、`source_type`、`source_ref`、`title`、`summary`、`source_url`、`captured_at`、`tags_json`、`normalized_hash`、`status`、`created_at`、`updated_at`
- 谁创建：发现模块、来源适配器、人工补录
- 谁使用：选题模块、复盘模块（回看源头）
- 与上下游关系：一个 `signal` 可派生多个 `topic`；没有 `signal_id` 的 `topic` 不允许创建

### 3.2 `topic`
- 核心字段：`id`、`signal_id`、`title`、`angle`、`priority`、`target_platform`、`decision_note`、`status`、`created_at`、`updated_at`
- 谁创建：选题模块
- 谁使用：内容模块、复盘模块、发布检查模块
- 与上下游关系：必须归属一个 `signal`；可拥有多个 `content_variant`

### 3.3 `content_variant`
- 核心字段：`id`、`topic_id`、`variant_type`、`platform`、`title`、`body`、`style_profile`、`revision_no`、`status`、`created_at`、`updated_at`
- 谁创建：内容模块、能力层调用结果
- 谁使用：图片模块、发布检查模块、复盘模块
- 与上下游关系：必须归属一个 `topic`；可拥有多个 `image_asset`

### 3.4 `image_asset`
- 核心字段：`id`、`content_variant_id`、`asset_type`、`template_id`、`storage_path`、`prompt_snapshot`、`width`、`height`、`status`、`created_at`、`updated_at`
- 谁创建：图片模块、图像能力适配器
- 谁使用：发布检查模块、复盘模块
- 与上下游关系：必须归属一个 `content_variant`；只有 `READY_FOR_CHECK` 的图片资产才能进入送检

### 3.5 `publish_check`
- 核心字段：`id`、`content_variant_id`、`image_asset_id`、`topic_id`、`platform`、`result`、`problem_summary`、`suggested_action`、`risk_note`、`check_version`、`block_count`、`warn_count`、`pass_count`、`checked_at`、`created_at`
- 谁创建：发布检查模块
- 谁使用：复盘模块、页面状态栏、导出动作
- 与上下游关系：必须绑定 `content_variant_id`；若存在图片则必须绑定 `image_asset_id`；`topic_id` 可作为查询索引冗余保存；没有检查记录不得形成“可发布”状态

### 3.6 `retro_record`
- 核心字段：`id`、`publish_check_id`、`signal_id`、`topic_id`、`content_variant_id`、`image_asset_id`、`publish_result_summary`、`metrics_json`、`insight`、`next_action`、`status`、`created_at`、`updated_at`
- 谁创建：复盘模块、人工录入发布后结果
- 谁使用：选题模块、内容模块、策略回看
- 与上下游关系：必须归属一个有效 `publish_check`，并冗余保存主链关键信息以便审计和查询

### 3.7 支撑对象

#### `publish_check_item`
- 作用：记录每个检查项的分类、结果、建议和是否阻断
- 核心字段：`id`、`publish_check_id`、`rule_code`、`rule_category`、`severity`、`result`、`message`、`suggestion`

#### `execution_record`
- 作用：记录技能调用、适配器调用和回退链路，满足审计要求
- 核心字段：`id`、`capability_name`、`provider_name`、`input_ref`、`output_ref`、`status`、`started_at`、`ended_at`

### 3.8 全对象落库规则
1. 主链对象全部采用数据库主表持久化，不允许只存文件路径而没有数据库记录。
2. 图片文件、报告文件、导出文件可以落在 `artifacts/`，但必须在数据库中有对应索引记录。
3. 检查明细、人工 override、能力执行记录必须入库，不能只写终端日志。
4. 下一步页面只读取持久化对象，不读取上一步未保存的表单草稿作为唯一真源。

## 4. 模块边界

### 4.1 业务模块
- `discovery`：负责来源接入、信号清洗、`signal` 建立与状态更新
- `topic`：负责 `signal` 评估、`topic` 创建、优先级管理
- `content`：负责 `content_variant` 生成、改写、版本管理
- `image`：负责 `image_asset` 生成、模板选择、资产保存
- `check`：负责 `publish_check`、`publish_check_item`、override 和 gate 决策
- `retro`：负责 `retro_record` 创建、结果回看、策略沉淀

### 4.2 支撑模块
- `skills`：能力注册与路由，不直接承载业务状态
- `adapters`：来源、模型、图片、导出等外部依赖适配
- `workflows`：串联主链路的状态推进和校验
- `tests`：单元、集成、流程验收测试
- `docs`：项目定义、实施方案、验收记录

### 4.3 边界约束
1. 业务模块只处理本领域对象，不直接读写其他模块的内部实现细节。
2. `check` 模块是全链路 gate，但不是万能服务；它只读取必要对象快照并输出检查记录与决策。
3. `skills` 不能直接写业务数据库；必须经由业务服务层提交落库。
4. `workflows` 负责流程推进，但不能绕开领域校验直接改状态。

## 5. 发布检查模块定义

### 5.1 检查对象
一期检查对象是“待发布内容包”，其核心绑定关系如下：

1. 必须绑定 `content_variant`
2. 若存在图片，则应同时绑定 `image_asset`
3. `topic` 作为上游上下文参与检查和索引，但不替代 `content_variant` 成为最低检查锚点

平台参数作为检查上下文写入 `publish_check.platform`，但不单独升级为一期核心领域对象。

### 5.2 检查分类
一期至少保留六类核心检查：

1. 内容质量检查：标题强度、信息完整性、CTA 清晰度
2. 图文一致性检查：图片与文案主题是否一致
3. 平台适配检查：字数、结构、格式、尺寸是否满足平台要求
4. 风险合规检查：违禁词、敏感表达、夸张承诺
5. 账号定位检查：内容是否偏离账号主题或目标受众
6. 重复与冗余检查：与历史内容高度重复或内部表达重复

### 5.3 结果模型
- `PASS`：所有检查项通过，可以进入下一步
- `WARN`：无阻断项，但存在风险，允许进入下一步，且必须记录风险
- `BLOCK`：存在至少一个阻断项，当前内容包不得进入下一步

### 5.4 强 gate 规则
1. 只有存在最新有效 `publish_check` 记录时，系统才允许标记“可发布”。
2. `BLOCK` 时必须禁止下游动作，页面按钮置灰，接口返回业务错误。
3. `WARN` 时允许继续流转，但必须保留风险说明、问题列表和建议动作。
4. `PASS` 和 `WARN` 都允许进入“待复盘”或“待发布结果录入”状态。
5. 任意上游对象变更后，历史 `publish_check` 自动失效，必须重新送检，并生成新的检查记录；旧记录只能失效，不能覆盖。

### 5.5 检查记录层
一期至少分三层：

1. 检查头记录：`publish_check`
2. 检查明细：`publish_check_item`
3. 版本与失效记录：保存 `check_version` 和旧记录失效状态，保证重检可追溯

### 5.6 与其他模块关系
- 与 `content`：文案改写后必须重跑检查
- 与 `image`：图片替换后必须重跑检查
- 与 `platform`：平台规则以配置方式注入检查上下文
- 与 `retro`：复盘必须读取最近一次有效检查结果，作为结果解释依据

## 6. skills 能力层定义

### 6.1 目标
一期只解决“能力接入统一、可替换、可记录”，不做复杂编排平台。

### 6.2 最小能力组件
- `SkillRegistry`：登记可用能力、能力编码、输入输出协议
- `CapabilityAdapter`：封装外部模型、抓取器、图像工具等能力调用
- `ProviderRouter`：按能力类型和配置选择具体 provider
- `FallbackPolicy`：当首选 provider 失败时决定是否回退
- `ExecutionRecord`：记录每次能力执行的输入引用、输出引用、状态与耗时

### 6.3 强约束
1. 业务模块不能直接硬编码调用某个模型 SDK。
2. 所有能力调用必须留下 `execution_record`。
3. 业务对象最终落库必须由领域服务完成，能力层只返回结果载荷。

## 7. 测试边界

1. 测试数据只能读取 `data/testdata/` 或测试夹具目录。
2. 测试不得读取真实 `runtime/`、`reports/`、`artifacts/` 中的运行产物。
3. 主链路必须至少覆盖一条从 `signal` 到 `retro_record` 的最小集成测试。
4. 发布检查必须有专项测试，覆盖 `PASS`、`WARN`、`BLOCK`、风险记录和重检保留旧记录。
5. 页面流转必须有基本端到端测试，验证不可跳步和按钮状态。

## 8. 运行边界

### 8.1 目录职责
- `app/`：接口、路由、页面入口
- `domain/`：领域对象、仓储接口、状态规则
- `services/`：业务服务和流程编排
- `skills/`：能力注册和路由
- `adapters/`：外部接入层
- `workflows/`：主链路工作流
- `tests/`：测试代码
- `docs/`：方案、定义、验收文档
- `data/`：种子数据、测试数据、数据库文件
- `runtime/`：本地运行态缓存和临时状态
- `reports/`：测试报告、验收报告
- `artifacts/`：图片、导出文件、检查附件

### 8.2 Git 边界
必须进 git：
- `app/`
- `domain/`
- `services/`
- `skills/`
- `adapters/`
- `workflows/`
- `tests/`
- `docs/`
- `data/seeds/`
- `data/testdata/`
- 配置模板与脚本

必须 ignore：
- `runtime/**`
- `reports/**`
- `artifacts/**`
- `data/runtime/**`
- 本地数据库快照、临时导出、日志文件

## 9. 一期验收定义

1. 主链路验收：可从一个已落库 `signal` 完整走到 `retro_record`。
2. 对象验收：六个核心对象都有独立表、主键、状态和上游关联。
3. Gate 验收：没有有效 `publish_check` 不能形成“可发布”；`PASS/WARN` 允许进入下一步，`BLOCK` 必须阻断。
4. 页面验收：任一页面都能看到当前对象、当前状态、下一步动作，且不能跨级跳转。
5. 审计验收：检查记录、能力执行记录、复盘记录可回溯到同一条主链。
6. 测试验收：主链路基础测试、发布检查专项测试、页面基本流转测试全部通过。
