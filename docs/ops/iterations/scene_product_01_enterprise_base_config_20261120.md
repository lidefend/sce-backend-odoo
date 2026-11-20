# SCENE-PRODUCT-01：企业基础配置与开通

Base/main: `d2fb27530f5c1bf56719660af64199c6b343d8ff`

Branch: `feature/scene-product-01-enterprise-base-config-20261120`

## 产品结果

企业配置管理员在业务场景尚未启用时，可以进入企业初始化，看到当前企业与维护责任，按企业与组织、人员账号权限、业务场景三个配置组完成现有入口的维护和回读，返回同一企业重新诊断，并选择具备产品资格的企业场景。

配置事实、角色工作空间交付和实际业务办理保持分开。企业信息、组织、岗位、人员、账号、角色、公司范围和场景选择由企业管理员维护；企业创建、首个企业管理员、产品版本发布和技术配置仍由平台管理员负责。

## 层级与作用域

| 项目 | 声明 |
| --- | --- |
| Formal Product Layer | P1/P4 |
| Layer Target | 企业初始化场景、企业就绪诊断契约及既有前端消费旅程 |
| Module | `smart_construction_scene`、`smart_construction_core`、`frontend/apps/web`、`make/frontend.mk` |
| Standard vs User-Specific | 施工产品标准与公司运行时配置 |
| Why Here | 企业配置事实和企业级场景资格由 P1 施工产品拥有，前端只消费现有诊断与原生入口 |
| Why Not Elsewhere | 不把平台开企业、币种或版本发布放进企业页面，不复制组织人事、账号和权限模型 |
| Blast Radius | 企业初始化入口、诊断分组与汇总、原生配置入口返回、企业场景启停和目标角色业务验证边界 |

## 验证边界

本轮只执行纯契约、既有真实生产函数和前端消费链测试。ORM、模块基线、模块升级、fixture、浏览器矩阵、部署和完整产品验收不在本轮范围。目标环境中真实账号的使用结果留给选定交付版本的用户验收。

## 实施前责任门禁

| Gate | 状态 | 责任入口 | 依据 |
| --- | --- | --- | --- |
| 精确 base/HEAD 与范围 | required | `make agent.run.resume`、增量规划器 | 固定主线 `d2fb2753` 和本批分支 |
| owning module baseline | excluded | ORM 基线 | Owner 明确限定纯契约范围 |
| 既有受影响测试族 | required | 导航发布消费者、场景中心投影与事实边界目标 | 企业诊断和场景消费 |
| 新增行为测试 | required | 企业就绪诊断纯测试与前端 lifecycle | 配置分组、责任范围、返回与回读 |
| 契约消费 | required | `verify.frontend.workspace_scenario_lifecycle.unit` | 真实 composable 与受控传输 |
| 前端 lint/type/build | required | 增量规划结果 | 修改生产前端源码 |
| runtime/browser | excluded | 受管运行与浏览器车道 | Owner 指定纯契约，不产生用户验收结论 |
| 远端必需门禁 | required | 四项受保护 PR 检查 | 待精确 HEAD 发布 |

## 执行记录

- Owner preparation: branch/run registered from post-merge bookkeeping HEAD; SCENE-CLOSE-04 completion commit is carried into this product candidate.
- Product diagnosis: `enterprise_readiness.v2` now declares three stable configuration sections, current-company maintenance scope, explicit platform/enterprise responsibility and an aggregate that keeps configured facts, missing facts and pending business validation separate.
- Enterprise setup UI: current company and responsibility boundary are visible; rules are grouped by declared section; summary never collapses the diagnosis into “enterprise ready”.
- Enterprise setup return journey: native enterprise, organization, position, personnel/account and permission entries receive a declared return target to the same `/s/enterprise.setup` company/page context.
- Scenario activation remains below the readiness facts. Enabling a scene does not manufacture role delivery or business-journey acceptance.

## 验证结果

- `test_enterprise_readiness_contract.py`：2 项通过，覆盖分组声明、当前公司维护范围、摘要计数、待业务验证和不适用规则。
- `verify.navigation.publication_consumers.unit`：268 项前置及目标测试通过。
- `verify.frontend.workspace_scenario_lifecycle.unit`：readiness lifecycle 14 案通过；完整目标 481 项前置、消费及持久化案例通过。
- `verify.frontend.scene_entry_contract.unit`：scene entry 61、runtime fetch 73、diagnostic 85、hydration 94 案通过。
- `verify.frontend.navigation_shell.unit`、`verify.frontend.lint.src`、`verify.frontend.typecheck.strict` 通过；lint 仅有仓库既有警告，无错误。
- `verify.frontend.component_driver_takeover.unit`：18 项通过，组件驱动接管清单 current。
- `verify.frontend.dev.incremental.unit`：188 项通过。
- 场景中心投影守卫 9 项、场景事实边界 1 项通过。
- `make ci.local.iteration`：exit 0，实际执行 11 个必需目标；无缺失登记、无未映射路径、无 ORM 执行项。
- `ci.delivery.freeze.prepare`：通过，生成证据 current。

本轮仅使用真实纯生产函数、前端实际消费函数和受控传输。企业资料、组织、岗位、人员、角色和场景的原生写入仍由各自模型、ACL 与记录规则执行；目标环境中真实账号使用结果不在本轮伪证。
