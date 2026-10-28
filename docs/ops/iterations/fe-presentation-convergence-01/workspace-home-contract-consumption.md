# FEPC-05 角色首页双重契约消费链只读核查

## 基线

- 本次核查的源码基线：`a49742c31d1a08e053187c1ab146ab914108ad11`
- PR 当前合入目标基线：`edb65fd1bd0bebfd45f00b236b5fa064891d3af8`
- 运行时基线：Demo `3f46dd7e`

`a49742c3` 到 `edb65fd1` 之间仅合并了 FEPC-04 的 3 个角色首页审计文档
（role-home-contract-matrix.md / role-home-findings.json / role-home-evidence-index.md），
无产品代码、契约或前端调用链变更，本核查结论在 `edb65fd1` 上仍然成立。

## 结论

归入“情况 3”：`smart_construction_core/services/workspace_contract_builder.py`
（`workspace.home.enter` handler）当前无生产消费证据，可列为候选清理项，
但删除需独立评审。`smart_core/core/workspace_home_contract_builder.py`
（system.init 返回的 `session.workspaceHome`）是权威来源。

## 调用链证据

### 权威路径（已确认生效）

- 前端路由 `/` 与 `/s/workspace.home` 均指向 `HomeView.vue`（router/index.ts:313-314）。
- `HomeView.vue` 渲染 `<WorkspaceHome />`，`WorkspaceHome.vue` 通过
  `useWorkspaceHome` 消费 `session.workspaceHome`（hero / advice / metrics /
  today_actions / risk / my_objects / ops / scene_groups / group_overview）。
- `session.workspaceHome` 由 `smart_core/core/workspace_home_contract_builder.py`
  生成（`SOURCE_KIND=workspace_home_startup_surface_projection`，经 system.init 返回）。

### 未消费路径（workspace.home.enter）

- `smart_construction_core/services/workspace_contract_builder.py` 的区块
  （metric_card / shortcut_grid / todo_list / warning_list / native_view_ref）
  由 `workspace.home.enter` handler 返回，注册于
  `smart_construction_core/core_extension_intent_handlers.py:246`。
- scene registry 声明 workspace.home 的 `intent: "workspace.home.enter"`
  （`smart_construction_scene/profiles/scene_registry_content.py:744`）。
- 但 `/s/workspace.home` 由 `HomeView.vue` 渲染，不经 `SceneView.vue` 的
  `sceneContractEntryIntent` 分支（SceneView 只处理 `/s/:sceneKey` 的其它场景）。
- 前端 `src/` 目录内无 `workspace.home.enter` 的直接 API 调用；`standard_page_type_browser.mjs`
  中的映射属测试脚本，非生产消费。

### 间接声明（运行时未触发）

- `sceneRegistry.ts:329` 会把 target.intent 解析进 SceneTarget；该 intent 仅在
  SceneView 的 entry-intent 分支和 action 导航的 open_intent 中被引用，但
  workspace.home 是专用 HomeView 路由，这两个分支对 workspace.home 不生效。

## 兼容与影响

- 引用两套契约的测试：`test_odoo_native_alignment_boundaries.py`、
  `standard_page_type_browser.mjs`、`test_scene_block_schema_contract.py` 等
  引用 workspace.home.enter / WorkspaceContractBuilder；删除前需逐项迁移或重新评审。
- 不因结构不同推断应删除；本核查只记录“当前生产路径未消费”，删除需独立评审。

## 待核实边界

- 是否存在 scene 预取 / 动态分发会在运行时触发 `workspace.home.enter`（本核查
  未在 HomeView 渲染路径发现此类调用，但未穷举全部运行时路径）。
