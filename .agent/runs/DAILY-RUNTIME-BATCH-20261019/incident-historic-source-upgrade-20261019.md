# 事故登记：受保护历史源被误升级

- 登记时间：2026-10-19 20:53 CST（2026-10-19 12:53 UTC）
- 级别：治理违规写入（非生产环境，未造成对外服务中断）
- 状态：写入已停止；恢复方式待所有者裁决

## 事实

| 项目 | 内容 |
|---|---|
| 载体 | compose 项目 `sc-backend-odoo-dev`，数据库容器 `sc-backend-odoo-dev-db-1` |
| 数据库 | `sc_demo`（与 duty 同名，属声明中的 `protected_historic_sources`） |
| 写入时间 | 2026-10-19 12:49:12–12:51:32 UTC（20:49–20:51 CST） |
| 写入动作 | `make mod.upgrade MODULE=smart_core,smart_construction_core`（级联） |
| 触发入口 | `make daily.runtime.published_face.converge` 的远端升级步骤 |
| 直接原因 | 远端 make 读取 `.env.dev`，其 `COMPOSE_PROJECT_NAME=sc-backend-odoo-dev`、`DB_USER=odoo` 覆盖了 duty 绑定 |
| 治理依据 | `config/ops/daily_runtime_database_duties.v1.json` 的 `protected_historic_sources` 明确要求该载体不得 rename / clean / migrate / upgrade / seed |

## 证据（只读）

`sc-backend-odoo-dev-db-1` 中 `ir_module_module`：

```
smart_core|installed|17.0.1.1.17|2026-10-19 12:49:27.454337
smart_construction_core|installed|17.0.0.171|2026-10-19 12:50:56.973997
smart_construction_demo|uninstalled||2026-10-19 12:43:32.908407
```

同库约 400 条模块记录的 `write_date` 被统一刷新为 `2026-10-19 12:49:12.660453`（模块清单批量更新）。
该栈的 `odoo` 服务当前未运行，仅 db/redis 存活，没有对外服务消费者。

对照：duty 库 `sc-demo-dev-db-1/sc_demo` 的 `smart_core` 写入时间为 `2026-10-19 11:16:01`，未被本次误写覆盖。

## 影响评估

- 受影响范围是该历史源的模块注册表与模块自有元数据；升级命令未显式针对业务表。
- 模块升级可能重新加载 `noupdate=0` 的模块自有 XML 记录，因此不能声称业务数据“完全未变”。
- 未发现该载体被当前运行入口引用；不影响 18081 对外服务。
- 未执行任何进一步写入、修复或清理。

## 恢复点

- 最新完整备份：`/opt/projects/backups/20261005T023211-pre-user-acceptance-sc_demo/sc_demo.pgdump`（2026-10-05，约 487 MB）。
- 更早备份存在于 `/data/backups/dba-rec-01/20260715T132929Z/sc_demo.dump` 等路径。
- 恢复到 2026-10-05 会丢弃此后 14 天的历史数据，属破坏性操作，本轮不执行。
- 该载体是否还有 PITR/WAL 归档，未核实；在核实前不得假定可精确回滚。

## 已实施的防复发措施

`scripts/ops/daily_runtime_published_face_converge.py` 远端步骤改为：

1. 从 duty 声明解析 duty，得到 carrier、数据库角色和 duty 自己的环境文件；
2. duty 环境文件的 `COMPOSE_PROJECT_NAME`/`DB_USER`/`DB_NAME` 与声明不一致即 BLOCKED；
3. 操作员传入的环境文件若声明了其他 carrier，直接 BLOCKED（`OPERATOR_ENV_CARRIER_MISMATCH`）；
4. make 命令行绑定 duty 环境文件、carrier、角色，不再让 `.env.dev` 的值进入远端环境；
5. 证据必须回带 `duty`/`duty_carrier`/`duty_database_role`，本地入口校验不一致即拒绝。

对应单测：`scripts/ops/test_daily_runtime_published_face_converge.py`（32 项通过）。

## 待所有者裁决

1. 是否接受该历史源保持现状并登记漂移；
2. 是否用 2026-10-05 备份覆盖恢复（会丢弃 14 天历史）；
3. 是否先补一次该载体的独立快照/导出再决定。
