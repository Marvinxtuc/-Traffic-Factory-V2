# Skills Boundary

本目录承接一期能力层最小骨架，不直接承载业务对象落库。

已落地组件：

- `registry.py`：能力注册表（`content_generation`、`image_generation`、`publish_check_enhancement`）
- `router.py`：provider 路由器
- `fallback.py`：回退策略占位
- `runtime.py`：统一能力执行入口（含 execution_record 写入接线）

边界约束：

1. 不接入复杂 provider 编排。
2. 不直接写主链业务对象。
3. 必须通过服务层完成业务对象最终落库。
