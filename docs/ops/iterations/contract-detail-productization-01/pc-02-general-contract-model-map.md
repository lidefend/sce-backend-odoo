# PC-02 · 综合合同 sc.general.contract 产品映射（代码事实审计）

结论类型：CODE_FACT（只读审计）。

## 1. 模型与入口

- 模型：`sc.general.contract`（综合合同），`general_contract.py`，独立模型。
- 继承：`_inherit = ["mail.thread", "mail.activity.mixin", "tier.validation"]`，与
  `construction.contract` **无继承关系**。
- 权威导航入口：`smart_construction_core.menu_sc_p1_daily_contract` →
  `smart_construction_core.action_sc_general_contract`。
- 表单：`view_sc_general_contract_form`。

## 2. 身份字段映射（与 construction.contract 不同）

| 展示职责 | sc.general.contract 字段 | 说明 |
| --- | --- | --- |
| 合同主标题 | `contract_name`（合同名称） | 不是 `subject` |
| 平台合同编号 | `contract_no`（合同编号，只读） | 不是 `name` |
| 登记单号 | `name`（登记单号） | `name` 在此模型是登记单号 |
| 合同方向 | `contract_direction`（income/expense） | 不是 `type` |
| 生命周期 | `state`（draft/confirmed/signed/legacy_confirmed/cancel） | statusbar |
| 审批状态 | `validation_status`（tier.validation，invisible） | 无独立 `document_status` 字段 |
| 合同相对方 | `partner_id`（往来单位） | |
| 关联项目 | `project_id`（关联项目） | |
| 合同类型 | `contract_type`（Char） | 不是 `business_category_id` |

## 3. 金额字段映射

| 层级 | sc.general.contract 字段 | 说明 |
| --- | --- | --- |
| 原始合同金额 | `amount_untaxed`（不含税）、`tax_id`/`tax_rate`、`amount_total`（合同金额） | 无独立 `amount_tax` 金额字段 |
| 合同变更 | `change_amount_total`（累计变更金额）+ `change_rate` | 不是 `amount_change` |
| 最终合同价 | `amount_total`（合同金额） | 无独立 `amount_final` |
| 合同结算 | `settlement_amount`（结算金额） | 无 `settlement_balance` |
| 资金履约 | `invoice_amount`/`uninvoiced_amount`、`received_amount`/`unreceived_amount`、`paid_amount`/`unpaid_amount`、`prepayment_amount`、`install_*`、`warranty_deposit` | |

## 4. 关键差异与冻结

- `sc.general.contract` 与 `construction.contract` 是两套独立字段与计算链，字段同名也不可混用。
- 三个 NOT_VERIFIED 边界在综合合同模型下需按本模型口径重新记录，不能沿用基础模型结论。
- 无 `subject`、`document_status`、`business_category_id`、`type`、`amount_final`、`settlement_balance`、`amount_tax` 金额字段。

## 5. 结论

PC-02 当前产品化应以 `sc.general.contract` 的 `view_sc_general_contract_form` 为落点，
按上述字段重新映射 P1 身份带与 P2 金额带，不复用 construction.contract 的字段映射。
