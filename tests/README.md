# 测试边界说明

本目录承接一期最小可验证体系，覆盖主链路、发布检查强闸门、接口最小行为、页面动作联动与能力层骨架稳定性。

## 目录职责

- `support.py`、`conftest.py`：注入测试临时 SQLite，阻断真实运行目录访问。
- `unit/`：规则与边界单测（含页面路由-动作映射和页面关键文案校验）。
- `integration/`：主链路正负向、发布检查专项、接口最小调用、页面动作桥接集测。
- `e2e/`：仅保留占位，不落复杂端到端自动化。

## 测试边界口径

1. 测试数据库只能来自测试临时目录，不允许连接 `data/runtime/`。
2. 测试数据来源限定为 `data/testdata/minimal_chain_cases.json` 与测试夹具。
3. 测试过程中禁止读写 `runtime/`、`reports/`、`artifacts/`、`data/runtime/`。
4. 数据库连接采用显式关闭策略，避免测试结束后残留连接告警。

## 运行命令

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```
