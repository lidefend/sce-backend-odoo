# PC-02 · 五层金额状态带设计

结论类型：DESIGN_PROPOSAL（产品设计，不是已实现能力）。

## 设计原则

合同金额具有时间与业务上的连续关系，应表达为连续状态带，而不是四张并列卡片或 20 个平铺字段。
每个答案必须来自 CODE_FACT 字段，不补未经确认的业务结论。

## 五层结构

1. 原始合同金额：`amount_untaxed`（未税）+ `amount_tax`（税额）= `amount_total`（含税）。
2. 合同变更：`amount_change`；当前计算未接入，必须表达为「变更金额计算尚未接入」，不得表达为「无变更」。
3. 最终合同价：`amount_final`（履约执行基准）。
4. 结算：`settlement_amount` / `settlement_balance`。
5. 资金履约：`invoice_amount`/`uninvoiced_amount`、`received_amount`/`unreceived_amount`（out）、
   `paid_amount`/`unpaid_amount`（in）、`historical_*`。

## 每层表达要求

- 金额值视觉权重最高；单位（币种）与数值紧密关联。
- 第二层变更在 `amount_change` 未接入时显示「待接入」状态，不显示假 0。
- 第四/五层的「已/未」成对呈现，负值（如结算超最终价）作为 NOT_VERIFIED 状态不预设结论。

## 待裁定

- 变更汇总口径、结算上限、历史付款边界（见 financial-semantics 文档）。NOT_VERIFIED
