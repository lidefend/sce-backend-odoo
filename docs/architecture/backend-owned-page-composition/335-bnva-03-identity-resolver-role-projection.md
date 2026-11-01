# 335 · BNVA-03 IdentityResolver Role Projection

## 合并规则

- 允许字段（landing_scene_candidates / primary_menu_xmlids / contextual_* / admin_*）：有序并集。
- 拒绝字段（denied_* / blocklist）：有序交集。
- 角色优先级：system_admin, experience, business_full, business_config_admin, executive, owner, pm, finance, cost, accounting。
- NAV_MENU_SCENE_MAP 将菜单 xmlid 映射到 scene key（如 menu_sc_project_initiation → projects.intake）。

## 回归样板

项目发起入口缺失已被证明是 `pm.primary_menu_xmlids` 投影漏列，而非合并机制错误。
