# 331 · BNVA-03 Project 652 Entry Resolution

## 解析

- Action 652 = `action_sc_project_manage`（项目管理），project.project，kanban,tree,form，
  view_id=1422 = `view_sc_project_kanban_lifecycle`（kanban）。
- Action 652 无显式 act_window.view 绑定，无 productized 配置。
- 曾引用的 View 944 = `project.edit_project`（Odoo 基础项目 form）。
- `project_project_overview_form_structure_v1` 实际绑定 action 590（项目台账），不是 652。

## 结论

590 与 652 是两个独立项目入口；590 已有 productized 配置，652 是项目管理看板入口且
无 productized 配置。Identity Summary 复用问题仍待业务裁定，本轮未修改。
