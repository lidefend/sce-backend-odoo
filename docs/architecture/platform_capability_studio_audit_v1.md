# 平台能力目录与场景化治理审计 v1

状态：第一轮只读审计完成

审计基线：`main@2571346afc8c69cea20e32fcba36082c949cf825`

运行环境：`demo / sc_demo / daily-dev-demo`

> 2026-11-15 方向更新：本文的能力事实审计继续有效，但第 10 节中的
> `PlatformCapabilityCatalogService` 实施建议已被 `ARCH-DECISION-014` 取代。
> 后续采用 Odoo-Native Capability Discovery：模块安装提供能力，场景组合定义
> 产品，平台发布与企业启用完成交付，不新建平行能力 Registry。

## 1. 结论

当前平台还没有一份可以同时回答“能力是什么、由谁执行、达到什么成熟度、哪些入口已发布、被哪些场景和产品版本使用”的权威能力目录。

现实中存在八类不同事实源：

| 事实源 | 当前数量 | 它是什么 | 不能当成什么 |
|---|---:|---|---|
| Installed modules | 77 | 安装资产 | 业务能力 |
| Models | 758 | 数据结构/行为载体 | 业务能力 |
| Native action menus | 498 | 原生可执行入口 | 业务能力 |
| Business native action menus | 282 | 业务根下的入口候选池 | 标准化能力目录 |
| Current capability registry | 63 | 当前启动页 UI 能力投影 | 已完成能力治理目录 |
| Runtime `sc.capability` | 6 | 旧场景 Tile 能力 | 全平台能力目录 |
| Product release entry aliases | 每版本 274 | 已发布菜单页兼容身份 | 274 个业务能力 |
| Product configuration UI catalog | 25 | 产品配置功能目录 | 平台业务能力目录 |

完整、机器可读的跨来源身份清单见
[`platform_capability_studio_inventory_v1.json`](platform_capability_studio_inventory_v1.json)。
该清单共 65 个身份，是证据联合体，不是已经批准的正式能力目录。

## 2. CAP-01 历史结果对账

当前签入材料给出的权威统计是：

- 历史身份：63。
- keep：13。
- defer：26。
- exclude：24。
- 候选目录：39。

这与此前口述的“14 keep / 26 defer / 23 exclude / 40 candidates”不一致。当前仓库的
[`capability_candidate_catalog_check.py`](../../scripts/verify/capability_candidate_catalog_check.py)
实际输出为 `PASS keep=13 defer=26 total=39`。因此本轮只采用可复核的 13/26/24/39。

`d019b7e9c → 2571346af` 之间能力身份、成熟度、场景和发布服务源码没有变化，变化集中在
PR #888 导航投影。当前运行态仍暴露出历史候选目录未成为正式目录：

- CAP-01 候选与当前 63 项 registry 重合 38 项。
- CAP-01 唯一独有项：`project.initiation.create`。当前 registry 仍使用旧身份
  `project.initiation.enter`，迁移计划中的 canonical rename 未落地。
- 当前 registry 比候选目录多 25 项，其中 24 项是 CAP-01 已明确排除的页面/入口身份，
  另 1 项是未迁移的立项旧 key。

所以当前 63 项 registry 不是 CAP-01 候选目录的后继版本，而是旧的 UI 入口能力池被重新扩张后的结果。

## 3. 全平台能力身份清单

当前 registry 的 63 项按领域分布如下。它们是待治理输入，不是正式资格结论：

### 项目管理（25）

`project.initiation.enter`, `project.list.open`, `project.board.open`,
`project.dashboard.enter`, `project.dashboard.open`, `project.plan_bootstrap.enter`,
`project.execution.enter`, `project.execution.advance`, `project.lifecycle.open`,
`project.task.list`, `project.task.board`, `project.document.open`,
`project.structure.manage`, `project.risk.list`, `project.weekly_report.open`,
`project.lifecycle.transition`, `construction.plan.manage`, `construction.plan.report`,
`construction.diary.open`, `quality.issue.list`, `quality.rectification.list`,
`quality.recheck.list`, `safety.issue.list`, `safety.rectification.list`,
`safety.recheck.list`.

### 财务管理（10）

`finance.payment_request.list`, `finance.payment_request.form`,
`finance.approval.center`, `finance.ledger.payment`, `finance.ledger.treasury`,
`finance.settlement.order`, `finance.invoice.list`, `finance.plan.funding`,
`finance.metrics.operating`, `finance.exception.monitor`.

### 成本管理（5）

`cost.ledger.open`, `cost.budget.manage`, `cost.boq.manage`,
`cost.progress.report`, `cost.profit.compare`.

### 合同管理（4）

`contract.center.open`, `contract.income.track`, `contract.expense.track`,
`contract.settlement.audit`.

