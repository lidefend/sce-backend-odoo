# SCENE-PRODUCT-02：企业配置管理员办理旅程与可用性收口

Base/main: `f2f7fd02f0f28f84e6190102f3bf559db0c28457`

Branch: `feature/scene-product-02-enterprise-config-journey-20261120`

Carried post-merge bookkeeping commit: `74dae16496222bdba07ea67f0fbd5fac550213be`

## 产品结果

企业配置管理员在现有企业初始化入口中，按业务依赖顺序完成企业资料、部门、岗位、人员与账号、同一用户的业务权限及企业场景选择。每条旅程必须有真实对象、提交结果、拒绝或成功反馈、权威回读、返回同一企业和重新诊断。

## 层级与边界

| 项目 | 声明 |
| --- | --- |
| Formal Product Layer | P1/P4 |
| Layer Target | 原生企业配置事实、五类维护入口、企业场景选择及自定义前端消费 |
| Standard vs User-Specific | 施工产品标准与企业运行时配置 |
| Why Here | 组织人事、账号权限和场景选择事实属于 P1 模型；前端只消费其声明 |
| Why Not Elsewhere | 平台只负责建企业和产品发布；P4 不成为业务事实来源，也不扩大权限 |
| Blast Radius | 六个配置入口的输入、拒绝、保存、回读、返回与重新诊断 |

## 运行环境与身份

开工检查结果：

- `make local.dev.health`：PASS，`sc-local-dev / sc_dev_demo`。
- `make local.dev.entry_identity.verify`：PASS，`/t/demo` 与 `ns_000000000002` 绑定 `sc_dev_demo`。
- `make local.dev.verify_authority`：PASS，演示环境模块、财务身份、本位币和税率事实成立。
- `make local.dev.write_lease.status`：`LOCAL_DEV_WRITE_LEASE_FREE`。
- `local.env.status` 的 sample 未启动和主静态入口 404 不影响 persistent local.dev；本批使用候选前端 5176。

精确运行身份：

- 后端源码 revision / 前端构建 revision：`c7de01f85d9fc572ea1c7bbf6d979f93c9c15bce`。
- 配置管理员：`res.users(24)` / `sc_demo_business_config` / 徐磊。
- 当前公司：`res.company(1)` / 四川智汇某某建设集团有限公司。
- 允许公司：`[1]`。
- 候选前端健康同时核对了后端源码挂载、`SC_SOURCE_REVISION`、数据库、dbfilter 和 filestore。

首次登录时，`system.init` 因 `sc_product_policy.business_scene_composition` 列不存在返回 500。先创建受管恢复快照：

```text
artifacts/local-dev/snapshots/20261120T043906Z
```

随后通过写租约执行 `make local.dev.upgrade MODULE=smart_core`，升级成功并恢复：

- 数据库 schema 与当前源码一致；
- `SC_SOURCE_REVISION=c7de01f85…`；
- `/t/demo`、`sc_dev_demo` 和候选前端 5176 健康；
- 登录、`system.init` 和企业初始化页面读取成功。

## 执行顺序

1. C02-01 企业信息：修改、保存、权威回读并返回初始化。
2. C02-02 部门：创建/维护并核对公司、上级和负责人。
3. C02-03 岗位：选择已保存部门并核对唯一编码与关系。
4. C02-04 人员与账号：创建普通内部用户、员工关联、部门和岗位，再修改同一对象并补部门负责人。
5. C02-05 业务权限：对同一用户授予和调整角色/允许公司，使用目标用户核对访问结果。
6. C02-06 企业场景：启用、回读、刷新、撤销/恢复，并区分企业选择、产品可用性和用户访问。

## 当前状态

- `local.dev.health`、入口身份、演示权限、写租约和候选前后端 revision 一致性通过。
- C02-01 在“点击企业信息”处阻断：按钮没有发出请求或改变路由；直接访问 `/a/960?action_id=960` 被前端以 `NAVIGATION_AUTHORITY_DENIED` 拒绝。
- 运行契约中五个入口只声明 `action_xmlid`，而当前执行权限路由没有解析出对应 action/menu。
- 这与未合并的 #950 所修复的 native route discovery 丢失一致。本批依赖 PR #950，当前观察 HEAD 为 `ce1da712e174f002890fdbef8ad7f9320d631060`；不在本分支重复修改同一路由链。
- C02-01 到 C02-05 均未发生业务写入；实际保存、拒绝、回读和用户可用性结论仍为 `not_run`。
- C02-06A 已独立读取：目录返回 92 个源行、0 个可启用业务场景；92 行全部声明 `PRODUCT_RELEASE_UNVERIFIED`、`product_released=false`、`enable_allowed=false`，没有启停动作，因此没有执行场景写入。
- C02-06B 目标用户业务入口可达性未执行，且仍可能依赖 #950 的路由恢复。

