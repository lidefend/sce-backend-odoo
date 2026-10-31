# PC-02 · 金额字段权威映射

目标模型：`construction.contract`（`addons/smart_construction_core/models/support/contract_center.py`，
`contract_business.py`，`historical_payment_fact.py`）。

结论类型：CODE_FACT 为源码事实；DESIGN_PROPOSAL 为产品设计；NOT_VERIFIED 为待业务裁定。

## 权威字段表

| 展示项 | 权威字段 | 计算/来源 | 类型 |
| --- | --- | --- | --- |
| 平台合同金额（未税） | `amount_untaxed` | `_compute_amount_total` = round(`line_amount_total`) | CODE_FACT |
| 可见合同金额 | `visible_contract_amount` | `_compute_visible_contract_amount` = `amount_untaxed`；inverse 写回 `amount_untaxed` | CODE_FACT |
| 税额 | `amount_tax` | round(untaxed × tax_id.amount%)，percent 且 price_include=false | CODE_FACT |
| 含税金额 | `amount_total` | round(untaxed + tax) | CODE_FACT |
| 合同明细合计 | `line_amount_total` | Σ `line_ids.amount_contract` | CODE_FACT |
| 累计变更金额 | `amount_change` | `_compute_final_amount` 当前硬编码 0.0（变更模块未上线） | CODE_FACT |
| 最终合同价 | `amount_final` | `_compute_final_amount` = `amount_total` + `amount_change`（当前 = amount_total） | CODE_FACT |
| 结算金额 | `settlement_amount` | `contract_execution_position_map` 的 `settled`（Σ sc.settlement.order.line，结算单 approve/done） | CODE_FACT |
| 未结算金额 | `settlement_balance` | `amount_final` − `settlement_amount` | CODE_FACT |
| 开票金额 | `invoice_amount` | `invoiced_output`（out）/ `invoiced_input`（in） | CODE_FACT |
| 未开票金额 | `uninvoiced_amount` | `amount_final` − `invoice_amount` | CODE_FACT |
| 收款金额 | `received_amount` | `received`（仅 out） | CODE_FACT |
| 未收款金额 | `unreceived_amount` | `amount_final` − `received_amount`（仅 out） | CODE_FACT |
| 付款金额 | `paid_amount` | `paid`（仅 in） | CODE_FACT |
| 未付款金额 | `unpaid_amount` | `amount_final` − `paid_amount`（仅 in） | CODE_FACT |
| 现金执行金额 | `cash_executed_amount` | out=received / in=paid | CODE_FACT |
| 现金未执行金额 | `cash_balance` | `amount_final` − `cash_executed_amount` | CODE_FACT |
| 结算/开票/现金执行比例 | `settlement_rate`/`invoice_rate`/`cash_execution_rate` | 已执行额 ÷ `amount_final` × 100 | CODE_FACT |
| 历史已确认付款 | `historical_confirmed_paid_amount` | Σ `historical_payment_fact_ids` 已确认 | CODE_FACT |
| 历史待确认付款 | `historical_amount_pending_confirmation` | Σ `historical_payment_fact_ids` 待确认 | CODE_FACT |
| 新系统流付款 | `new_system_flow_paid_amount` | 新系统流付款汇总 | CODE_FACT |
| 累计付款 | `cumulative_paid_amount` | 历史已确认 + 新系统流 | CODE_FACT |

## 关键事实

- `visible_contract_amount` 与 `amount_untaxed` 同口径（未税）；`amount_total` 是含税，两者不同口径。CODE_FACT
- 所有履约执行（结算/开票/收款/付款/余额/比例）的基准都是 `amount_final`，不是 `amount_total`。CODE_FACT
- `amount_change` 当前恒为 0，且未消费 `sc.contract.change.amount_delta`。NOT_VERIFIED（变更单是否应汇总至此）
- 结算单金额来源为 `sc.settlement.order.line`（approve/done）；开票/收款/付款来自
  `contract_execution_position_map` 的对应业务单据。CODE_FACT
