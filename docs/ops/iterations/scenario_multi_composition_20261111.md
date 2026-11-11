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

`sc_dev_demo` 已完成 `17.0.0.181` 升级：

- 17 个业务场景、79 条场景入口；数据库约束为 `unique(scenario_id, menu_id)`。
- 14 个工作区/平台直连入口均有精确豁免，`runtime_menu_scope` 均识别为 `exempt`。
- 当前租户只启用 `business.v1:payment.capital`，最终场景选择只出现该场景。
- Business Config Admin 收到企业初始化；Business Full 不收到该配置中心入口。
- 当前维护中的 dev 产品策略仍是历史 91 入口快照，本批没有覆盖管理员维护策略。
  当前源码 92 入口策略的 My Work/企业初始化行为由验收事务同步当前策略后验证。

受管验收库 `sc_frontend_acceptance` 在旧候选上曾执行
`make acceptance.frontend.fixture_orm`：49 tests，0 failed，0 errors。该结果不适用于当前
候选。当前候选最近一次执行为 **49 tests，0 failed，6 errors**，失败归因为
`baseline_evidence_defect`：共享验收库尚未执行 `17.0.0.181` pre-migrate，重载 seed 时
仍能看到人员档案的旧场景绑定。必须先用受管 `acceptance.module.upgrade` 升级并回读，
再重新执行用例；不能通过放宽 seed 校验或让场景层覆盖事实来迁就旧库。

这组用例覆盖：

- 一菜单多场景、同场景内唯一约束；
- 租户启用/停用对启动导航和直接路由 authority 的同步裁剪；
- 共享能力最终只出现一次及替代位置诊断；
- My Work 对 internal user、企业初始化对 Business Config Admin 的可见性；
- Business Full 不获得配置中心菜单；
- 场景中心不再随原生 menu 迁移，直连入口按原生 sequence 排序；
- 场景中心和入口的 `scenario.sequence`、`entry.sequence` 都支持显式 `0`。

全新隔离测试库 `sc-local-test/sc_test` 执行
`TestScenarioDirectInitialization`：**6 tests PASS，0 failed，0 errors**，证明首次安装
即可生成工作区/平台直连声明，且已有场景绑定优先于直连豁免。

## 验证与交付车道

| 检查 | 结果 |
| --- | --- |
| `verify.navigation.publication_consumers.unit` | PASS，173 tests |
| `verify.scenario.center_projection.guard` | PASS，7 tests |
| `verify.backend.navigation_delivery.unit` | PASS，76 tests |
| `verify.daily.permission_truth.capability.orm` | PASS，13 tests |
| `acceptance.frontend.fixture_orm` | FAIL，49 tests 中 0 failed / 6 errors，验收库尚未升级到 17.0.0.181 |
| fresh `sc_test` direct-entry initialization | PASS，6 tests |
| fresh `sc_test` `TestProjectMemberRoleSurface` | PASS，31 tests |
| `local.dev.upgrade` | PASS，schema/migration/authority readback |
| `ci.local.iteration` | PASS，25 个受影响目标全部退出 0，110 路径未映射 0 |

## 最新主线同步与缺口收敛

候选已经通过受管 extended sync 集成 GitHub main
`19b502b487d0b646a1fc22f269b508d3224c1c3e`，并把 run baseline、完整 104 路径 scope
和旧 receipt 的失效事实更新到同一结果索引。

同步后迭代暴露并关闭了三类真实缺口：

- 前端增量规划器将本分支 35 个场景迁移、原生导航、角色暴露、验收 fixture 和守卫路径
  判为未映射。现在均路由到既有职责目标，新增行为锁后 `unmappedPathCount=0`，
  规划器单测 121 例通过。
- 发布导航守卫仍从正式产品策略读取 route，和“route 只由场景身份派生”的边界冲突。
  守卫改为从 `scene_key` 调用唯一 `scene_route()`，发布清单比较 `/s/{scene_key}`；
  正式策略若维护 route 会 fail-closed。导航策略目标通过。
- 入口发布和角色首页契约测试夹具仍假定 product policy 持久化 route，或没有注入统一
  `target_route/derive_entry_route` API。夹具现在消费同一纯路由 API，并验证已解析场景
  target 覆盖节点残留 action route；入口发布 34 例、角色首页契约 33 例通过。

最终 `make ci.local.iteration` 执行 23 个受影响目标并全部通过，包括 P0/P1 导航交付、
场景中心、`system.init` 菜单边界、角色 surface、产品菜单契约、前端 lint/严格类型、
本地 ORM 和 P4 branch-sync 工具。远端 PR、当前 HEAD 的必需 CI、合并和部署尚未执行。

PR [872](https://github.com/lidefend/sce-backend-odoo/pull/872) 发布后，远端
`frontend_release_gate` 在 `f1858dfbb` 上发现一个复查工具缺陷：
`frontend_navigation_shell_guard` 仍要求 `system.init` 内联执行 authority filter、
canonical projection 和 payload seal，而本批已经把该职责收敛到
`NavigationContractCompiler`。产品相关检查均通过，失败属于 `validation_tool_defect`。
守卫现已改为验证 `system.init` 只委托并消费封存结果，同时验证编译器内部顺序；
`verify.frontend.navigation_shell.unit` 26 tests PASS。该修复必须形成新 HEAD 并重新取得
当前 HEAD 的四项必需检查，旧 `f1858dfbb` 的失败不得被重跑成功覆盖。

更新到 `f320d2e40` 后，同一远端车道又暴露另一个同类文本断言：
`test_platform_admin_duty_contract` 仍搜索已提取的
`surface=(...)` 内联文本。测试已改为验证 `platform_duty=(...)` 输入和
`platform_duty_merger=lambda authority, surface: ...` 单一回调；该目标 26 个 Python
测试和 4 个 Node 测试通过。随后本地直接执行与远端相同的
`pnpm -C frontend/apps/web test`，完整通过，未再发现同类残留。

更新到 `0d719d631` 后，远端 `backend_suite (0)` 发现两类问题：

- `TestProjectMemberRoleSurface` 把完整 `ROLE_PRECEDENCE` 错误覆盖成测试夹具，导致
  `project_member` 从最终身份中消失。测试现已消费真实优先级，并分别验证能力发现与
  blocklist 语义；`group_sc_cap_project_read` 作为 project member 的读取能力组进入
  事实层映射。隔离新库 31 tests PASS。
- 人员档案 `menu_sc_runtime_user_management` 被错误放入
  `governance.organization` 业务场景。它是系统配置入口，当前由事实层精确直连声明，
  配置管理员 ACL 继续生效；`17.0.0.181` pre-migrate 只删除该菜单的历史场景绑定。
  场景投影守卫现在明确验证它属于 direct platform，而非 tenant scenario。

隔离新库 `TestScenarioDirectInitialization` 6 tests PASS。最新
`make ci.local.iteration` 对 110 个变更路径执行 25 个受影响目标，全部退出 0，
`unmappedPathCount=0`。当前剩余阻断仅为共享验收库升级与 49 例重跑，之后仍需提交新的
精确 HEAD 并取得当前 HEAD 的远端必需检查。

## 回退

代码回退恢复旧的单场景约束和原 authority 链；数据库升级会移除旧唯一约束，
数据行本身不删除。回退到旧代码前必须确认每个 menu 只有一个场景引用，或通过受管迁移处理。
新增的直连事实豁免是精确 XMLID 的一次性声明，管理员后续撤销不会被普通升级恢复。
本批不执行主线集成、发布、部署或远端写入。
