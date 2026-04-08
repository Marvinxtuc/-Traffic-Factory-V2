# 流量工厂 v2 上下文包

## 1. 用途

本文件是流量工厂 v2 的长期稳定上下文。

目标：

1. 让新线程可以在不回溯旧聊天记录的前提下继续工作。
2. 减少 Codex 会话因长上下文触发自动压缩。
3. 固定事实源、边界和当前协作方式，避免每轮重复灌入整包制度文本。

## 2. 线程接续规则

新线程默认只加载以下文件：

1. `docs/context-pack-v2.md`
2. `reports/phase1-current-run.md`
3. 当前目标直接相关的 1 到 3 个文件

默认不要整包重复加载：

1. `流量工厂_任务卡制度_md文件包_v2/`
2. 长篇 PRD 全文
3. 大段旧线程聊天记录
4. 与当前子任务无关的页面稿、日志和截图解释

如果线程已经出现“正在自动压缩背景信息”，本轮优先收口到文件，不继续往线程里堆材料。

## 3. 当前正式事实源

流量工厂 v2 当前正式事实源以仓库内文档为准：

1. `README.md`
2. `docs/phase1-minimal-system-definition.md`
3. `docs/phase1-implementation-plan.md`
4. `docs/repo-boundaries.md`
5. `tests/README.md`
6. `stitch/`

## 4. 当前项目目标

一期目标不是做全平台运营系统，而是先建立一条可运行、可验收、可回滚的最小内容生产闭环：

`Signal -> Topic -> ContentVariant -> ImageAsset -> PublishCheck -> RetroRecord`

当前正式约束：

1. 不允许跳步。
2. 所有主链对象必须落库。
3. `PublishCheck` 是强 gate。
4. 上游对象变更后，旧检查记录失效，必须新建检查记录。
5. 页面、接口、工作流都必须围绕同一条主链，不额外并行造新链路。

## 5. 当前仓库边界

代码边界：

1. `app/`、`domain/`、`services/`、`workflows/`、`adapters/`、`skills/` 放工程代码。
2. `stitch/` 只存页面结构稿，不作为业务代码目录。

数据边界：

1. `data/seeds/` 放可纳入版本管理的种子数据。
2. `data/testdata/` 放测试夹具。
3. `data/runtime/` 放本地数据库与临时运行数据。

运行边界：

1. `runtime/` 放本地缓存与临时状态。
2. `reports/` 放测试、验收、执行报告。
3. `artifacts/` 放图片、导出文件和运行产物。

测试边界：

1. `tests/unit/` 只做单元测试。
2. `tests/integration/` 做主链路串联测试。
3. `tests/e2e/` 做页面流转和端到端测试。
4. 测试不得读取真实 `runtime/`、`reports/`、`artifacts/`。

## 6. 当前协作规则

每个线程只处理一个窄任务，常见粒度如下：

1. 只定义一个领域对象。
2. 只落一个 service 的最小闭环。
3. 只补一组测试。
4. 只修一个边界或 gate。
5. 只做一轮验收说明。

每轮结束后，必须把结果写回 `reports/phase1-current-run.md`，而不是把完整结论留在聊天线程里。

## 7. 新线程启动建议

推荐把新线程输入收敛成如下结构：

1. 当前目标
2. 本轮不允许改动范围
3. 需遵守的边界文件
4. 需要读取的 1 到 3 个目标文件
5. 输出要求

推荐示例：

```text
继续流量工厂 v2。

只基于以下文件接续：
1. docs/context-pack-v2.md
2. reports/phase1-current-run.md
3. docs/phase1-minimal-system-definition.md

当前目标：
只完成一个窄任务，不回溯旧线程长上下文。

输出要求：
先结论，后依据；明确已确认事实、风险点、下一步。
```

## 8. 当前已知非项目问题

Codex 会话在长上下文下会触发自动压缩；该问题跨线程复发，属于会话层问题，不应误判为流量工厂 v2 仓库代码缺陷。

因此本仓推进规则是：

1. 上下文尽量写入 `docs/` 和 `reports/`。
2. 线程只保留短结论。
3. 一旦线程变重，直接切新线程继续。