## 本批消费修复

- `SceneView` 在办理目录声明存在、但无法解析为当前用户获准目标时，不再静默返回。页面通过现有 `ContractGapError` 错误表面显示入口不可用，并携带缺失契约路径和声明层，不猜测动作 ID、不拼接兜底路由、不发业务写请求。
- `StatusPanel` 优先显示显式传入的契约缺口，不再把已知 `ContractDefectRef` 降级成普通 unknown/permission 状态。
- 场景目录消费者按后端已声明的 `rows`、`row_count` 和 `enablement_blockers` 保留资格诊断。没有可启用场景时，页面显示真实目录数量和启用阻断原因，不再只显示笼统的空目录。

定向验证：

- real `StatusPanel` component 契约缺口渲染与无恢复按钮：通过。
- `verify.frontend.workspace_scenario_lifecycle.unit`：通过，新增目录资格诊断 6 案。
- `verify.frontend.delivery_hardening.guard`：18 项通过。
- `verify.frontend.dev.incremental.unit`：189 项通过。
- frontend lint 仅有仓库既有 warning；strict typecheck 通过。

## 实际浏览器消费结果

候选源码/构建：`a36f24f423148445a30a650d94685cbfc0f2f042`

使用 `sc_demo_business_config`（user 24）/ company 1，在 `sc-local-dev / sc_dev_demo / ^sc_dev_demo$` 的候选前端 5176 执行：

```text
[enterprise_configuration_consumer] PASS entry=contract_gap catalog=blocked_by_declared_qualification rows=92
```

入口反例结果：

- 点击可见“企业信息”后仍停留在 `/s/enterprise.setup`。
- 页面显示“页面执行契约暂不可用”，而不是静默无反馈或普通权限不足。
- 契约缺口为 `scene_ready_contract.scene_internal_actions.enterprise.setup:smart_construction_core.action_sc_enterprise_company`。
- 声明层为 `P0:smart_core:system_init_scene_runtime_surface_builder`。
- 未导航到猜测目标，未发出业务写请求。

五入口只读对账：

| 入口 | XMLID | 当前 action / model | 原生授权 | 原始内部动作 | 最终 `scene_internal_actions` |
| --- | --- | --- | --- | --- | --- |
| 企业信息 | `action_sc_enterprise_company` | 960 / `res.company` | action group、ACL read/write 通过 | 已解析 | 缺失 |
| 组织架构 | `action_sc_organization_department` | 804 / `hr.department` | action group、ACL read/write 通过 | 已解析 | 缺失 |
| 岗位管理 | `action_sc_product_job_management_v1` | 954 / `hr.job` | action group、ACL read/write 通过 | 已解析 | 缺失 |
| 人员与账号 | `action_sc_runtime_user_management` | 807 / `res.users` | action group、ACL read/write 通过 | 已解析 | 缺失 |
| 业务权限分配 | `action_sc_product_data_permission_v1` | 957 / `res.users` | action group、ACL read/write 通过 | 已解析 | 缺失 |

结论：稳定 XMLID 和原始内部动作解析成立，原生授权未阻断；阻断发生在最终 effective delivery 输出/消费边界。该 P0 生产链仍归 #950，当前候选只在消费端显式报告缺口。

### 加载 #950 候选后的复验

为区分“已修复”和“候选包含修复”，本轮另外建立本地组合验收分支：

```text
C02 父候选：7c4c5e32fb028fc8dcdf6bd844b26ddaec4ab9ab
#950 候选：af7bf00026cb78cee4cb84edd9c6b3c281d7d429
组合候选：fab3415370b513e1fbb453d317e8b316171785f5
```

该组合版本仅用于运行验收，不属于 C02 最终 PR。后端与 5176 前端均重新构建到 `fab341537…` 并通过候选健康。

结果：

- 原始内部动作仍能解析出 5 项；
- action group、模型 read/write 权限均通过；
- effective delivery 的 `scene_keys` 只包含 `workspace.home`；
- 最终 `scene_internal_actions={}`；
- 点击“企业信息”后落到 `/workbench?...action_id=961&reason=CAPABILITY_MISSING`，不是当前公司的 `res.company` 维护页；
- 没有业务写入。

