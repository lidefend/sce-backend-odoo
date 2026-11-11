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

## 实现结果

- `sc.product.scenario.entry` 的数据库约束从 `unique(menu_id)` 改为
  `unique(scenario_id, menu_id)`。同一原生菜单可以拥有多条场景引用，每个引用只维护
  本场景内的中心、意图和顺序。升级迁移会删除旧的一菜单一场景约束。
- `smart_construction_scene` 新增 authority finalizer：在最终导航过滤前读取当前公司的
  `business.v1:<scenario>` 选择，只保留已启用场景已有授权入口。该逻辑位于场景责任层；
  `smart_core` 只提供通用 finalizer 挂点，编译器和直接路由 authority 使用同一实现。
- 同一菜单被多个已启用场景引用时，以
  `scenario.sequence -> entry.sequence -> scenario_key -> intent -> entry.id`
  选出唯一显示位置；其他启用位置进入 `scenario_composition.shared_by_menu` 诊断，
  不静默丢弃。
- 工作区壳入口和系统配置中心入口通过原生 `ir.ui.menu.sc_scenario_exempt` 精确声明为
  直连事实。My Work 仍只要求 `base.group_user`；企业初始化和配置中心仍只要求
  `group_sc_cap_business_config_admin`。豁免不绕过发布、ACL、记录规则或执行时业务条件。
- 直连入口使用原生 `ir.ui.menu.sequence`，场景入口使用场景声明 sequence。`0` 是合法
  显式顺序，不再被 `or 10`、`_positive_int` 或节点构建器误判为缺省值。
- 场景 seed 在重置 marker 后不会给已经被维护到其他场景的菜单重新补旧绑定；同一 menu
  在首次初始化中可以进入多个场景，但已有任一维护绑定时不自动扩张。

## 运行时证据

`sc_dev_demo` 已完成 `17.0.0.180` 升级：

- 17 个业务场景、79 条场景入口；数据库约束为 `unique(scenario_id, menu_id)`。
- 14 个工作区/平台直连入口均有精确豁免，`runtime_menu_scope` 均识别为 `exempt`。
- 当前租户只启用 `business.v1:payment.capital`，最终场景选择只出现该场景。
- Business Config Admin 收到企业初始化；Business Full 不收到该配置中心入口。
- 当前维护中的 dev 产品策略仍是历史 91 入口快照，本批没有覆盖管理员维护策略。
  当前源码 92 入口策略的 My Work/企业初始化行为由验收事务同步当前策略后验证。

受管验收库 `sc_frontend_acceptance` 升级后执行
`make acceptance.frontend.fixture_orm`：**49 tests，0 failed，0 errors**。覆盖：

- 一菜单多场景、同场景内唯一约束；
- 租户启用/停用对启动导航和直接路由 authority 的同步裁剪；
- 共享能力最终只出现一次及替代位置诊断；
- My Work 对 internal user、企业初始化对 Business Config Admin 的可见性；
- Business Full 不获得配置中心菜单；
- 场景中心不再随原生 menu 迁移，直连入口按原生 sequence 排序；
- 场景中心和入口的 `scenario.sequence`、`entry.sequence` 都支持显式 `0`。

## 验证与交付车道

| 检查 | 结果 |
| --- | --- |
| `verify.navigation.publication_consumers.unit` | PASS，173 tests |
| `verify.scenario.center_projection.guard` | PASS，7 tests |
| `verify.backend.navigation_delivery.unit` | PASS，76 tests |
| `verify.daily.permission_truth.capability.orm` | PASS，13 tests |
| `acceptance.frontend.fixture_orm` | PASS，49 tests |
| `local.dev.upgrade` | PASS，schema/migration/authority readback |
| `ci.local.iteration` | BLOCKED，旧交付规划器不映射本批新增迁移/数据/测试路径 |

`ci.local.iteration` 的失败属于 `validation_tool_defect`。当前分支基线早于已经进入最新
主线的 P4 交付车道修复；本批没有把 P4 修补混入 P0/P1 产品提交。集成最新主线后必须
重新执行受影响门禁，不能把本次定向通过表述为远端 CI 或交付完成。

## 回退

代码回退恢复旧的单场景约束和原 authority 链；数据库升级会移除旧唯一约束，
数据行本身不删除。回退到旧代码前必须确认每个 menu 只有一个场景引用，或通过受管迁移处理。
新增的直连事实豁免是精确 XMLID 的一次性声明，管理员后续撤销不会被普通升级恢复。
本批不执行主线集成、发布、部署或远端写入。
