# P1 报表投影可用性收口：后端可实施任务交接（2026-09-24）

> 归档说明（2026-09-28）：本件迁入自 `audit/formal-entry-gap-intake@28d2e05e`，下文运行观察、对象 ID 和验收状态属于 2026-09-24 原候选及环境；不是当前 main 的新运行结果。拟议字段映射与创建能力仍待产品确认及责任层实施，本轮仅恢复交接文档，不升级任何入口验收状态。

来源缺口：`frontend_shared_foundation_gap_audit_20260909.md` → `G-F3-03 / B04`。
本文件是**交给后端/产品责任层的一份可实施任务**（模型、字段映射、拟改文件、更新策略、验收用例），
不是前端任务，也不改通用兼容层。定位结论见 `report_center_projection_availability_20260924.md`。

## 1. 三个恒空视图的正式入口、模型与字段

| 报表 | 正式入口 | action | 模型 | 视图类型 |
|---|---|---|---|---|
| 资金报表 | `ir.ui.menu 366`（父 309 报表中心） | `699`（企业资金日报汇总） | `sc.fund.daily.summary` | view, `WHERE false` |
| 成本报表 | `ir.ui.menu 592`（父 309 报表中心） | `826`（另有 `705` 同模型） | `sc.comprehensive.cost.summary` | view, `WHERE false` |
| 应收应付报表 | **无菜单**（仅存在 action `698`） | `698` | `sc.ar.ap.report.summary` | view, `WHERE false` |

- `sc.fund.daily.summary` 字段：`display_name, document_date, company_id, business_entity_id, business_entity_name,
  project_id, project_name, account_name, bank_account_no, line_count, daily_income, daily_expense, net_amount,
  account_balance, current_account_balance, current_bank_balance, bank_system_difference`；
  其下钻 `action_open_snapshot_facts` 依赖 `document_scope='enterprise'` 的**企业资金日报快照事实**，
  但本构建**不存在** `sc.fund.daily` / `sc.fund.daily.snapshot` / `sc.legacy.fund.daily.snapshot.fact` 任何表。
- `sc.comprehensive.cost.summary` 字段：合同/收款/开票/未收、应付/供货/材料/劳务/租赁/费用/工资成本、
  成本发票、已付/未付、成本合计、利润额/利润率、四类计数、`coverage_note`。
- `sc.ar.ap.report.summary` 字段：施工合同价、已收/已开票/已收未开票/已开票未收、供货合同价、已付、
  应付已开票/开票未付/付款未开票、销项/进项/抵扣税额、税负、销项/进项附加、`coverage_note`。

## 2. 首批实施对象（建议）

**成本报表 `sc.comprehensive.cost.summary`（menu 592 / action 826）**。理由：

1. 唯一同时具备**正式菜单入口**与**按项目键可用的已填充来源**的报表；
   资金报表的来源模型在本构建缺失，应收应付报表没有正式入口。
2. 行内动作方法已实现且已携带对象上下文（`_project_domain()` / `_project_context()`，见 §5），
   缺的只是行。

## 3. 权威来源核对：`sc.finance.business.fact` 不足以支撑该报表

- `sc_finance_business_fact` 实测仅 3 行：`guarantee_deposit/guarantee_out`(1)、`guarantee_deposit/guarantee_return`(1)、
  `tax_deduction/tax_deducted`(1)。**不含收款、开票、合同、材料、工资任何域**。
- 因此「事实表有 3 行」不能证明可构成完整报表；不作为该报表的权威来源。
- 已填充且按项目键可用的来源（实测行数）：`sc_income_contract_ledger` 47、`sc_expense_contract_ledger` 58、
  `sc_output_invoice_ledger` 2、`sc_expense_reimbursement_summary` 1、`sc_salary_summary` 1。
- 可作为模板的**已工作先例**：`sc.finance.project.counterparty.position` 以 `init()` 建
  `CREATE OR REPLACE VIEW … SELECT … FROM sc_finance_business_fact`（`to_regclass` 守卫，view，3 行）。

## 4. 字段映射（grain = `company_id` × `project_id`）

关联键统一为 `project_id`（`project_project.id`）与 `company_id`；币种取该组内 `currency_id`（同项目须唯一，
否则按 §7 的用例拒绝）。

