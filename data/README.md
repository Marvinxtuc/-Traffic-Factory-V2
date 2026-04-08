# 数据目录边界说明

本目录拆分为三个子区域：

- `seeds/`：可纳入版本管理的种子数据。
- `testdata/`：可纳入版本管理的测试数据。
- `runtime/`：本地运行数据库与临时运行数据。

边界要求：

1. 测试不得读写 `data/runtime/`。
2. 运行数据库默认路径为 `data/runtime/traffic_factory.sqlite3`。
3. `data/runtime/` 仅保留本地运行数据，不提交业务性运行产物。
