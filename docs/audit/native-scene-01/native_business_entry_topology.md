# NATIVE-SCENE-01 / A08 · 原生业务入口拓扑

状态：只读检查点，等待独立复核。

基线：`audit/native-scene-01-a01-a04-20261116@44cfed924b44b690dbb9f833ca9fcb605e8196cc`

## 1. 三个不能混用的入口口径

本轮必须同时保留三张图：

| 口径 | 回答的问题 | 证据 |
|---|---|---|
| 源码声明图 | 模块安装时会声明哪些菜单、Action、View | 当前 HEAD manifest/XML |
| Odoo Registry 图 | 当前 Odoo 中实际存在并解析哪些对象 | 历史只读 `sc_dev_demo` Registry 快照 |
| 正式产品图 | 当前产品允许发布哪些入口 | `product_menu_source.json` + release policy |

三者数量不同是正常现象：

- 源码有更新记录、重复 XMLID 和未进入产品的编排资产。
- Registry 包含外部 Odoo/OCA 模块。
- 正式产品只选择和发布其中一部分。

不能用任何一张图单独证明“前端已完整交付”。

## 2. 源码声明拓扑

### 2.1 数量

| 对象 | XML 声明数 | Unique XMLID | 说明 |
|---|---:|---:|---|
| Menu | 896 | 446 | 同一菜单被多个导航/安全文件更新 |
| `ir.actions.act_window` | 584 | 427 | 多个文件可更新同一 Action |
| `ir.actions.server` | 151 | 101 | 同一 Server Action 可有组补丁 |
| `ir.actions.client` | 2 | 2 | 项目工作台、定额中心 |
| `ir.ui.view` | 800 | 797 | 3 个 View 被更新 |
| `ir.actions.act_window.view` | 18 | 18 | 显式 view set 绑定子记录 |

Unique Menu 中：

- 361 个至少由一个声明提供 Action。
- 85 个没有声明 Action，通常是目录/分组节点。
- 439 个有 parent。
- 402 个声明了 groups。

复用仓库已登记 `product_native_menu_inventory.py` 工具（`PYTHONPATH=.`）对
`smart_construction_core` 的源码事实再做一次分类，得到 411 个菜单事实：

- `registered_product=129`
- `same_action_as_registered_entry=20`
- `roadmap_carrier=17`
- `structure_only=78`
- `native_action_requires_review=167`

其中 129 个仓库内原生入口加 3 个外部 `account` presentation，正好组成正式产品
132 个入口。`native_action_requires_review` 不是“孤儿”定论，只表示尚未进入当前产品
选择，仍需从按钮、Wizard、上下文和外部模块反向解释。

源码 Action 全量与本轮静态反向引用结果：

- `530` 个 unique Action XMLID 均在至少一个 XML 源位置被引用。
- 这包括菜单、`type=action` 按钮、`view_ids/views` 字段和配置引用。
- “源码有引用”仍不等于“运行态可达”；B01 必须按 actor/company/context 再验证。

### 2.2 一个 Window 入口的最小拓扑

```text
ir.ui.menu
  -> action reference
  -> ir.actions.act_window
  -> res_model
  -> view_mode
  -> view_id / views / view_ids / ir.actions.act_window.view
  -> ir.ui.view（继承合并）
  -> search_view_id
  -> domain / context / groups_id
  -> ui.contract.v2
  -> Renderer
  -> CRUD / onchange / object method / server action
  -> ACL / record rule / field groups / company context
```

一个完整原生菜单若能把上链全部事实无损传入契约，就可以作为独立业务场景交付，
不需要额外创建场景模型。

## 3. Registry 拓扑

