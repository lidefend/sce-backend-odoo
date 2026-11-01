# 328 · BNVA-03 Project Initiation Entry Audit

## 事实

- 原生菜单 `menu_sc_project_initiation`（id 379，新项目立项）→ `action_project_initiation`（id 795）。
- action 795：project.project，view_mode=form，view_id=1511。
- 菜单持组：`group_sc_cap_project_user`（项目中心经办）+ `group_sc_cap_project_approval`（项目中心审批）。

## 根因

`pm` 角色面（`core_extension_policy_maps.ROLE_SURFACE_OVERRIDES["pm"]`）的
`landing_scene_candidates` 已含 `projects.intake`，但 `primary_menu_xmlids` 漏列
`menu_sc_project_initiation`。这是导航投影遗漏，不是原生菜单缺失，也不是 ACL 问题。