因此当前 #950 候选尚未覆盖企业初始化的内部动作保留链，不能据此开始 C02-01 保存。证据：

```text
.runtime/agent-runs/SCENE-PRODUCT-02-ENTERPRISE-CONFIG-JOURNEY-20261120/combined-950/entry-and-catalog.json
sha256=4723d8e7fa8fa97e08b41da04fbc1b98673855f97cd395a56c50c44c89326c68
```

### 发布前置与 C02-06A 收口

前面的 `92 × PRODUCT_RELEASE_UNVERIFIED` 已确认为验收前置数据缺陷，不是场景目录消费错误：

- `smart_core.release_operator.catalog_source_db` 为空，发布预检回退到 `sc_demo`；
- 当前运行库 `sc_dev_demo` 没有任何 `construction.standard` 发布快照；
- 错误源库导致预检产生 137 个 `SOURCE_MENU_NOT_FOUND`，发布无法完成。

新增 `local.dev.product_release.prepare`，固定当前数据库、要求完整源码 SHA、显式确认和写租约，并调用既有 `EditionReleaseSnapshotService`。实际执行后：

- `catalog_source_db=sc_dev_demo`、`platform_release_db=sc_dev_demo`；
- 唯一活动快照 ID `4`，版本 `local-dev-fab3415370b5`；
- 状态 `released`、`is_active=true`，发布门禁 `applied=true`；
- 发布范围 132 页；
- policy SHA-256：`30181d9a0432ac81c5a6c71066b2bdf676edd9868a96383856ba07d1b69b6ce0`。

发布前置使用以下恢复点：

```text
artifacts/local-dev/snapshots/20261120T063623Z
```

该准备只建立产品发布事实，不授予用户访问权限。配置管理员 user 24 的实际 `company_ids` 为 `[2, 1]`；本轮固定 company 1 上下文办理，不修改其公司授权。

### C02-06A 真实浏览器启停

最终验证身份：

```text
candidate / backend / frontend build:
65a7bd0cd85ac5732535c670c6fff4fd4a98ed41
```

使用 user 24 / company 1，在现有 5176 候选前端完成：

1. 读取目录：92 行，17 个可执行业务场景；
2. 在页面启用 `governance.organization`；
3. 服务端回读 `enabled=true`、company 1、`write_committed=true`、`access_granted=false`；
4. 刷新导航并重新读取目录；
5. 在页面停用同一场景；
6. 服务端回读 `enabled=false`；
7. 独立 Odoo 回读确认参数值为 `0`。

浏览器实际发出两次 `scenario.activation.set`，目标值分别为 `true` 和 `false`；浏览器错误为 0。运行证据：

```text
.runtime/agent-runs/SCENE-PRODUCT-02-ENTERPRISE-CONFIG-JOURNEY-20261120/enterprise-configuration-consumer/report.json
sha256=c0a3684bc2099d2b5a748159b13870a72c3145177b51557800d26f2821d23e69
```

该旅程同时定位并修复了一个真实 P1 缺陷：启用后立即停用时，参数写入完成后的同请求回读可能命中旧 registry 缓存，返回 `INTERNAL_ERROR`。现在写入完成后再次清理缓存，并增加“写 false 后立即读 false”的回归。

C02-06B 继续 `not_run`：企业选择、导航刷新和独立访问授权已分开；`demo_role_pm`（user 48）只读回读得到 `role_surface=pm` 和项目中心声明，但本批没有适用的业务项目旅程，且企业维护入口仍被 #950 的 P0 绑定缺口阻断。

## 本批验证结果

- `verify.frontend.workspace_scenario_lifecycle.unit`：515 案通过；其中新增目录资格诊断 6 案。
- `verify.frontend.delivery_hardening.guard`：18 项通过；真实 `StatusPanel` 的显式契约缺口渲染与无恢复按钮断言通过。
- `verify.admin_close_01.backend.unit`：167 项通过，包含场景启停缓存失效回归。
- `verify.local.development_lifecycle.unit`：58 项通过，包含发布前置入口身份、租约和确认断言。
- `verify.frontend.dev.incremental.unit`：189 项通过。
- `verify.local.dev.enterprise_configuration.consumer` scenario-only：PASS；17 个可执行场景，启用和停用均完成回读及目录刷新。
- 候选前端构建：PASS，后端、前端构建和 5176 服务均绑定 `65a7bd0cd85ac5732535c670c6fff4fd4a98ed41`。
- `make ci.local.iteration`：exit 0；13 个必需目标实际执行，无缺失登记、无未映射路径、无 ORM 执行项。
- `ci.delivery.freeze.prepare`：通过；生成测试清单 1735 条且证据 current。
- frontend lint 无 error；strict typecheck 通过。

