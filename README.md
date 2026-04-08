# 流量工厂 v2

## 当前状态

本仓已完成一期主线（002-009）与条件修正卡（C01、C02），当前处于收尾清理阶段，目标是达到“一期可交付整理完成”。

一期固定主链路：

`信号 -> 选题 -> 内容版本 -> 图片资产 -> 发布检查记录 -> 复盘记录`

对应模型：

`Signal -> Topic -> ContentVariant -> ImageAsset -> PublishCheck -> RetroRecord`

## 一期固定约束

1. 不允许无信号创建选题。
2. 不允许无选题创建内容版本。
3. 不允许无内容版本创建图片资产。
4. 不允许无发布检查记录创建复盘记录。
5. 不允许跳步。
6. 所有主链对象必须落库。
7. 发布检查是强闸门，不是提示层。
8. 修改内容版本或图片资产后，旧检查记录失效，必须新增发布检查记录，不能覆盖旧记录。

发布检查状态固定为：`通过 / 警告 / 拦截`。

## 当前工程落点

- `app/api/`：最小接口入口与路由（6 个核心模块）。
- `app/web/pages/`：6 个页面骨架与最小动作联动入口。
- `app/web/action_bridge.py`：页面动作到接口的桥接层。
- `domain/`：领域对象、规则与 SQLite 仓储。
- `services/`：主链服务、发布检查服务、能力桥接服务。
- `workflows/`：主链工作流编排。
- `skills/` 与 `adapters/providers/`：技能能力层最小骨架与 provider 占位。
- `tests/`：一期最小测试边界、主链验证、发布检查专项、页面联动验证。

## 事实源

1. `docs/phase1-minimal-system-definition.md`
2. `docs/phase1-implementation-plan.md`
3. `docs/repo-boundaries.md`
4. `stitch/`（仅设计输入资产，不作为运行页面目录）

## 常用命令

```bash
# 初始化数据库（默认 data/runtime/traffic_factory.sqlite3）
python3 scripts/init_db.py

# 运行全量测试
python3 -m unittest discover -s tests -p "test_*.py"

# 启动本地服务
python3 -m app.main --host 127.0.0.1 --port 8787 --db-path data/runtime/traffic_factory.sqlite3
```
