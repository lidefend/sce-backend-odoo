# NATIVE-SCENE-01 / A01 · Odoo 原生模型与字段盘点

状态：只读检查点，等待独立复核。

基线：`audit/native-scene-01-a01-a04-20261116@44cfed924b44b690dbb9f833ca9fcb605e8196cc`

## 1. 范围与判据

本轮检查三组事实：

1. 当前仓库内 17 个 Odoo 模块的 Python 模型声明、字段、关系、计算、约束、onchange 和业务方法。
2. 已登记的 Odoo Registry 只读运行态证据。
3. 当前正式产品入口实际触及的模型，以及行业投影/统计模型登记。

仓库内模块的最终运行基础镜像固定为 Odoo 17：
[`docker-compose.yml:46`](../../../docker-compose.yml#L46)。核心行业模块依赖
`project/purchase/stock/account/hr/mail/product/web` 等外部原生模块：
[`addons/smart_construction_core/__manifest__.py:5`](../../../addons/smart_construction_core/__manifest__.py#L5)。
这些外部模块源码不在本仓库，因此本报告不会把“本仓库未发现”写成“Odoo 不存在”。

静态扫描方法：

- 以每个模块 `__manifest__.py` 的 `data` 和 `demo` 为 XML 装载范围。
- 以模块内非测试 Python 文件的 class body 为模型/字段声明范围。
- `_name` 视为新模型身份；无 `_name` 且只有一个 `_inherit`，或 `_name` 出现在
  `_inherit` 中，视为已有模型扩展。
- 同一模型可在多个模块、多个类块中扩展；运行态有效字段与源码声明分开陈述。

## 2. 结论先行

| 事实层 | 结果 | 可信边界 |
|---|---:|---|
| 当前仓库模块 | 17 | 8 个模块含模型类，其余为 bundle/seed/portal/scene 数据或集成模块 |
| 模型类声明 | 498 | 包含多文件扩展类和 abstract mixin |
| Distinct 模型身份 | 359 | 当前仓库源码可见身份，不含未落源码的 Odoo 核心模型 |
| 字段声明 | 5,896 | 源码 class body 中 `fields.*` 赋值 |
| 关系字段 | 1,434 | 1,181 Many2one、140 One2many、112 Many2many、1 Reference |
| 计算字段 | 708 | 声明中含 `compute=` |
| Related 字段 | 313 | 声明中含 `related=` |
| 必填字段声明 | 1,074 | 声明中含 `required=` |
| `@api.constrains` 方法 | 124 | 覆盖 96 个 distinct 模型 |
| class-level `_sql_constraints` 声明 | 136 | 共含 175 条可解析约束 |
| `@api.onchange` 方法 | 63 | 覆盖 33 个 distinct 模型 |
| public 模型方法 | 1,356 | 非下划线开头的方法，含业务动作、compute、helper |
| TransientModel | 21 个身份 / 23 个类声明 | 向导、设置页和 workspace 临时模型 |
| AbstractModel | 27 个身份 / 29 个类声明 | mixin、parser、service 等不可实例化模型 |
| `mail.thread` 模型 | 92 | 同时继承 `mail.activity.mixin` 的 distinct 模型也是 92 |
| `tier.validation` 模型 | 50 | OCA 审批能力复用覆盖 |
| 运行态 Registry 模型 | 758 | `sc_dev_demo` 只读探针，来源 revision `f35d981b2` |
| 282 个业务入口直接触及模型 | 167 | 不是 Registry 全量，也不是仓库源码全量 |
| 正式投影/读取面登记 | 36 | 见 `backend_business_projection_registry_v1.json` |

机器可读模型清单：
[`native_model_inventory.json`](inventories/native_model_inventory.json)；
扫描口径和结果哈希：
[`inventory_manifest.json`](inventories/inventory_manifest.json)。

运行态模型数量证据：
[`docs/audit/capability-explorer-05/evidence/current-native.log:19854`](../capability-explorer-05/evidence/current-native.log#L19854)
记录 `all_model_count=758`，同处 `model_count=167` 是 282 个原生业务入口触及的模型数，
不是全部模型。不能据此把另外 591 个 Registry 模型判定为不存在或无用。

## 3. 模块与模型声明分布

| 模块 | 类声明 | Distinct 模型 | 新模型类 | 扩展类 | Transient 类 | Abstract 类 | 字段声明 | 关系字段 | 计算字段 | Related |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `base_tier_validation` | 7 | 7 | 5 | 2 | 2 | 1 | 76 | 23 | 19 | 11 |
| `base_tier_validation_server_action` | 2 | 2 | 0 | 2 | 0 | 1 | 4 | 2 | 0 | 0 |
| `sc_norm_engine` | 10 | 10 | 6 | 4 | 2 | 0 | 85 | 22 | 8 | 1 |
| `sce_customer_sample` | 1 | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| `smart_construction_core` | 394 | 279 | 253 | 141 | 16 | 15 | 5,058 | 1,282 | 671 | 295 |
| `smart_construction_demo` | 8 | 7 | 2 | 6 | 0 | 2 | 0 | 0 | 0 | 0 |
| `smart_construction_scene` | 5 | 5 | 5 | 0 | 1 | 0 | 27 | 5 | 0 | 0 |
| `smart_core` | 71 | 69 | 62 | 9 | 2 | 9 | 646 | 100 | 10 | 6 |

`smart_construction_core` 是行业事实权威主模块，版本为 `17.0.0.182`：
[`addons/smart_construction_core/__manifest__.py:5`](../../../addons/smart_construction_core/__manifest__.py#L5)。
`smart_core` 是平台机制模块，版本为 `17.0.1.1.19`：
[`addons/smart_core/__manifest__.py:11`](../../../addons/smart_core/__manifest__.py#L11)。

## 4. 模型分类

### 4.1 Odoo/OCA 原生模型扩展

当前仓库可见 165 个扩展类声明，落在 112 个 distinct 被扩展模型身份上。关键原生目标包括：

| 原生/OCA 模型 | 仓库内扩展证据 | 当前判断 |
|---|---|---|
| `project.project` | [`project_core.py:37`](../../../addons/smart_construction_core/models/core/project_core.py#L37) | 原生项目主档被复用并扩展；还有多个独立扩展类 |
| `project.task` | [`task_extend.py:10`](../../../addons/smart_construction_core/models/support/task_extend.py#L10) | 原生任务主档复用，扩展 OCA 审批与删除守卫 |
| `project.project.stage` | [`project_core.py:20`](../../../addons/smart_construction_core/models/core/project_core.py#L20) | 原生阶段模型扩展 |
| `account.move` | [`account_extend.py:5`](../../../addons/smart_construction_core/models/support/account_extend.py#L5) | 原生会计凭证扩展项目维度与成本联动 |
| `account.move.line` | [`account_extend.py:52`](../../../addons/smart_construction_core/models/support/account_extend.py#L52) | 原生凭证明细扩展项目/WBS/成本编码 |
| `account.tax` | [`account_tax_contract_rate.py:8`](../../../addons/smart_construction_core/models/support/account_tax_contract_rate.py#L8) | 原生税模型扩展合同税率语义 |
| `purchase.order` | [`purchase_extend.py:6`](../../../addons/smart_construction_core/models/core/purchase_extend.py#L6) | 原生采购单复用 |
| `purchase.order.line` | [`purchase_extend.py:158`](../../../addons/smart_construction_core/models/core/purchase_extend.py#L158) | 原生采购明细复用 |
| `stock.picking` / `stock.move` | `models/core`、`models/support` 中的扩展类 | 原生库存流转被复用 |
| `product.template` | [`product_extend.py:5`](../../../addons/smart_construction_core/models/support/product_extend.py#L5) | 产品主档保持 Odoo 权威 |
| `res.partner`、`res.partner.bank`、`res.partner.category` | `models/**` 中 3 类扩展 | 客商、银行账户和分类保留原生身份 |
| `res.users`、`res.groups`、`res.company` | `models/support/contract_center.py`、`smart_core/models` 等 | 用户、组、公司保持原生权威 |
| `res.config.settings` | [`res_config_settings.py:6`](../../../addons/smart_construction_core/models/support/res_config_settings.py#L6) | 设置页为原生 TransientModel 扩展 |
| `ir.ui.menu`、`ir.ui.view`、`ir.sequence`、`ir.http` | `smart_construction_core/models`、`smart_core/models` | 只做运行机制扩展，不另造菜单/视图事实 |
| `mail.notification` | `models/support/mail_notification_product.py` | 原生通知模型扩展 |
| `tier.validation`、`tier.definition` | OCA 与行业扩展 | 审批核心机制由 OCA 提供 |

判断：Odoo 原生模型继续作为身份、会计、库存、采购、项目、用户、公司、权限和
协作的事实根。行业模块主要通过字段、关系、状态和业务方法扩展，不另造平行根对象。

### 4.2 行业自定义模型

行业新模型属于 Odoo 原生缺少的一等施工业务文档，代表例子：

| 业务族 | 代表模型与源码 |
|---|---|
| 付款办理 | `payment.request`：[`payment_request.py:103`](../../../addons/smart_construction_core/models/core/payment_request.py#L103) |
| 预算/成本计划 | `project.budget`：[`project_budget.py:5`](../../../addons/smart_construction_core/models/core/project_budget.py#L5)；`project.cost.plan`：[`cost_plan.py:8`](../../../addons/smart_construction_core/models/core/cost_plan.py#L8) |
| 成本计划层级 | `project.cost.plan.line`：[`cost_plan.py:520`](../../../addons/smart_construction_core/models/core/cost_plan.py#L520)；`project.cost.plan.node`：[`cost_plan.py:666`](../../../addons/smart_construction_core/models/core/cost_plan.py#L666) |
| 工程量清单 | `project.boq.line`：[`boq.py:205`](../../../addons/smart_construction_core/models/core/boq.py#L205) |
| 结算 | `sc.settlement.order`：[`daily_contract_settlement.py:8`](../../../addons/smart_construction_core/models/core/daily_contract_settlement.py#L8) |
| 劳务/材料/设备/分包 | `sc.labor.*`、`sc.material.*`、`sc.equipment.*`、`sc.subcontract.*` 的独立业务文档 |
| 质量/安全 | `sc.quality.*`、`sc.safety.*`、`sc.risk.*` 的独立问题与闭环文档 |
| 投标 | `tender.bid`、`tender.opening`、`tender.guarantee` 等 |

`payment.request` 同时继承 `mail.thread`、`mail.activity.mixin`、`tier.validation`
及删除守卫：
[`payment_request.py:103`](../../../addons/smart_construction_core/models/core/payment_request.py#L103)
至 `:112`。这说明付款场景不是纯自定义状态页，而是直接复用 Odoo 协作与 OCA 审批能力。

### 4.3 投影与统计模型

已登记的 36 个投影/读取面分级如下，来自
[`backend_business_projection_registry_v1.json:1`](../../architecture/backend_business_projection_registry_v1.json#L1)：

- SQL view、物理刷新表、受控生成台账、运行期 workbench fact、计算摘要和受控快照。
- 代表：`sc.dashboard.cockpit.fact`、`sc.workbench.item`、
  `project.cost.ledger`、`sc.ar.ap.project.summary`、`sc.fund.daily.summary`、
  `sc.treasury.ledger`、`project.boq.summary.component`。

这些模型是管理可见性投影，不是原生交易根。A 阶段只确认其登记与源码身份；
刷新幂等性、口径、权限裁剪和全范围统计留到 C01/C02 与 D01/D02。

### 4.4 临时向导模型

共 23 个 TransientModel 类声明，落在 21 个 distinct 模型身份上：

| 模块 | Transient 模型 |
|---|---|
| OCA | `comment.wizard`、`res.config.settings` |
| `sc_norm_engine` | `project.boq.import.wizard`、`sc.norm.import.wizard` |
| `smart_core` | `sc.group.authority.reconcile`、`ui.form.custom.field.wizard` |
| `smart_construction_core` | `material.plan.to.rfq.wizard`、`payment.ledger.funding.allocation.wizard(.line)`、`project.boq.import.wizard`、`project.funding.baseline.transition.wizard`、`project.quick.create.wizard`、`project.task.from.boq.wizard`、`quota.import.wizard`、`res.config.settings`、`sc.approval.scope.user.wizard`、`sc.company.project.refund.workspace`、`sc.current.account.workspace`、`sc.product.system.settings`、`sc.project.stage.requirement.wizard(.line)`、`sc.team.loan.deduction.workspace` |
| `smart_construction_scene` | `sc.scene.governance.wizard` |

它们的“临时模型”身份不等于“非业务能力”。例如导入向导、批量生成任务和阶段要求
都可能承载真实业务写入，B09 必须继续验证默认值、提交、事务与结果。

## 5. 约束、计算与业务方法

| 机制 | 数量 | 代表证据 |
|---|---:|---|
| `@api.constrains` | 124 个方法 / 96 个模型 | 例如投标、付款、预算、WBS、材料数量与金额约束 |
| `_sql_constraints` | 136 个类级列表声明 / 175 条约束 | 业务编号/来源/唯一键约束 |
| `@api.onchange` | 63 个方法 / 33 个模型 | 例如 `execution_structure`、`purchase_extend`、`payment_request` |
| `@api.depends` | compute 字段依赖链 | `project_core.py`、`cost_domain.py`、`cost_plan.py` 等 |
| public methods | 1,356 个声明 | 包含业务动作、compute、helper 和 service |

关键判断：原生模型的事实不仅包括字段，还包括约束、onchange、compute 和按钮方法。
A01/A03 只能证明这些源码身份存在；B05/B12 必须再证明它们进入契约并由后端执行。

## 6. 支持状态

| 状态 | 模型范围 | 结论 |
|---|---|---|
| `source_declared` | 359 个 distinct 身份 | 仓库源码存在声明 |
| `runtime_registry_observed` | 758 个 Registry 模型 | 历史只读快照存在；不是当前 HEAD 的逐模型重跑 |
| `entry_reachable_observed` | 167 个模型 | 282 个原生业务入口直接触及 |
| `industry_fact_registered` | 10 个 formal runtime fact 模型 | 已有正式迁移事实登记 |
| `projection_registered` | 36 个投影/读取面 | 已登记实现模式与边界 |
| `native_reuse` | 92 个 mail/activity 模型、50 个 tier 模型 | 原生协作/审批能力直接复用 |
| `not_verified` | 所有模型的当前角色、字段权限、record rule 和事务 | 不在 A01 内完成；留给 B11/B12 |

## 7. A01 判定

已经具备完整的 Odoo 原生业务模型底座，不是“只有少量场景模型”：

- Odoo/OCA 原生项目、任务、会计、采购、库存、产品、伙伴、用户、公司、审批和协作模型继续复用。
- 施工行业在原生模型之上建立了合同、预算、成本、付款、结算、材料、劳务、设备、分包、
  质量、安全和投标等一等业务文档。
- 已存在 36 个投影/读取面，但必须继续区分可重建投影与业务事实。
- 当前仓库源码无法替代 Odoo Registry 的全量事实；本轮用历史只读 Registry 证据补足
  “已存在但不在本仓库源码中的 Odoo 模块能力”，同时保留验证边界。

本轮 A01 不判定任何模型已经被前端完整接管，也不进入字段权限、记录规则和交易事务验收。
