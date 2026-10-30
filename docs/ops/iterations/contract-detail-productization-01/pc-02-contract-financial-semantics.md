# PC-02 · 资金履约与历史承接口径

结论类型：CODE_FACT 为源码事实；NOT_VERIFIED 为待业务裁定。

## 执行基准

`contract_center._compute_execution_amounts` 以 `amount_final`（最终合同价）为唯一执行基准：
`uninvoiced/unreceived/unpaid/settlement_balance/cash_balance` 及三个执行比例都从 `amount_final`
扣减或相除。CODE_FACT

## 履约口径

| 维度 | 收入合同（type=out） | 支出合同（type=in） | 类型 |
| --- | --- | --- | --- |
| 结算 | `settlement_amount`（结算单 approve/done） | 同 | CODE_FACT |
| 开票 | `invoiced_output` | `invoiced_input` | CODE_FACT |
| 收款 | `received_amount` | 恒 0 | CODE_FACT |
| 付款 | 恒 0 | `paid_amount` | CODE_FACT |

## 历史付款承接

`historical_payment_fact_ids`（One2many）汇总为：

- `historical_confirmed_paid_amount`：已确认历史付款。
- `historical_amount_pending_confirmation`：待确认历史付款。
- `new_system_flow_paid_amount`：新系统流付款。
- `cumulative_paid_amount`：历史已确认 + 新系统流。

CODE_FACT；但「历史付款」与「新系统流付款」的业务边界 NOT_VERIFIED。

## 待裁定事项（不得在 UI 自行补结论）

1. 变更单 `amount_delta` 是否汇总至 `amount_change`，进而影响 `amount_final`。NOT_VERIFIED
2. 结算金额能否超过最终合同价（`settlement_balance` 可为负？）。NOT_VERIFIED
3. 历史付款与当前系统付款的边界与去重口径。NOT_VERIFIED