### 经营分析（4）

`analytics.dashboard.executive`, `analytics.lifecycle.monitor`,
`analytics.exception.list`, `analytics.project.focus`.

### 治理配置（3）

`governance.capability.matrix`, `governance.scene.openability`,
`governance.runtime.audit`.

### 物资管理（10）

`material.catalog.open`, `material.procurement.list`, `labor.plan.manage`,
`labor.request.list`, `labor.attendance.list`, `labor.settlement.list`,
`equipment.plan.manage`, `equipment.request.list`, `equipment.usage.list`,
`equipment.settlement.list`.

### 常用入口（2）

`workspace.today.focus`, `workspace.project.watch`.

正式身份收敛需要先解决 canonical key、页面身份误纳和 Provider 绑定，不能直接把上述 63 项冻结为目录。

## 4. 能力来源与实际执行者

当前 63 项 registry 全部声明 `intent=ui.contract`，其中：

- 10 项声明原生 `access_action`。
- 3 项声明 required groups。
- 52 项声明 required roles。
- 1 项不可见，2 项 deprecated。
- 对 wutao 的启动能力投影返回 57 项；这是 UI 可见投影，不是资格。
- runtime `sc.capability` 只有 6 项，且没有任何一项与当前 8 项验收契约重合。

业务根下原生事实为 282 个 action menu，覆盖 167 个模型；其中 277 个来自
`smart_construction_core`，2 个来自 Demo，3 个来自 Scene 模块。它们是发现能力的入口事实，
不是业务能力身份。

CAP-01C 已形成 6 项可追溯 Provider Join：

| capability | 执行模板 | unresolved |
|---|---|---|
| `project.lifecycle.transition` | state transition | 0 |
| `construction.plan.report` | business write | 0 |
| `cost.progress.report` | business write | 0 |
| `contract.expense.track` | read-only query | 0 |
| `contract.income.track` | read-only query | 0 |
| `contract.settlement.audit` | audit state transition | 0 |

这 6 项可以作为首批 Provider Join 样板复用，但不能替代全平台 Provider 绑定。

## 5. 成熟度与证据矩阵

当前 `capability_acceptance_contracts_v1.json` 有 8 项验收契约：

`project.initiation.create`, `project.list.open`, `project.lifecycle.transition`,
`construction.plan.report`, `cost.progress.report`, `contract.income.track`,
`contract.expense.track`, `contract.settlement.audit`.

当前状态：

- 8 项中有 7 项存在于 registry；`project.initiation.create` 不存在。
- 8 项全部不存在于 runtime `sc.capability`。
- 当前仓库未发现任何 `capability.maturity.evidence.v2` 证据 bundle。
- 因此证据支撑的 Preview 资格为 0，Standard 资格为 0。
- `make verify.capability.maturity.unit` 通过 42 项，只证明评估器正确，不证明产品能力合格。

能力成熟度必须是独立状态，不能由 `sc.capability.status=ga`、菜单 `released` 或场景已启用替代。

## 6. 入口发布矩阵

当前有两个 active released snapshot：

- `construction.standard`，snapshot 51。
- `construction.preview`，snapshot 52。

每个版本冻结 274 个唯一入口兼容别名，全部标记 `release_state=released`。这 274 是菜单页入口，
不是业务能力。

运行态交叉结果：

- 业务根下原生 action menus：282。
- 已进入标准版发布：274。
- 未进入标准版发布：8。
- 被产品场景引用：75。
- 已发布但未绑定场景：201。
- 场景已引用但未发布：2。

正式菜单策略中可观察到 132 个唯一带成熟度入口，其中 92 个
`RELEASED_FOUNDATION`、40 个 `PREVIEW_FOUNDATION`。但当前 released snapshot
没有保留 `capability_maturity`，274 条运行态别名全部只剩 `released`。这是入口成熟度证据在发布投影中的丢失。

两个 active snapshot 各有 4 个 scene projection，均为 `policy_only`，且 trace 都是
`BINDING_MISSING`，没有任何实际 `sc.scene.snapshot` 绑定。

## 7. 场景化与未场景化

当前可维护业务场景模型已有 17 个场景、78 个菜单引用、8 个中心：

`governance.organization`, `project.management`, `contract.performance`,
`cost.budget`, `procurement.supplier`, `material.management`,
`subcontract.management`, `labor.management`, `quality.management`,
`safety.management`, `payment.capital`, `receipt.payment.ledger`,
`tax.management`, `accounting.management`, `analytics.decision`,
`equipment.management`, `administration.office`.

公司 1 的 17 个场景全部已启用。当前 `business_catalog()` 只要场景内任一菜单处于
released，就把整个场景标成 `product_released`；它没有检查能力成熟度、完整场景证据或全部成员资格。

