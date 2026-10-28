# FEPC-04 角色首页证据索引

## 运行时身份

- Demo source_revision `3f46dd7e`，前端构建 `5690cde9`
- 视口 1440×960，Chromium headless

## 截图

| 文件 | 内容 |
| --- | --- |
| /tmp/fepc04/demo_role_project_manager.png | 项目经理首页 |
| /tmp/fepc04/demo_role_project_a_member.png | 项目成员首页 |
| /tmp/fepc04/demo_role_owner.png | 企业负责人首页 |

## 关键读数

- 三个角色均含：当前状态、今日工作、风险与提醒、我的项目与业务对象、常用入口与最近访问、工作入口。
- 风险区：项目经理/成员为“风险处置”，企业负责人为“项目风险预警”。
- 工作入口：三个角色均为“暂无首页快捷入口”。

## 契约与代码引用

- `smart_core/core/workspace_home_contract_builder.py`：system.init 的 workspaceHome 契约。
- `smart_construction_core/services/workspace_contract_builder.py`：workspace.home.enter handler 契约。
- `smart_construction_core/core_extension_system_init_rows.py` `build_risk_action_rows`：风险区 fallback。
- `frontend/apps/web/src/components/role-home/WorkspaceHome.vue` + `composables/shared-surface/useWorkspaceHome.ts`：实际渲染。
