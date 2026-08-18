# .agent 工程上下文（P0 恢复工作副本）

## 仓库定位

`sce-backend-odoo` 的恢复/桥接工作副本：P0 UI5 场景基础恢复 v2 + 场景组件桥 v1 +
canonical effective primary v1。目录名本身记录变更谱系。

## 血缘规则

- 父仓库：`sce-backend-odoo`（权威实现所在）
- 本副本只承载恢复/桥接任务期间的改动，任务结束后回流父仓库或整体归档
- 禁止与父仓库长期并行演进造成分叉

## AI 工作原则

执行策略以本仓库根目录 `AGENTS.md` 与 `ARCHITECTURE_GUARD.md` 为准。

## 本目录约定

- `context.yaml`：仓库身份、血缘关系与权威路径
- `goals/`、`workflows/`、`runs/`：涉及本仓库的工程任务按需创建
