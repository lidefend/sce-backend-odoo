# 多场景能力复用与租户编排权威

## 批次目标

本批只处理“事实完整、编排不足”的问题：同一个已经存在的 Odoo
`ir.ui.menu / ir.actions` 能力可以被多个业务场景引用，但原生事实仍只有一份。
租户对业务场景的选择在场景责任层完成，`system.init` 只编译已经完成的选择结果。

责任边界：

- P0 `smart_core`：提供通用 authority finalizer 挂点，并把完成后的 authority
  封印为唯一最终导航契约。
- P1 `smart_construction_core/scene`：维护场景对原生能力的引用、中心、意图、
  顺序及租户选择，不生成 menu/action/route/model/group/ACL 事实。
- Frontend：继续只消费最终 `navigation.nav`，不补菜单、不去重、不推断场景。

## 验收行为

- 同一 `(scenario_id, menu_id)` 唯一；同一 menu 可被多个 scenario 引用。
- 当前租户只消费已启用场景产生的入口；停用或未启用场景不能进入最终导航或直接路由授权。
- 同一原生 menu 被多个已启用场景引用时，最终导航只出现一次；放置顺序由场景和入口声明顺序确定，
  其余可选放置作为诊断输出，不能静默丢失。
- 缺少场景归属且未显式豁免时仍按 `BUSINESS_SCENARIO_CONFIGURATION_MISSING` fail-closed。
- `system.init` 不重复执行业务场景选择；启动导航与直接路由授权使用同一最终 authority。

## 回退

代码回退恢复旧的单场景约束和原 authority 链；数据库升级会移除旧唯一约束，
数据行本身不删除。回退到旧代码前必须确认每个 menu 只有一个场景引用，或通过受管迁移处理。
本批不执行主线集成、发布、部署或远端写入。
