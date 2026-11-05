# NAV-UX-01 场景化中心导航交付收口

## 目的

把场景化导航从“6 域 hand JSON 投影 + 新旧导航二选一”收敛为“原生菜单树中心 + 数据库维护业务场景 + 统一前端消费”的一条交付链，并恢复搜索、展开记忆、当前位置定位与权威空态/错误态。

## 批次范围

- 后端：`sc.product.scenario` / `sc.product.scenario.entry` 模型、视图、权限、种子导入、policy 同步 create-only。
- 投影：`scenario_surface_projection.project_authorized_nav_with_env`，中心取原生 `ir.ui.menu` 父级链，场景取数据库模型。
- 前端：`AppShell` 单一场景导航消费，`ProductScenarioNavigation` 中心→场景→入口 + 搜索/展开/定位，`session` 展开持久化。

## 验证状态

- 静态：py_compile / manifest / XML / CSV / vue-tsc / eslint 通过。
- 定向：`verify.nav01.native_authority.unit`、`verify.frontend.workspace_scenario_lifecycle.unit` 通过。
- 运行时：未执行。阻塞为受管环境挂载 `mainline-deploy` 而非本分支，待合入 main 后按受管流程验证。
