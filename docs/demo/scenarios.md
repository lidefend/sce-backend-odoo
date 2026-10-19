# 正式 Demo 业务场景目录（S00–S30）

本文件定义 Smart Construction Demo 租户的正式业务场景、业务目标、
核心模型与可验证断言。场景编号仅用于数据装载与回归定位，不进入用户可见字段。

目标：
- 作为正式 Demo 的数据装载与回归测试统一入口
- 作为业务规则的“可执行样本库”
- 为后续业务场景提供设计基准

边界：
- 正式 Demo 只包含可正常演示的真实业务数据。
- 失败路径、门禁拒绝、修复演练属于产品测试面，由产品测试用例保证，
  不进入正式 Demo 数据集。

## Scenario Index

| Code | Name | Business Goal | Core Models | Verification Focus |
|-----:|------|---------------|-------------|--------------------|
| S00 | Minimal Path | 项目最短可跑路径 | project / boq / material / invoice | 基础数据存在性 |
| S10 | Contract + Payment | 合同 → 付款申请 → 发票 | construction.contract / payment.request / account.move | 关联完整性 |
| S20 | Settlement Clearing | 结算单 + 明细 + 收款关联 | sc.settlement.order(+line) / payment.request | 结算完整性 |
| S30 | Workflow Seed | 草稿待业务推进 | sc.settlement.order | 明细与收付款关联完整 |

## Scenario Dependency

- S00 为所有场景基础
- S10 依赖 S00（项目 / 往来单位）
- S20 依赖 S10（付款申请 / 合同）
- S30 基于 S20，但使用独立结算单

## S00 – Minimal Path

目标：
提供最短可跑的演示路径，覆盖项目、BOQ、材料与发票。

断言：
- 项目/BOQ/材料/发票数据存在

## S10 – Contract + Payment

目标：
演示合同、付款申请与发票的最小闭环（均保持 draft）。

关键记录：
- sc_demo_contract_out_010
- sc_demo_pay_req_010_001
- sc_demo_invoice_s10_001 / sc_demo_invoice_s10_002

断言：
- 合同/付款申请/发票记录存在

## S20 – Settlement Clearing

目标：
演示结算单、结算明细与收款关联的业务闭环。

关键记录：
- sc_demo_settlement_020_001
- sc_demo_settle_line_020_001 / sc_demo_settle_line_020_002
- sc_demo_payment_020_001

断言：
- 结算单/明细存在
- 结算单与收款关联存在

## S30 – Settlement Workflow Seed

目标：
演示一张条件完整、等待业务推进的草稿结算单。

关键记录：
- sc_demo_settlement_030_001（完整条件）

断言：
- 完整结算单：state = draft + 条件齐全

## Verification Model

所有场景均通过 make demo.verify 验证。

原则：
- 不调用 action_*
- 不依赖 UI 或审批流
- 仅使用 SQL 验证数据状态与约束

这保证了：
- CI 可用
- 回归可复现
- 演示稳定

## Versioning & Evolution

当前版本：Demo Platform v1 (S00–S30)

约定：
- 新场景必须新增 Sxx 编号
- 不修改已有场景语义
- 正式 Demo 不承载失败演练数据，失败路径由产品测试单独覆盖
