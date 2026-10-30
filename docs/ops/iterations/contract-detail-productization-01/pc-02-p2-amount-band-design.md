# PC-02 · P2 五层金额状态带设计

结论类型：DESIGN_PROPOSAL（字段映射与视图配置设计）；CODE_FACT 为源码事实；
NOT_VERIFIED 为待业务裁定。

## 1. 目标

把当前 `金额概览` 分组里平铺的 25 个金额字段，重组为五层连续的金额状态带：
原始合同金额 → 合同变更 → 最终合同价 → 合同结算 → 资金履约。

实现原则：优先原生视图分组、字段映射与已有标准组件；不新建合同专属 Vue 渲染器；
不改金额计算、ACL、record rule、审批逻辑。

## 2. 字段到展示层级映射

| 层 | 层级名 | 字段 | 展示口径 |
| --- | --- | --- | --- |
| L1 | 原始合同金额 | `amount_untaxed`（未税）、`amount_tax`（税额）、`amount_total`（含税） | 未税 + 税额 = 含税 |
| L2 | 合同变更 | `amount_change`、变更单关系 | `amount_change` 当前恒 0（`_compute_final_amount` 硬编码 0.0） |
| L3 | 最终合同价 | `amount_final` | 履约执行基准，视觉权重最高 |
| L4 | 合同结算 | `settlement_amount`、`settlement_balance` | 已结算 / 未结算 |
| L5 | 资金履约 | `invoice_amount`、`uninvoiced_amount`、`received_amount`/`unreceived_amount`（out）、`paid_amount`/`unpaid_amount`（in）、`historical_*`、`cumulative_paid_amount` | 开票 / 收款（out）或付款（in）及历史承接 |

权威口径以 `pc-02-amount-field-map.md` 为准：所有履约执行（结算/开票/收款/付款/余额/比例）
基准均为 `amount_final`，不是 `amount_total`。

## 3. 五层配置结构

建议在 `view_construction_contract_form` 中用五个具名分组表达，按收入/支出方向调整内容：

```xml
<group name="sc_contract_amount_original" string="原始合同金额" col="4"
       data-sc-anchor="contract-amount-original">
  <field name="amount_untaxed" string="未税金额" readonly="1"/>
  <field name="amount_tax" string="税额" readonly="1"/>
  <field name="amount_total" string="含税金额" readonly="1"/>
</group>
<group name="sc_contract_amount_change" string="合同变更" col="4"
       data-sc-anchor="contract-amount-change">
  <field name="amount_change" string="累计变更金额" readonly="1"/>
</group>
<group name="sc_contract_amount_final" string="最终合同价" col="4"
       data-sc-anchor="contract-amount-final">
  <field name="amount_final" string="最终合同价" readonly="1"/>
</group>
<group name="sc_contract_amount_settlement" string="合同结算" col="4"
       data-sc-anchor="contract-amount-settlement">
  <field name="settlement_amount" string="已结算" readonly="1"/>
  <field name="settlement_balance" string="未结算" readonly="1"/>
</group>
<group name="sc_contract_amount_fulfillment" string="资金履约" col="4"
       data-sc-anchor="contract-amount-fulfillment">
  <!-- out: 开票/收款；in: 付款/未付款，由 existing type 驱动 -->
</group>
```

以上为设计示意，实施时按现有字段的 `invisible`/`type` 能力做方向适配，不引入新字段。

## 4. 收入/支出共用一套结构

- `type=out`（收入）：资金履约突出 `invoice_amount`/`uninvoiced_amount`、
  `received_amount`/`unreceived_amount`。
- `type=in`（支出）：资金履约突出 `settlement_amount`/`settlement_balance`、
  `paid_amount`/`unpaid_amount`。

使用现有 `type` 字段的 `invisible` 表达式控制可见性，不建两套页面。

## 5. 关键表达约束

1. 最终合同价 `amount_final` 突出，但与原始 `amount_total` 分属不同层，不混淆。
2. `amount_change` 当前恒为 0，必须表达为「变更金额计算尚未接入」，不得表达为「无变更」。
3. 历史付款 `historical_*` 与新系统流 `new_system_flow_paid_amount` 分项展示，
   `cumulative_paid_amount` 作为累计突出，分项作为明细。
4. 币种 `currency_id` 与数值紧密关联，精度与空态统一。
5. 结算超最终价时 `settlement_balance` 可能为负，UI 不得静默截断。

## 6. 冻结的 NOT_VERIFIED 边界（P2 不解决）

1. 变更单 `amount_delta` 是否汇总至 `amount_change`。
2. 结算金额是否允许超过最终合同价。
3. 历史付款与新系统付款的业务边界与去重口径。

## 7. 实施与验收顺序

1. 仅改 `contract_views.xml` 的原生分组，不改金额计算/ACL/审批。
2. 静态质量门禁：字段映射、分组结构、结构锁定、无新增专属 Vue。
3. 真实合同数据核对：用 candidate 库既有 5 条合同抽样核对五层字段值。
4. 浏览器几何验收：待 P4 candidate lane 接通后统一执行。