| 报表字段 | 权威来源 | 计算规则 |
|---|---|---|
| `income_contract_amount` | `sc_income_contract_ledger.amount_total` | `sum()`，排除 `state='cancel'` |
| `receipt_amount` | `sc_income_contract_ledger.received_amount` | `sum()` |
| `output_invoice_amount` | `sc_output_invoice_ledger.invoice_amount` | `sum()`（含冲红调整）；与 `sc_income_contract_ledger.invoice_amount` 对账 |
| `receivable_unpaid_amount` | `sc_income_contract_ledger.unreceived_amount` | `sum()` |
| `payable_contract_amount` | `sc_expense_contract_ledger.amount_total` | `sum()` |
| `supplier_contract_amount` | `sc_expense_contract_ledger.amount_total` | `sum()`，`contract_type='supplier'` |
| `labor_cost_amount` | `sc_expense_contract_ledger.amount_total` | `sum()`，`contract_type ∈ {labor, subcontract}` |
| `lease_cost_amount` | `sc_expense_contract_ledger.amount_total` | `sum()`，`contract_type ∈ {lease, machinery}` |
| `expense_cost_amount` | `sc_expense_reimbursement_summary.approved_amount` | `sum()` |
| `paid_amount` | `sc_expense_contract_ledger.paid_amount` | `sum()` |
| `payable_unpaid_amount` | `sc_expense_contract_ledger.unpaid_amount` | `sum()` |
| `total_cost_amount` | 上述成本字段 | `material+labor+lease+expense+salary`（缺项按 `coverage_note` 声明） |
| `profit_amount` | 派生 | `income_contract_amount - total_cost_amount` |
| `profit_rate` | 派生 | `income_contract_amount != 0 ? profit/income*100 : 0`（不得除零） |
| `source_line_count` | 上述来源 | 参与聚合的来源行数合计 |
| `material_line_count` | — | 见 §6 开放项 |
| `expense_line_count` | `sc_expense_reimbursement_summary.claim_count` | `sum()` |
| `salary_line_count` | — | 见 §6 开放项 |
| `coverage_note` | 派生 | 逐项声明不可得来源（材料成本、工资、成本发票），不得静默填 0 |

**公司／权限过滤责任**：投影只暴露 `company_id` / `project_id`，**不在视图里写权限**。
权限由记录规则承担，已有一致先例：`rule_sc_project_user_finance_business_fact`
（`['|',('project_id.user_id','=',user.id),('project_id.message_follower_ids.partner_id','=',user.partner_id.id)]`）、
`rule_sc_project_manager_finance_business_fact`（`[(1,'=',1)]`）与
`rule_sc_project_user_finance_project_counterparty_position`。新投影需配同型规则。

## 5. 运行时更新方式

**采用只读视图，不使用物化与刷新任务。** 视图在每次读取时计算：无刷新触发、天然幂等、
不存在「刷新失败后恢复」问题，也就不会再依赖只在迁移期执行的刷新函数
（现行仅迁移期使用的 `refresh_ar_ap_project_summary` 不得作为本报表的运行时机制）。
若后续确有必要物化，必须同时定义刷新触发、幂等键与失败恢复，并单独评审。

## 6. 明确开放项（不得静默补零）

- `material_cost_amount` / `material_line_count`：本构建无按项目键的材料成本台账
  （存在 `sc_material_plan/acceptance/inbound` 等单据，但无可直接汇总的成本口径），需产品确认权威口径。
- `salary_cost_amount` / `salary_line_count`：`sc.salary.summary` **没有 `project_id`**
  （只有 `period_year/month`、`department_id`、`payer_unit`），无法按项目归属；需产品确认按项目分摊规则。
- `input_invoice_amount`：无已填充的进项台账（`sc_invoice_registration` 仅 2 行且未成台账口径）。

以上三项在实现首版时以 `coverage_note` 明示，不参与 `total_cost_amount` 的默认真值。

## 7. 拟改文件

| 文件 | 改动 |
|---|---|
| `addons/smart_construction_core/models/projection/comprehensive_cost_summary.py` | `init()` 不再调用 `_create_empty_projection_view()`，改为按 §4 建权威只读视图（`to_regclass` 守卫 + `tools.drop_view_if_exists`，模板见 `finance_project_counterparty_position.py::init()`） |
| `addons/smart_construction_core/security/sc_record_rules.xml` | 新增 `model_sc_comprehensive_cost_summary` 的项目成员/经理记录规则（同 §4 先例） |
| `addons/smart_construction_core/tests/test_comprehensive_cost_summary_projection.py`（新增） | §8 用例 |

不改动：`optional_product_projection.py`（兼容桥接层保持原责任，不承载业务事实所有权）；
不读取客户交接材料；不复制客户事实进通用模块。

## 8. 验收用例（必须非零且覆盖以下各项）

1. **金额与来源对账**：每个可派生金额字段与来源台账按 `project_id` 汇总逐项相等（含一项目多合同/多开票/冲红）。
2. **公司隔离**：两公司数据下按 `company_id` 分组不串账；跨公司同项目编号不合并。
3. **无权限反例**：非项目成员用户在项目成员规则下看不到该项目行；经理组按 `[(1,'=',1)]` 可见；
   直接按 id 读取被拒。
4. **来源变化后结果更新**：新增/取消一条来源台账记录后，重读投影立即反映（验证视图而非迁移快照）。
5. **行内动作对象上下文**：`action_open_receipts` / `action_open_output_invoices` 等返回的
   `domain` 与 `context` 携带当前行 `project_id`（`_project_domain()` / `_project_context()`）；
   未归属项目的行为 `project_id = False` 且不误带其他项目。
6. **空与非空**：无来源的项目不产生行或产生全 0 行均可接受，但**不得报错**，且 `coverage_note` 明示缺项。
7. **币种一致**：同一 `project_id` 出现多币种时按 §4 拒绝或显式拆分，不得静默相加。

## 9. 边界

- 本交接不含前端改动；前端继续按契约渲染（空列表是当前的真实表达）。
- 「收款登记」等行内按钮目标即 action 637（已验收的同一收款列表 URL），缺的是投影行触发而非目标路由。
- 资金报表与应收应付报表在本构建缺少来源/入口，不纳入首批；如需上线需先补来源或入口，单独评审。