历史只读快照
[`navigation_capability_inventory_v1.json:26`](../../../artifacts/backend/navigation_capability_inventory_v1.json#L26)
记录：

| 指标 | 数量 |
|---|---:|
| Menu | 720 |
| Active Menu | 622 |
| 带 Action 的 Menu | 555 |
| 无 Action 的 Menu | 165 |
| 无 Action 容器 | 138 |
| 无 Action 叶子 | 27 |
| 菜单引用 Unique Action | 520 |
| 菜单 Action 引用次数 | 555 |
| 多菜单复用 Action | 31 |
| 未解析菜单 Action 引用 | 0 |

Registry Action 总量为 744 Window、173 Server、9 Client、3 URL、40 Report、
969 Close：
[`navigation_capability_inventory_v1.json:274`](../../../artifacts/backend/navigation_capability_inventory_v1.json#L274)。

不能简单用 `1938 - 520` 计算“无菜单业务能力”：

- Report/Server/Close 可能只由按钮或业务方法返回。
- Window Action 可能是 Wizard、关系选择、stat button 或上下文下钻。
- 同一 Action 被多菜单复用说明 Action 本身不是唯一业务入口。

### 3.1 无 Action 叶子

Registry 的 27 个无 Action 叶子必须分三类：

1. 合法 Scene Entry；当前确认 `smart_construction_core.menu_sc_workspace_home` 就是
   一个声明式场景入口，指向 `workspace.home`。
2. 外部 Odoo 的自定义快捷/技术容器，例如 `base.menu_config`、`base.theme_store`。
3. 需要 B/A08 继续解释的 active 叶节点，例如
   `smart_construction_core.menu_sc_project_internal_group_v2` 在快照中是 active 且无子节点、
   无 Action。它可能是错误隐藏/分组残留，也可能由导航投影补目标；本轮不擅自修复。

### 3.2 282 个原生业务入口目录

独立只读探针证明：

- 282 个 Menu+Action 复合身份。
- 264 个 unique Action XMLID。
- 75 个入口有权威场景绑定，207 个只能确定原生中心。
- 0 个技术阻断。
- 触及 167 个模型、776 个 View、581 条 ACL 和 348 条 Record Rule。

证据：
[`current-native.log:19849`](../capability-explorer-05/evidence/current-native.log#L19849)。

这 282 个入口是“当前原生业务能力目录”，不是正式产品的 132 个发布入口。

## 4. 正式产品入口拓扑

正式产品选择事实：
[`product_menu_source.json:95`](../../../addons/smart_construction_core/data/product_menu_source.json#L95)。
发布策略：
[`formal_business_product_menu_policy_v1.json:20`](../../../addons/smart_construction_core/data/formal_business_product_menu_policy_v1.json#L20)。

| Center | 入口 | Released | Preview | 不同模型数 |
|---|---:|---:|---:|---:|
| Workbench / 工作台 | 6 | 6 | 0 | 4 |
| Project / 项目中心 | 65 | 29 | 36 | 56 |
| Contract / 合同中心 | 8 | 7 | 1 | 5 |
| Cost / 成本中心 | 4 | 4 | 0 | 3 |
| Finance / 财务中心 | 14 | 11 | 3 | 9 |
| Tax / 税务中心 | 9 | 9 | 0 | 5 |
| Accounting / 会计账务中心 | 6 | 6 | 0 | 6 |
| Reporting / 报表中心 | 5 | 5 | 0 | 5 |
| Administration / 行政中心 | 8 | 8 | 0 | 6 |
| Product Configuration / 产品配置 | 7 | 7 | 0 | 7 |
| 合计 | 132 | 92 | 40 | 101 |

其中：

- 131 个入口绑定 Action。
- 1 个入口是无 Action 的 `workspace.home` Scene Entry。
- 128 个 Action 的 View Set 可由本仓库源码解释。
- 3 个 `account` Action 的 View Set 必须由外部模块运行态解释。

## 5. 三个 B 阶段样板入口

### 5.1 `payment.request`

正式路径：

```text
smart_construction_core.menu_sc_user_payment_apply
  -> smart_construction_core.action_payment_request_user_payment_apply
  -> payment.request
  -> tree,form
  -> view_payment_request_tree
  -> view_payment_request_pay_form
  -> view_payment_request_search
```

证据：

- 正式发布选择：
  [`product_menu_source.json:387`](../../../addons/smart_construction_core/data/product_menu_source.json#L387)。
- 菜单：
  [`menu_business_taxonomy.xml:927`](../../../addons/smart_construction_core/views/menu_business_taxonomy.xml#L927)。
- Action、显式 views/view_ids/search：
  [`menu_business_taxonomy.xml:442`](../../../addons/smart_construction_core/views/menu_business_taxonomy.xml#L442)。
- Tree：
  [`payment_request_views.xml:3`](../../../addons/smart_construction_core/views/core/payment_request_views.xml#L3)。
- Form header、按钮、statusbar：
  [`payment_request_views.xml:42`](../../../addons/smart_construction_core/views/core/payment_request_views.xml#L42)。
- Search：
  [`payment_request_views.xml:394`](../../../addons/smart_construction_core/views/core/payment_request_views.xml#L394)。

优先原因：View Set 显式、业务按钮齐全、同时覆盖 Odoo collaboration、tier validation、
domain/context、字段权限和付款执行。

### 5.2 `project.project`

正式路径：

```text
smart_construction_core.menu_sc_project_project
  -> smart_construction_core.action_sc_project_list
  -> project.project
  -> tree,kanban,form
  -> 多份继承 form/tree/kanban/search
```

证据：

- 正式发布选择：
  [`product_menu_source.json:153`](../../../addons/smart_construction_core/data/product_menu_source.json#L153)。
- 菜单：
  [`menu.xml:24`](../../../addons/smart_construction_core/views/menu.xml#L24)。
- Action 和创建入口 context：
  [`project_list_actions.xml:3`](../../../addons/smart_construction_core/actions/project_list_actions.xml#L3)。
- 核心表单继承：
  [`project_views.xml:82`](../../../addons/smart_construction_core/views/core/project_views.xml#L82)。
- 生命周期 Kanban：
  [`project_lifecycle_kanban_views.xml:32`](../../../addons/smart_construction_core/views/core/project_lifecycle_kanban_views.xml#L32)。
- 项目搜索：
  [`project_search_views.xml:3`](../../../addons/smart_construction_core/views/core/project_search_views.xml#L3)。

优先原因：一个入口包含多 View、13 个继承 View、复杂 x2many、stat buttons、
多关系和历史/财务扩展，适合验证“不是只显示默认 List”。

### 5.3 `project.task`

当前正式 132 入口没有直接 `project.task` 菜单。它通过项目 Form 的 stat button
`action_view_tasks` 或 Odoo `project` 原生动作进入：

[`project_views.xml:105`](../../../addons/smart_construction_core/views/core/project_views.xml#L105)。

仓库内仅有 3 个任务 View 扩展，全部继承 Odoo `project` 原生 View：

- 表单状态/审批：
  [`task_sc_state_views.xml:2`](../../../addons/smart_construction_core/views/support/task_sc_state_views.xml#L2)。
- Tree 状态列：
  [`task_sc_state_views.xml:23`](../../../addons/smart_construction_core/views/support/task_sc_state_views.xml#L23)。
- BOQ tab：
  [`task_boq_views.xml:2`](../../../addons/smart_construction_core/views/core/task_boq_views.xml#L2)。

优先原因：它可以验证 Button 返回 Action、Odoo 原生 Kanban/Activity/Calendar 等
外部 View、计划和任务协同。它应从 B07 开始并行，而不是在 B01-B06 中先假定
存在一个自定义产品菜单。

## 6. 正式产品 132 入口清单

下列链路由 `load_source()` 依据 native Menu/Action XML 解析，不是手工导航清单。

### Workbench

- `menu_sc_workspace_home` → `workspace.home` → scene → released
- `menu_sc_my_work` → `action_sc_my_work` → `project.project` → tree,form → released
- `menu_sc_operating_metrics_project` → `action_sc_operating_metrics_project` → `sc.operating.metrics.project` → tree,form,pivot → released
- `menu_sc_project_kanban` → `action_project_dashboard` → `project.project` → kanban,tree,form → released
- `menu_sc_workbench_my_todo_fact` → `action_sc_workbench_task_center` → `sc.workbench.item` → tree,form → released
- `menu_sc_product_message_notification_v1` → `action_sc_product_message_notification_v1` → `mail.notification` → tree,form → released

### Project

- `menu_sc_project_initiation` → `action_project_initiation` → `project.project` → form → released
- `menu_sc_project_quick_create` → `action_project_initiation_quick` → `project.project` → form → preview
- `menu_sc_product_project_lifecycle_v1` → `action_sc_product_project_lifecycle_v1` → `project.project` → tree,form → released
- `menu_sc_project_project` → `action_sc_project_list` → `project.project` → tree,kanban,form → released
- `menu_sc_customer_partner` → `action_sc_customer_partner` → `res.partner` → tree,form → released
- `menu_sc_supplier_partner` → `action_sc_supplier_partner` → `res.partner` → tree,form → released
- `menu_sc_product_partner_blacklist_v1` → `action_sc_product_partner_blacklist_v1` → `res.partner` → tree,form → released
- `menu_sc_product_tender_information_v1` → `action_sc_product_tender_information_v1` → `tender.opportunity` → tree,form → released
- `menu_sc_project_tender` → `action_tender_bid` → `tender.bid` → tree,form → released
- `menu_sc_product_tender_document_v1` → `action_sc_product_tender_document_v1` → `tender.document` → tree,form → released
- `menu_sc_tender_guarantee` → `action_sc_tender_guarantee` → `tender.guarantee` → tree,form → released
- `menu_sc_tender_won` → `action_sc_tender_won` → `tender.bid` → tree,form → released
- `menu_sc_tender_registration_fee` → `action_sc_tender_registration_fee` → `tender.doc.purchase` → tree,form → preview
- `menu_sc_tender_opening` → `action_sc_tender_opening` → `tender.opening` → tree,form → preview
- `menu_sc_safety_issue` → `action_sc_safety_issue` → `sc.safety.issue` → tree,form → released
- `menu_sc_product_quality_acceptance_v1` → `action_sc_product_quality_acceptance_v1` → `sc.quality.acceptance` → tree,form → released
- `menu_sc_project_documents` → `action_sc_project_document` → `sc.project.document` → tree,form → released
- `menu_sc_construction_diary` → `action_sc_construction_diary` → `sc.construction.diary` → tree,form → released
- `menu_sc_construction_progress` → `action_project_progress_entry` → `project.progress.entry` → tree,form → released
- `menu_sc_product_site_variation_v1` → `action_sc_product_site_variation_v1` → `sc.site.variation` → tree,form → released
- `menu_sc_product_labor_realname_v1` → `action_sc_product_labor_realname_v1` → `sc.labor.worker` → tree,form → released
- `menu_sc_product_labor_cost_v1` → `action_sc_product_labor_cost_v1` → `sc.labor.usage` → tree,form → released
- `menu_sc_product_labor_deduction_v1` → `action_sc_product_labor_deduction_v1` → `sc.labor.deduction` → tree,form → released
- `menu_sc_material_inbound` → `action_sc_material_inbound_handling` → `sc.material.inbound` → tree,form → released
- `menu_sc_material_outbound` → `action_sc_material_outbound` → `sc.material.outbound` → tree,form → released
- `menu_sc_product_material_return_v1` → `action_sc_material_supplier_return` → `sc.material.supplier.return` → tree,form → released
- `menu_sc_product_equipment_shift_v1` → `action_sc_equipment_usage` → `sc.equipment.usage` → tree,form → released
- `menu_sc_product_subcontract_cost_v1` → `action_sc_subcontract_register` → `sc.subcontract.register` → tree,form → released
- `menu_sc_product_subcontract_variation_v1` → `action_sc_product_subcontract_variation_v1` → `sc.site.variation` → tree,form → released
- `menu_sc_product_project_payroll_v1` → `action_sc_product_project_payroll_v1` → `sc.hr.payroll.document` → tree,form → released
- `menu_sc_product_project_salary_payment_v1` → `action_sc_product_project_salary_payment_v1` → `sc.hr.salary.payment` → tree,form → released
- `menu_sc_product_team_loan_deduction_v1` → `action_sc_product_team_loan_deduction_v1` → `sc.team.loan.deduction.workspace` → form → released
- `menu_sc_plan` → `action_sc_plan` → `sc.plan` → tree,form → preview
- `menu_sc_plan_report` → `action_sc_plan_report` → `sc.plan.report` → tree,form → preview
- `menu_sc_quality_issue` → `action_sc_quality_issue` → `sc.quality.issue` → tree,form → preview
- `menu_sc_quality_rectification` → `action_sc_quality_rectification` → `sc.quality.rectification` → tree,form → preview
- `menu_sc_quality_recheck` → `action_sc_quality_recheck` → `sc.quality.recheck` → tree,form → preview
- `menu_sc_quality_standard_v2` → `action_sc_check_standard` → `sc.check.standard` → tree,form → preview
- `menu_sc_quality_site_photo_v2` → `action_sc_site_photo_batch` → `sc.site.photo.batch` → tree,form → preview
- `menu_sc_safety_plan_v2` → `action_sc_safety_plan` → `sc.safety.plan` → tree,form → preview
- `menu_sc_safety_disclosure_v2` → `action_sc_safety_disclosure` → `sc.safety.disclosure` → tree,form → preview
- `menu_sc_safety_risk_library_v2` → `action_sc_risk_library` → `sc.risk.library` → tree,form → preview
- `menu_sc_safety_hazard_source_v2` → `action_sc_hazard_source` → `sc.hazard.source` → tree,form → preview
- `menu_sc_safety_patrol_v2` → `action_sc_safety_patrol_task` → `sc.safety.patrol.task` → tree,form → preview
- `menu_sc_safety_rectification` → `action_sc_safety_rectification` → `sc.safety.rectification` → tree,form → preview
- `menu_sc_safety_recheck` → `action_sc_safety_recheck` → `sc.safety.recheck` → tree,form → preview
- `menu_project_material_plan` → `action_project_material_plan` → `project.material.plan` → tree,form → preview
- `menu_sc_material_purchase_request` → `action_sc_material_purchase_request` → `sc.material.purchase.request` → tree,form → preview
- `menu_sc_material_acceptance` → `action_sc_material_acceptance` → `sc.material.acceptance` → tree,form → preview
- `menu_sc_material_rfq` → `action_sc_material_rfq` → `sc.material.rfq` → tree,form → preview
- `menu_sc_material_transfer` → `action_sc_material_transfer` → `sc.material.outbound` → tree,form → preview
- `menu_sc_material_loss` → `action_sc_material_loss` → `sc.material.outbound` → tree,form → preview
- `menu_sc_material_settlement` → `action_sc_material_settlement` → `sc.material.settlement` → tree,form → preview
- `menu_sc_labor_plan` → `action_sc_labor_plan` → `sc.labor.plan` → tree,form → preview
- `menu_sc_labor_request` → `action_sc_labor_request` → `sc.labor.request` → tree,form → preview
- `menu_sc_labor_settlement` → `action_sc_labor_settlement` → `sc.labor.settlement` → tree,form → preview
- `menu_sc_equipment_plan` → `action_sc_equipment_plan` → `sc.equipment.plan` → tree,form → preview
- `menu_sc_equipment_request` → `action_sc_equipment_request` → `sc.equipment.request` → tree,form → preview
- `menu_sc_equipment_settlement` → `action_sc_equipment_settlement` → `sc.equipment.settlement` → tree,form → preview
- `menu_sc_material_rental_plan` → `action_sc_material_rental_plan` → `sc.material.rental.plan` → tree,form → preview
- `menu_sc_material_rental_order` → `action_sc_material_rental_order` → `sc.material.rental.order` → tree,form → preview
- `menu_sc_material_rental_settlement` → `action_sc_material_rental_settlement` → `sc.material.rental.settlement` → tree,form → preview
- `menu_sc_subcontract_plan` → `action_sc_subcontract_plan` → `sc.subcontract.plan` → tree,form → preview
- `menu_sc_subcontract_request` → `action_sc_subcontract_request` → `sc.subcontract.request` → tree,form → preview
- `menu_sc_subcontract_settlement` → `action_sc_subcontract_settlement` → `sc.subcontract.settlement` → tree,form → preview

### Contract

- `menu_sc_p1_income_contract` → `action_construction_contract_income` → `construction.contract.income` → tree,form → released
- `menu_sc_p1_expense_contract` → `action_construction_contract_expense` → `construction.contract.expense` → tree,form → released
- `menu_sc_p1_contract_change` → `action_sc_contract_change` → `sc.contract.change` → tree,form → released
- `menu_sc_p1_daily_contract` → `action_sc_general_contract` → `sc.general.contract` → tree,form → released
- `menu_sc_product_general_contract_settlement_v1` → `action_sc_product_general_contract_settlement_v1` → `sc.settlement.order` → tree,form → released
- `menu_sc_p1_income_settlement` → `action_sc_settlement_order_income` → `sc.settlement.order` → tree,form → released
- `menu_sc_p1_expense_settlement` → `action_sc_settlement_order_expense` → `sc.settlement.order` → tree,form → released
- `menu_sc_settlement_order` → `action_sc_settlement_order` → `sc.settlement.order` → tree,form → preview

### Cost

- `menu_sc_p1_project_budget` → `action_project_budget` → `project.cost.plan` → tree,form → released
- `menu_sc_p1_cost_plan` → `action_project_cost_plan` → `project.cost.plan` → tree,form → released
- `menu_sc_p1_cost_ledger` → `action_project_cost_ledger` → `project.cost.ledger` → tree,form,pivot,graph → released
- `menu_sc_p1_profit_analysis` → `action_project_profit_compare` → `project.profit.compare` → tree,form,pivot → released

### Finance

- `menu_sc_receipt_income` → `action_sc_receipt_income` → `sc.receipt.income` → tree,form → released
- `menu_sc_user_payment_apply` → `action_payment_request_user_payment_apply` → `payment.request` → tree,form → released
- `menu_sc_payment_execution` → `action_sc_payment_execution_actual_outflow` → `sc.payment.execution` → tree,form → released
- `menu_sc_reimbursement_request` → `action_sc_expense_claim_reimbursement_request` → `sc.expense.claim` → tree,form → released
- `menu_sc_product_current_account_v1` → `action_sc_product_current_account_v1` → `sc.current.account.workspace` → form → released
- `menu_sc_user_income` → `action_sc_receipt_income_user_income` → `sc.receipt.income` → tree,form → released
- `menu_sc_company_finance_expense` → `action_sc_payment_execution_company_finance_expense` → `sc.payment.execution` → tree,form → released
- `menu_sc_deduction_bill` → `action_sc_expense_claim_deduction_bill` → `sc.expense.claim` → tree,form → released
- `menu_sc_product_company_project_refund_v1` → `action_sc_product_company_project_refund_v1` → `sc.company.project.refund.workspace` → form → released
- `menu_sc_advance_fund` → `action_sc_expense_claim_advance_fund` → `sc.expense.claim` → tree,form → released
- `menu_sc_funding_plan_summary` → `action_project_funding_baseline_summary` → `project.funding.baseline` → tree,form → released
- `menu_sc_engineering_progress_income` → `action_sc_receipt_income_engineering_progress` → `sc.receipt.income` → tree,form → preview
- `menu_payment_ledger` → `action_payment_ledger` → `payment.ledger` → tree,form → preview
- `menu_sc_treasury_ledger` → `action_sc_treasury_ledger` → `sc.treasury.ledger` → tree,form → preview

### Tax

- `menu_sc_tax_certificate_registration_user` → `action_sc_tax_certificate_registration_user` → `sc.tax.certificate.registration` → tree,form → released
- `menu_sc_invoice_prepaid_tax_user` → `action_sc_invoice_prepaid_tax_user` → `sc.invoice.registration` → tree,form → released
- `menu_sc_invoice_application_user` → `action_sc_invoice_application_user` → `sc.invoice.registration` → tree,form → released
- `menu_sc_invoice_registration_user` → `action_sc_invoice_registration_user` → `sc.invoice.registration` → tree,form → released
- `menu_sc_output_invoice_change_registration` → `action_sc_output_invoice_change_registration` → `sc.output.invoice.adjustment` → tree,form → released
- `menu_sc_invoice_input` → `action_sc_invoice_input` → `sc.invoice.registration` → tree,form → released
- `menu_sc_tax_deduction_registration_user` → `action_sc_tax_deduction_registration_user` → `sc.tax.deduction.registration` → tree,form → released
- `menu_sc_product_project_tax_deduction_v1` → `action_sc_product_project_tax_deduction_v1` → `sc.tax.deduction.registration` → tree,form → released
- `menu_sc_product_tax_filing_v1` → `action_sc_product_tax_filing_v1` → `sc.tax.filing` → tree,form → released

### Accounting

- `account.menu_action_move_journal_line_form` → `account.action_move_journal_line` → `account.move` → external view set → released
- `account.menu_action_account_moves_all` → `account.action_account_moves_all` → `account.move.line` → external view set → released
- `account.menu_action_account_form` → `account.action_account_form` → `account.account` → external view set → released
- `menu_sc_account_journal_foundation` → `action_sc_account_journal_foundation` → `account.journal` → tree,form → released
- `menu_sc_analytic_account_foundation` → `action_sc_analytic_account_foundation` → `account.analytic.account` → tree,form → released
- `menu_sc_analytic_distribution_foundation` → `action_sc_analytic_distribution_foundation` → `account.analytic.distribution.model` → tree,form → released

### Reporting

- `menu_sc_project_operation_statistics_report` → `action_sc_project_operation_statistics_report` → `sc.operating.metrics.project` → tree,form,pivot → released
- `menu_sc_comprehensive_cost_statistics_report` → `action_sc_comprehensive_cost_statistics_report` → `sc.comprehensive.cost.summary` → tree,form,pivot,graph → released
- `menu_sc_fund_daily_summary` → `action_sc_fund_daily_summary` → `sc.fund.daily.summary` → tree,form,pivot,graph → released
- `menu_sc_product_tax_report_v1` → `action_sc_product_tax_report_v1` → `sc.tax.filing` → pivot,graph,tree → released
- `menu_sc_product_labor_subcontract_report_v1` → `action_sc_product_labor_subcontract_report_v1` → `sc.labor.subcontract.report` → pivot,graph,tree,form → released

### Administration

- `menu_sc_organization_department` → `action_sc_organization_department` → `hr.department` → tree,form → released
- `menu_sc_product_job_management_v1` → `action_sc_product_job_management_v1` → `hr.job` → tree,form → released
- `menu_sc_runtime_user_management` → `action_sc_runtime_user_management` → `res.users` → tree,form → released
- `menu_sc_certificate_registration` → `action_sc_certificate_registration` → `sc.document.admin.document` → tree,form → released
- `menu_sc_product_social_fund_v1` → `action_sc_product_social_fund_v1` → `sc.hr.payroll.document` → tree,form → released
- `menu_sc_payroll_management` → `action_sc_payroll_management` → `sc.hr.payroll.document` → tree,form → released
- `menu_sc_product_office_asset_v1` → `action_sc_product_office_asset_v1` → `sc.office.asset` → tree,form → released
- `menu_sc_product_policy_document_v1` → `action_sc_product_policy_document_v1` → `sc.document.admin.document` → tree,form → released

### Product Configuration

- `menu_sc_business_config_workbench` → `action_sc_business_config_workbench` → `ui.business.config.contract` → tree,form → released
- `menu_sc_approval_policy` → `action_sc_approval_policy` → `sc.approval.policy` → tree,form → released
- `menu_ui_form_field_policy_business_config` → `action_ui_form_field_policy_business_config` → `ui.form.field.policy` → tree,form → released
- `menu_ui_menu_config_policy_business_config` → `smart_core.action_ui_menu_config_policy` → `ui.menu.config.policy` → tree,form → released
- `menu_sc_product_data_permission_v1` → `action_sc_product_data_permission_v1` → `res.users` → tree,form → released
- `menu_sc_product_system_parameter_v1` → `action_sc_product_system_parameter_v1` → `sc.product.system.settings` → form → released
- `menu_sc_product_numbering_rule_v1` → `action_sc_product_numbering_rule_v1` → `ir.sequence` → tree,form → released

## 7. A08 判定

- 一个稳定的 `Menu + Action + full View Set` 已经在结构上构成独立场景交付单元。
- 目前正式产品 132 入口覆盖 101 个模型，场景单元不需要新增场景模型即可交付大部分业务。
- 当前仍有三类不能直接下结论的入口：
  - 外部 Odoo Action 的 View Set；
  - 无 Action 但由 Scene 承载的入口；
  - 无菜单、由对象方法/按钮返回的 Action。
- 组合场景只应在跨对象流程、统一驾驶舱或多专业视图组合时引入，不应替代单入口原生交付。
- 下一轮 B01-B06 应先验证复合身份、Action/View Set、Search/Form/List，暂不扩展到
  Kanban、Wizard、Chatter 和完整业务执行。
