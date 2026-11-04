# Capability Reconciliation Matrix v1（CAP-01B · B2）

状态：候选分类，待架构复核
方法：按 B0 五条件 + B1 六类操作，对 42 + 63 候选逐项分类；131 条产品菜单入口整体排除。

## 1. 分类方法

- 动词为真实业务操作（create/manage/enter/advance/track/audit/compare/report/transition）→ 候选能力。
- 动词为页面/导航（open/list/form/board/matrix/dashboard/focus/watch）→ 页面入口，排除或暂缓。
- “list” 需核实是独立查询功能还是仅打开列表页 → 暂缓。

## 2. 分类表（63 项）

| capability_key | 分类 | 说明 |
|---|---|---|
| project.initiation.enter | keep（rename → project.initiation.create） | 项目创建，有真实 intent handler；旧 key 保留为兼容别名 |
| project.list.open | defer | 需核实是查询能力还是打开列表页 |
| project.lifecycle.transition | keep | 生命周期流转，真实动作 |
| project.lifecycle.open | exclude | 打开生命周期视图（页面） |
| project.dashboard.enter | defer | 进入驾驶舱，需核实独立功能语义 |
| project.dashboard.open | exclude | 打开驾驶舱（页面） |
| project.board.open | exclude | 打开看板（页面） |
| project.task.list | exclude | 任务列表（页面） |
| project.task.board | exclude | 任务看板（页面） |
| project.document.open | exclude | 打开文档（页面） |
| project.weekly_report.open | exclude | 打开周报（页面） |
| project.risk.list | defer | 风险清单，需核实查询语义 |
| project.structure.manage | defer | 执行结构/WBS，需补契约 |
| project.plan_bootstrap.enter | defer | 计划引导，需核实 |
| project.execution.enter | defer | 进入执行，需核实 |
| project.execution.advance | defer | 执行推进，可能为原子动作 |
| construction.plan.manage | keep(composite) | 计划管理组合 |
| construction.plan.report | keep | 计划汇报，真实提交动作 |
| construction.diary.open | defer | 施工日志，需核实是填写还是打开 |
| cost.budget.manage | keep(composite) | 预算管理组合 |
| cost.boq.manage | keep(composite) | 工程量清单管理组合 |
| cost.ledger.open | exclude | 打开成本台账（页面） |
| cost.profit.compare | keep(composite) | 盈亏对比，有可验证产出 |
| cost.progress.report | keep | 进度填报，真实提交动作 |
| contract.center.open | exclude | 打开合同中心（页面） |
| contract.expense.track | keep | 支出合同跟踪 |
| contract.income.track | keep | 收入合同跟踪 |
| contract.settlement.audit | keep | 结算审计 |
| equipment.plan.manage | keep(composite) | 设备计划管理 |
| equipment.request.list | defer | 需核实查询 vs 列表页 |
| equipment.settlement.list | defer | 同上 |
| equipment.usage.list | defer | 同上 |
| labor.plan.manage | keep(composite) | 劳务计划管理 |
| labor.attendance.list | defer | 需核实 |
| labor.request.list | defer | 需核实 |
| labor.settlement.list | defer | 需核实 |
| quality.issue.list | defer | 需核实查询语义 |
| quality.recheck.list | defer | 需核实 |
| quality.rectification.list | defer | 需核实 |
| safety.issue.list | defer | 需核实 |
| safety.recheck.list | defer | 需核实 |
| safety.rectification.list | defer | 需核实 |
| material.catalog.open | exclude | 打开材料档案（页面） |
| material.procurement.list | defer | 需核实 |
| finance.approval.center | exclude | 审批中心（页面） |
| finance.exception.monitor | defer | 异常监控，可能为监控能力 |
| finance.invoice.list | exclude | 发票列表（页面） |
| finance.ledger.payment | exclude | 付款台账（页面） |
| finance.ledger.treasury | exclude | 资金台账（页面） |
| finance.metrics.operating | exclude | 经营指标（页面） |
| finance.payment_request.form | exclude | 付款申请表单（页面） |
| finance.payment_request.list | exclude | 付款申请列表（页面） |
| finance.plan.funding | defer | 资金计划，需核实 |
| finance.settlement.order | defer | 结算单，需核实 |
| analytics.dashboard.executive | exclude | 经营驾驶舱（页面） |
| analytics.exception.list | exclude | 异常列表（页面） |
| analytics.lifecycle.monitor | defer | 生命周期监控，可能为监控能力 |
| analytics.project.focus | exclude | 项目聚焦（页面） |
| governance.capability.matrix | exclude | 能力矩阵（页面） |
| governance.runtime.audit | exclude | 运行态审计（无真实执行载体，平台机制/导航投影） |
| governance.scene.openability | defer | 场景可开性治理，需核实 |
| workspace.project.watch | exclude | 项目关注（工作台页面） |
| workspace.today.focus | exclude | 今日焦点（工作台页面） |

## 3. 统计

- keep（原子/组合候选）：13
- defer（待核实）：26
- exclude（页面/入口）：24
- 合计 63

B6 候选目录与此表一一对应（39 条 = 13 keep + 26 defer），exclude 24 条不进入候选目录。

最终正式能力数量以 CAP-01C 真实证据评估为准，不预设 63。
