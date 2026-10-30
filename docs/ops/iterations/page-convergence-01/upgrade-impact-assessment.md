# PAGE-CONVERGENCE-01A · smart_construction_core 升级副作用评估

评估对象：`feature/page-convergence-01` 相对 `main` 的 `smart_construction_core` 差异。

## 变更文件

| 文件 | 类型 | 升级副作用 |
| --- | --- | --- |
| `models/core/project_core.py` | Python 方法（`action_view_stage_requirements`） | 无 schema/字段/迁移；重启即生效 |
| `views/core/project_overview_views.xml` | 表单视图 arch（分组、标签、卡片） | 写入 `ir.ui.view.arch_db`，`arch_prev` 由 Odoo 保留 |

## 核对结论

- 无 `_inherit` 新增字段、无 `_auto_init`、无 SQL 视图、无迁移脚本。
- 无 `data/*.xml`、`security/*.xml`、`ir.model.access` 变更 → 不写业务数据、不改 ACL/record rule。
- 无 cron、queue、缓存、附件或外部集成变更。
- 视图升级只改 `ir.ui.view` 与 `arch_prev`，可逆（保留旧 arch）。

## 恢复边界

- 目标库：`sc_dev_demo`（项目 `sc-local-dev`），持久开发演示库。
- 受管备份入口：`make local.dev.snapshot`；执行升级前必须生成并回读一次快照，
  确认可恢复后，再执行 `make local.dev.upgrade MODULE=smart_construction_core`。

## 停止条件

若快照生成或回读失败、恢复路径不可验证、或出现未界定的数据迁移，则不执行升级。

