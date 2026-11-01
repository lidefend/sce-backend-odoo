# 321 · BNVA-03 Navigation Authority Chain

## 权威链

Odoo 原生 `ir.ui.menu` / `ir.actions.act_window` / `ir.ui.view`（唯一原生事实）
→ `IdentityResolver`（用户组 xmlids）
→ `NavDispatcher.build_nav`（根归一 → 节点归一 → action/model/xmlid 富化 → scene/groups 过滤 → 排序 → 去路由整形）
→ `DeliveryEngine.build` → `MenuService.build_nav` → `delivery_engine.nav`
→ `runtime_route_authority`（primary / role_home / contextual / admin / denied / menu_containers）
→ 前端 `routeAuthority.ts` / `canonicalNavigation.ts` / `useWorkspaceHome.ts`

## 关键定性

- `NavDispatcher` 声明 `projection_only=True`、`rebuildable=True`、`no_business_fact_authority=True`，
  自定义导航是可重建投影，不是第二菜单权威。
- 前端 `routeAuthority.ts` 声明消费层 `P0:smart_core:MenuService.build_route_authority`，缺失时
  `contractGapError` fail-closed。

## 定向测试

- test_route_authority_single_consumer：13 项 OK。
- test_menu_configuration_audit：51 项 OK。
