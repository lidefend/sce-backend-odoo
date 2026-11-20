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
- The 12 readiness rules now declare their product section by rule identity. User, employee, user-employee relation, organization-position relation, role and project responsibility facts belong to “人员、账号与权限”; the old `evaluation_layer` remains a separate evaluation field.
- Project responsibility is applicable only when the company has an existing project and the project scene is selected. Before the first project exists, the rule is a later business-validation item instead of a misleading enterprise-opening blocker.
- Project responsibility now also separates the reason by fact: no project asks the administrator to create one first; an existing project without responsibility asks them to maintain that project's member responsibility; existing responsibility has no failure reason.
- Saved enterprise scene selections remain counted when the product is temporarily unavailable, matching the scene catalog's saved-versus-current-availability semantics.
- The contract-only scope is registered only on this batch. The generated test inventory paths were moved out of the old LC-CONTEXT-01 entry; the final 27-path classifier result selects seven contract targets with `orm_required=false` and `managed_orm_required=false`.

## 五个原生维护入口审查

| 入口 | 实际 action / view | 维护字段与可编辑性 | 关联、权限与保存回读边界 |
| --- | --- | --- | --- |
| 企业信息 | `action_sc_enterprise_company` / `view_sc_enterprise_company_form` | 企业名称、税号、电话、邮箱、网站和地址可维护；币种只读 | 只查看当前公司；禁止创建和删除；业务配置管理员组；保存由 `res.company` 原生写权限和公司规则裁决 |
| 组织架构 | `action_sc_organization_department` / `view_sc_organization_department_form` | 名称、上级部门、负责人、公司、启用状态可维护；下级部门只读 | 业务配置管理员可写，数据读取角色只读；排除系统管理部门；无物理删除入口 |
| 岗位管理 | `action_sc_product_job_management_v1` / `view_sc_product_job_form_v1` | 岗位编码、名称、部门、公司、启用、编制、职责和任职要求可维护；在职人数只读 | 禁止删除；记录规则限制允许公司；业务配置管理员 ACL 含写权限 |
| 人员与账号 | `action_sc_runtime_user_management` / `view_sc_runtime_user_form` | 姓名、联系方式、部门、岗位、在职、登录账号、账号启用、主公司和密码可维护；建立后的人事档案字段只读 | 只显示当前公司范围内可维护的非特权内部用户；创建需要受控初始密码；公司、部门、岗位和角色写入经过白名单与范围校验；角色、允许公司和项目授权不在该页面重复维护 |
| 业务权限 | `action_sc_product_data_permission_v1` / `view_sc_data_permission_user_form` | 人员身份只读；主公司、允许公司、可分配角色和项目成员授权可维护 | 用户范围复用 `sc_runtime_company_maintainable`；角色只接受 `sc_assignable_user_permission`；项目授权必须引用现有项目和原维护用户；禁止物理删除用户与项目授权 |

五个入口都由原生模型完成持久化和回读，配置中心只提供入口、公司/页面上下文与返回路径。静态原生契约审查未发现需要重写页面的缺口；本批没有改变这些模型的保存语义，也没有把受控替身或纯契约测试冒充为真实数据库保存。

| 配置任务 | 声明与接线证据 | 本轮结论 | 运行态待验证项 |
| --- | --- | --- | --- |
| 企业信息 | 当前公司 action/view、字段可编辑性、公司记录规则与禁止增删声明测试 | 声明与消费接线成立，候选无需重写页面 | 实际账号保存企业字段，权威回读后仍属于原公司，重新进入一致 |
| 组织架构 | 组织表单、父子关系、负责人、允许公司和业务配置管理员 ACL | 声明与消费接线成立，候选无需重写页面 | 实际建立或修改组织，必填项和公司范围拒绝、保存回读及人员流程可见 |
| 岗位管理 | 岗位表单、关联部门、允许公司、写权限与禁止删除 | 声明与消费接线成立，候选无需重写页面 | 实际选择组织、保存岗位，再由人员维护流程选择该岗位 |
| 人员与账号 | 人员/账号表单、部门岗位关系、受控初始密码、角色与写入白名单 | 声明与消费接线成立，候选无需重写页面 | 实际创建或维护人员、账号和部门岗位关系，分别识别缺失事实并完成权威回读 |
| 业务权限 | 原用户只读、允许公司、可分配角色、项目授权和记录规则 | 声明与消费接线成立，候选无需重写页面 | 实际分配与拒绝角色/公司范围，回读仍绑定原用户、原公司并刷新目标角色导航 |
| 企业场景选择 | SCENE-CLOSE-04 已合入的目录、停用、回读证据及本批诊断/刷新消费 | 声明与消费链候选成立 | 选定运行版本中实际启用或撤销场景，刷新后选择保留，诊断继续区分已配置和待业务验证 |

