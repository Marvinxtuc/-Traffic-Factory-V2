# 页面目录边界说明

一期页面按固定 6 个核心模块落地在本目录：

1. `discovery/`：发现台
2. `topic-pool/`：选题池
3. `content-lab/`：内容工坊
4. `image-lab/`：图片工坊
5. `quality-gate/`：发布检查
6. `retrospective/`：复盘台

## 当前实现口径

- 页面动作统一通过 `POST /web/actions/{action_code}` 进入桥接层，再转调接口层。
- 无上游对象时，下游动作会禁用或被接口拒绝，不允许跳步。
- 发布检查页面已结构化呈现关键状态：结果、版本号、记录状态、风险说明、最新有效标记与重检历史。

路由以 `app/web/routes.py` 为准：

- `/discovery`
- `/topics`
- `/contents`
- `/images`
- `/checks`
- `/retros`

`stitch/` 仅为设计输入资产，不承担运行页面职责。运行页面仅在 `app/web/pages/`。
