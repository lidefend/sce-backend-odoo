# PAGE-CONVERGENCE-01 / P5 · 阶段要求只读前端呈现（实施）

结论：后端 `action_view_stage_requirements` 返回 tree-only 只读 act_window 已正确路由到列表
（`/a/822`）；剩余缺陷是只读 `context={create:false, edit:false, delete:false}` 未投射到列表
操作入口，导致「新建」「编辑」入口误显。本轮在 Action 运行层消费该上下文，最小修复完成。

## 一、根因

- 后端动作返回 `ir.actions.act_window`，`view_mode=tree`、`target=current`、`context=
  {create:false, edit:false, delete:false}`，语义正确。
- 前端 `ActionView` 的 `canCreateRecord` / `canEditRecord` 只读契约
  `effectiveRecordCapabilities`，未消费路由 `context_raw` 中显式声明的只读能力，
  因此列表仍显示「新建」并可编辑。

## 二、最小修复

仅改 `frontend/apps/web/src/views/ActionView.vue`：

1. 新增 `parseOdooDictLiteral`：安全解析 Odoo Python dict 字面量（`{'create': False,...}`）。
2. 新增 `routeContextOperationAllowed(operation)`：读取路由 `context_raw`，若该操作被显式
   声明为 false/0，则返回 false。
3. `canCreateRecord` 叠加 `routeContextOperationAllowed('create')`；`canEditRecord` 叠加
   `routeContextOperationAllowed('edit')`。

不新增列表渲染器、不硬编码模型、不改后端 action / ACL / 契约组装器 / 解析器。

## 三、验证

- 真实点击「查看阶段要求」：路由 `/a/822`，`data-can-create=false`、`data-can-edit=false`，
  「新建」消失，列表 5 条记录全部 `lifecycle_state=in_progress`，无 HTTP 400，无向导请求，
  控制台错误 0。
- `verify.frontend.collection_action_toolbar.unit`：PASS（31 cases + 11 tests）。
- 付款申请回归：付款申请 list action 未在 `context_raw` 声明 `create:false`，本修复是保守
  AND，仅当上下文显式关闭时才禁用，付款申请新建入口不受影响。

## 四、保留观察

「批量导入」是独立导入入口，不受 create/edit/delete 上下文控制；本轮未改动。