旧 `sc.scene` 编排目录有 60 条记录，但只有 2 条包含 Tile，共引用 6 个
`sc.capability`；58 条没有 Tile。旧场景目录目前主要是历史兼容数据，不能作为能力使用目录。

因此现阶段可以可靠列出：

- 201 个“已发布但未绑定产品场景”的入口发现候选。
- 6 个旧场景 Tile 能力。
- 8 项有验收契约但无运行态能力引用的治理候选。
- 57 个用户可见的 registry UI 能力。

但不能可靠列出“所有尚未场景化的业务能力”，因为业务能力身份与入口身份尚未统一。

## 8. 权限边界

当前实际 ACL：

| 身份 | 能力目录 | 场景组合 | 产品策略/发布 | 企业启用 |
|---|---|---|---|---|
| `smart_core.group_smart_core_admin` | CRUD | 旧 `sc.scene` CRUD | CRUD | 当前无直接写 ACL |
| `group_sc_cap_business_config_admin` | 只读 | `sc.product.scenario` CRUD | 无 | CRUD |
| `group_sc_internal_user` | 只读 | 只读 | 只读 | 只读 |
| 平台能力管理员 | 未实现 | 未实现 | 未实现 | 未实现 |
| 场景运营管理员 | 未实现 | 未实现 | 未实现 | 未实现 |
| 产品发布审核管理员 | 未实现 | 未实现 | 未实现 | 未实现 |

当前平台能力、旧场景和发布编排仍集中在平台管理员组，尚未形成“能力运营、场景运营、发布审核、
企业启用”职责分离。

## 9. 可复用后端能力

| 组件 | 复用方式 |
|---|---|
| `RuntimeCapabilityCatalogService` | 原生菜单/动作入口事实适配器 |
| `capability_registry.py` | 启动能力投影输入，但必须先做身份与 Provider 收敛 |
| `capability_maturity.py` | Preview/Standard 资格评估器 |
| `capability_maturity_evidence.py` | 受信证据 bundle 验证器 |
| `capability_acceptance_contracts_v1.json` | P1 验收标准与业务场景声明 |
| `CapabilityService` | 区分 business capability 与 entry compatibility alias |
| `sc.product.policy` / release snapshot | 产品策略和版本冻结 |
| `sc.product.scenario` / `scenario_surface_projection` | 当前场景组合权威 |
| `sc.scene` / `sc.scene.version` | 旧编排兼容/收敛对象 |
| `business_scene_enablement` / `sc.scene.company.enablement` | 企业启用 |
| `IdentityResolver` / role surface | 角色和权限边界 |

不建议新建第二个可编辑能力 Registry。应先建立只读的 `PlatformCapabilityCatalogService`，
将上述权威事实 Join 成统一能力视图。

## 10. 能力中心与场景编辑器设计

建议统一读模型字段：

`capability_key`, `label`, `domain`, `layer`, `definition_authority`,
`provider_refs`, `dependencies`, `preview_qualification`, `standard_qualification`,
`entry_aliases`, `entry_release_states`, `scene_references`, `product_version_references`,
`enterprise_enablement`, `blockers`, `last_verified_at`.

四个视图：

- 全部能力：完整能力身份和来源。
- 可场景化：Provider、依赖、契约和 Preview/Standard 资格满足。
- 已场景化：被哪些场景、产品版本和企业使用。
- 待治理：缺 provider、缺依赖、缺契约、缺证据、身份冲突或已退役。

场景编辑器只能从后端返回的合格能力集合中选择，并显示阻断原因；前端不得根据菜单、模型、
Action 或名称自行推断资格。

明确保持以下分离：

- 能力成熟度 != 入口发布。
- 入出兼容别名 != 业务能力。
- 场景组合资格 != 产品发布资格。
- 产品发布 != 企业启用。
- 业务操作能力 != 平台治理权限。

## 11. 第一阶段阻断项

| 编号 | 等级 | 结论 |
|---|---|---|
| PCS01-F01 | S1 | 当前没有统一能力目录权威。 |
| PCS01-F02 | S1 | 63 项 registry 与 CAP-01 39 项候选不一致，并重新纳入 24 项已排除页面身份。 |
| PCS01-F03 | S1 | 8 项验收契约与运行态能力目录脱节，当前证据 bundle 为 0。 |
| PCS01-F04 | S1 | Released snapshot 把 274 个入口别名暴露为能力，并丢失成熟度字段。 |
| PCS01-F05 | S1 | 场景发布只依据成员入口 released，未结合能力成熟度和完整场景证据。 |
| PCS01-F06 | S2 | 能力运营、场景运营和发布审核职责未独立。 |

本轮不实施修复。下一阶段应先批准身份权威、资格模型和权限边界，再进入只读能力中心实现。
