# Demo 数据重建执行计划（2026-10-27）

状态：重建受管工具已确认，B1 缺口的业务链依赖已梳理；本计划是下一轮执行输入，本轮不直接灌数据。

## 工具与入口

- 受管写入工具：`scripts/verify/daily_demo_walkthrough_ui.mjs`，经 `make daily.demo.walkthrough.ui` 入口，要求 `SC_DEMO_WALK_CONFIRM` 与计划文件。
- 支持模型：`sc.labor.worker`、`tender.opportunity`、`sc.material.supplier.return`、`sc.hr.salary.payment`、`payment.request`、`sc.invoice.registration`。
- 其他模型走官方业务入口前台办理，同样绑定写前恢复、回读与精确清理，不直接写终态。

## B1 缺口依赖与执行顺序

| 缺口 | 模型 / 入口 | 前置依赖 | 重建动作 |
| --- | --- | --- | --- |
| DD-06 劳务实名 | `sc.labor.worker` menu 688 | 项目、班组已存在 | 多状态名册（在场/退场）经工具或前台 |
| DD-08 材料退货 | `sc.material.supplier.return` | 材料入库单、供应商、库位 | 先补入库，再关联退货 |
| DD-09 薪资发放 | `sc.hr.salary.payment` menu 696 | 薪资核算单、人员、期间、资金账户 | 先核算单，再发放并回读金额 |
| DD-18 税务链 | `sc.invoice.registration` 等 | 合同/项目事实 | 外经证→预缴→开票→申报串联，不跳步骤 |
| DD-04 质量验收 | `sc.quality.acceptance` | 项目、质量责任人 | 待验收/已完成双状态 |
| DD-05 签证 | `sc.site.variation` menu 687/694 | 项目、合同、成本项 | 一般签证与分包签证分开 |
| DD-14 合同变更 | `sc.contract.change` menu 662 | 已签署合同 | 变更前后金额与审批一致 |
| DD-15 结算衔接 | `sc.settlement.order` menu 698 | 已签署日常合同 | 来源、期间、金额与资金回读 |
| DD-16 费用办理 | `sc.expense.claim` menu 578/563/575 | 项目、费用科目、责任人 | 报销/扣款/备用金分别建立 |
| DD-19 进度款 | `sc.receipt.income` menu 545 | 进度/合同/结算依据 | 项目、付款方、金额与台账衔接 |
| DD-01/DD-21 经营与报表 | 汇总机制 | 上述明细事实 | 明细触发正式汇总后对账，不灌报表行 |

## 执行纪律

- 每项按“备份 → 正式动作 → 独立回读 → 精确清理/保留台账”执行。
- 先补依赖，再补主记录；先 B1 后 B2/B3；禁止直接改状态或把汇总表当种子。
- 保留既有走查记录边界，不重放已完成的成功动作。

## 尚未闭环

完整 90 项矩阵、130 个新建点击、移动端与业务写入链重跑，在数据重建按本计划推进后，在冻结部署上一次性完成。