## 验证结果

- `test_enterprise_readiness_contract.py`：5 项通过，覆盖 12 条规则显式分组、有用户无角色、有员工无账号关联、有关联无岗位，以及项目责任的“无项目”“已有项目但无责任”“已有责任”三种事实和原因，另含产品暂时不可用时仍准确统计企业已保存的场景选择。
- `test_enterprise_setup_native_contracts.py`：5 项通过，逐项核对五个原生维护入口的 action/view、维护字段、可编辑性、公司/角色/项目关联和 ACL/记录规则。
- `verify.navigation.publication_consumers.unit`：276 项前置及目标测试通过。
- `verify.frontend.workspace_scenario_lifecycle.unit`：readiness lifecycle 20 案通过，使用完整 12 条规则和三组投影；真实 `EnterpriseReadinessPanel` SFC 挂载 14 案通过，首次读取和刷新均等待可观察的 `ready` 页面状态，覆盖当前企业、三组 12 条规则、摘要、组织整改按钮和刷新后新回读结果；完整目标 509 项前置、消费及持久化案例通过。
- `verify.frontend.scene_entry_contract.unit`：scene entry 61、runtime fetch 73、diagnostic 85、hydration 94 案通过。
- `verify.frontend.navigation_shell.unit`、`verify.frontend.lint.src`、`verify.frontend.typecheck.strict` 通过；lint 仅有仓库既有警告，无错误。
- `verify.frontend.component_driver_takeover.unit`：18 项通过，组件驱动接管清单 current。
- `verify.frontend.dev.incremental.unit`：188 项通过。
- 场景中心投影守卫 9 项、场景事实边界 1 项通过。
- `make ci.local.iteration`：exit 0；最终解析 11 个必需目标，其中 10 个实际执行、1 个按未变输入复用；无缺失登记、无未映射路径、无 ORM 执行项。
- `ci.delivery.freeze.prepare`：通过，生成证据 current。
- 生成测试清单包含 1735 条，新增的挂载式页面消费测试已登记；组件驱动接管清单与源码指纹一致。

本轮仅使用真实纯生产函数、前端实际消费函数和受控传输。企业资料、组织、岗位、人员、角色和场景的原生写入仍由各自模型、ACL 与记录规则执行；目标环境中真实账号使用结果不在本轮伪证。

远端首轮的 SFC 失败已分类为验证工具时序缺陷：受控响应释放后只推进固定次数微任务，CI 上仍在 loading 时便断言。修复改为按可观察页面状态等待，并设置次数上限与超时诊断；产品字段、分组和刷新实现未因该失败改变。远端误触发的 ORM 准备与后端分片按实际发生记录，没有计为通过，也不替代本轮纯契约分类。

场景启停能力复用已合入的 SCENE-CLOSE-04：企业保存值、当前发布可用性、停用动作、原公司回读与目录重读均有既有纯契约和消费证据。本批只补充其与诊断的公共口径，不重复声称目标角色已获得业务访问。

## 三层验收状态

| 层次 | 当前状态 | 证据与边界 |
| --- | --- | --- |
| 受影响通用机制 | 通过 | 诊断声明、导航/权限投影、异步消费上下文、lint/type、增量选择及其既有测试族通过 |
| 场景声明与消费闭环 | 候选完成，待独立复审 | 五个原生入口和场景选择的 action/view、字段、关联、权限、保存/回读接线、真实 SFC 受控消费均已核对 |
| 用户可用性验收 | 未执行 | 尚无选定运行版本中的配置管理员账号、实际保存、权威数据库回读、返回初始化与重新诊断证据 |

当前验证可以支持“场景声明与消费闭环”的候选结论，但不能替代实际运行环境中的用户可用性验收。五个原生入口的保存仍由真实 Odoo 模型、ACL、记录规则和受控表单机制执行；本轮通过静态原生契约、模型源码审查和受控组件/传输验证证明接线与边界，尚未执行真实账号保存、数据库回读或浏览器旅程。

目标用户是否真正可用，必须另行在选定受管运行环境中按同一配置管理员身份完成各自的“找到入口 → 输入或选择 → 提交 → 成功或拒绝 → 权威回读 → 返回并重新诊断”检查。该定向运行验收不要求恢复全量 ORM 或完整浏览器矩阵，也不会因本 PR 合并而自动视为完成。