仍未执行：C02-01 保存和回读、C02-02 至 C02-05、C02-06B 目标用户项目/业务访问。这些保留在 #950 路由生产链恢复和适用项目旅程形成之后。

## 132 个办理面业务组织设计

本轮将此前 17/19 项导航分组视为过程资料，不再作为产品场景结论。新的设计输入固定为：

- 一个工作台＋十个业务中心；
- `product_menu_source` 中实际发布的 132 个办理面；
- 原生模型和现有状态机测试所证明的业务用途。

设计结果：

- `config/product_scenario_organization_v1.json`：机器可读组织契约；
- `docs/product/product_scenario_organization_v1.md`：完整总表、中心目录、工作台路由、跨中心衔接和缺口；
- `scripts/audit/build_scenario_product_organization.py`：从真实菜单源生成并校验组织结果；
- `make verify.product.scenario.organization.unit`：13 项非零验证。

当前结果：

```text
released_page_count=132
organized_page_count=132
unique_page_count=132
duplicate_page_count=0
unassigned_page_count=0
unknown_page_count=0
scenario_group_count=46
center_count=11
```

该设计按“用户能完成什么结果”组织办理面，不把菜单名称自动等同于场景。46 个分组是本次组织结果，不是产品常量。工作台待办/消息和快捷办理已声明目标中心、目标办理面、结果展示和返回位置；18 个可执行衔接明确来源模型、来源记录 ID、触发条件、目标 XMLID、携带对象和返回位置。

## 定稿后的场景种子实施

产品负责人已审核通过上述组织结果，状态更新为：

```text
APPROVED_FOR_IMPLEMENTATION
approved_at=2026-11-20
```

运行时场景种子由同一生成器写入 `addons/smart_construction_core/data/scenario_product_surface.json`：

- 46 个已批准业务分组；
- 132 个唯一菜单 XMLID；
- 每个办理面显式声明办理、查看、报表或基础资料维护意图；
- 旧 19 个过程场景键不再进入运行时场景定义；
- 场景与页面顺序来自定稿 JSON，不在前端或数据库中重新推导。

`sc.product.scenario` 种子导入已支持逐页 `bindings` 和场景顺序。场景导航投影按批准顺序输出，不再按场景编码字母排序。

实际验证：

- `verify.product.scenario.organization.unit`：13 项通过；
- `verify.nav01.native_authority.unit`：25 项通过；
- `verify.admin_close_01.backend.unit`：103 项通过；
- `verify.frontend.workspace_scenario_lifecycle.unit`：通过，包含真实 SFC 消费；
- `local.dev.rebuild_demo`：从当前源码完整重建 `sc_dev_demo` 并加载 `demo_full`，通过；
- `local.clean.rebuild LOCAL_CLEAN_MODULES=smart_construction_core`：空库安装通过；
- 数据库权威回读：`sc_dev_demo` 与 `sc_clean` 均为 46 场景、132 绑定、132 唯一菜单，旧场景键为 0。

发布组合已改为强制分离：

- 业务目录与场景组合来源：`sc_dev_demo`；
- 发布快照目标：`sc_platform_control`；
- 两者相同直接拒绝，不再允许 demo 租户兼任平台发布库。

本地平台控制面已通过受管入口创建：

- Compose project：`sc-local-platform`；
- database：`sc_platform_control`；
- application role：`sc_platform_control_app`；
- maintenance role：`sc_platform_control_maintenance`；
- 独立数据库、Redis、Odoo 数据卷；
- 仅安装 `smart_core`，无 demo、行业或客户业务数据。

共享开发环境 `VITE_PLATFORM_ADMIN_DB` 已切换到 `sc_platform_control`。原 `.env.dev` 在修改前保留为私有 `0600` 备份。

跨库发布通过两段式受管入口完成：

1. `sc_dev_demo` 输出策略包：132 页面、46 场景，来源策略 SHA-256
   `412d744ff47b70ea4bd1277cc73f2a54efccd4787e661197548abc87be6b076f`；
2. `sc_platform_control` 校验策略包后冻结快照。

权威回读：

```text
snapshot_id=1
product=construction.standard
version=local-dev-65a7bd0cd85a
state=released
is_active=true
active=true
page_count=132
scenario_count=46
catalog_source_db=sc_dev_demo
platform_release_db=sc_platform_control
release_gate=applied
```

## 主线更新前的契约收口

最新 `origin/main` 为 `46f323cdaac1cb9b5a1fb4b64fcb21fd95183d37`；本分支从
`f2f7fd02f0f28f84e6190102f3bf559db0c28457` 出发，携带 16 个责任提交，并且尚未包含
上述主线提交。该主线提交包含本批此前等待的原生路由生产链修复，因此后续用户旅程必须先
在冻结候选上执行精确 HEAD Quick，再通过 `workspace.branch.sync-main.extended` 重放到
该主线，不能继续在旧基线上验证。

同步前定位并修复了三个契约问题：

- `ActionDispatcher` 的模型事实位于 `head.model`，V2 装配器此前只读取顶层
  `model`，导致 `pageInfo.model` 为空；现改为消费 `head.model`，并恢复严格 Action
  身份模型比较，不再允许空模型绕过校验；
- `sc_stage_requirements` 在当前环境中是已识别但缺少 payload provider 的节点，正确
  拒绝原因是 `NATIVE_VIEW_WIDGET_PAYLOAD_UNAVAILABLE`，不是未知 widget；
- 装配输入变化后，租约缓存版本提升为 `ui-contract-v2-demand-driven-snapshot-v93`，
  四源输入摘要重新固定为
  `adf726b4d74c1f2e430a7b0762347d0aa53d119e812bbf61aa4a9f171a73101b`。

同时修正了产品中心行为锁：当前骨架是工作台加十个业务中心，`supply_chain` 是第十个
业务中心，不再沿用工作台加九个中心的旧断言。

最终增量门禁实际执行 44 个受影响目标并全部通过，包括：

- `verify.native_occurrence.contract.orm`：8 项；
- `verify.product_center.policy.unit`：15 项；
- `verify.unified_page_contract.v2.assembler`；
- `verify.unified_page_contract.v2.runtime`：149 项；
- `verify.unified_page_contract.v2.web_architecture`；
- 真实 SFC 14 案和既有 20 案生命周期；
- `unmappedPathCount=0`、`blocked=0`、`not_run=0`。

增量回执：

```text
.runtime/frontend-dev-validation/executions/20261120T123643Z-2201996-755971495/receipt.json
```

此前 92 行 / 17 场景的浏览器启停只保留为历史机制证据，不能证明当前 46 场景 / 132
办理面的最终选择结果；C02-06A 因此改为同步后重新验证。C02-01 至 C02-05 也尚未在包含
`46f323cd` 的精确运行版本上完成，整体用户可用性仍为 pending。

## 全量本地门禁纠正

主线同步后确认，`workspace.branch.sync-main.extended` 曾自行要求预置 exact-HEAD
`ci.local.quick` 回执。该条件与仓库顶层增量交付规则冲突，也与远端每日全量回归重复。
它使普通 P0 修复、主线 rebase 和生成报告刷新都必须重新执行全仓扫描、构建和测试。

现已移除该条件：

- 常规迭代和主线同步不要求全量本地 Quick；
- 本地保留精确 HEAD、clean worktree、提交数、受影响 L2 和生成证据一致性；
- 远端每日全量继续承担完整回归；
- 全量 Quick 仅用于显式审计、基线重建或发布冻结。

`verify.workspace.branch.sync-main` 的 51 项测试用于锁定该边界，防止 extended sync 再次
以 Quick 回执复制远端全量职责。此次政策修正不削弱远端四项必需检查，也不改变主线同步的
恢复包、历史重写和冲突回滚约束。

## 验收深度校准

共享表单机制不再按五个入口重复做浏览器操作。C02-01 已用一次真实办理链证明：

- 从稳定 `action_xmlid` 找到入口；
- 从真实列表进入当前公司记录表单；
- 修改可编辑字段并提交；
- 保存响应和目标记录身份一致；
- UI 回读与 Odoo 权威回读一致；
- 恢复原值并再次确认；
- 经列表返回企业初始化并重新读取诊断。

其余入口继续保留静态声明审查。只有共享机制无法证明的独有语义才补定向检查：
部门层级和公司范围、岗位编码与部门关系、用户-员工-部门-岗位身份、角色与允许公司范围。
这避免把同一次表单保存机制复制成五个脆弱、环境相关的浏览器脚本。
