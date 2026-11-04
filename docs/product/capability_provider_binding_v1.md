# Capability Provider & Dependency Binding v1（CAP-01B · B3 + B4）

状态：候选映射，待架构复核

## 1. Provider Binding（B3）

| capability_key | Provider 类型 | Provider 引用 | 契约来源 |
|---|---|---|---|
| project.initiation.enter | odoo_intent + odoo_action + odoo_model | `project.initiation.enter` + `action_project_initiation` + `project.project` | 立项 form/list 契约 |
| project.list.open | odoo_action + odoo_model | `action_sc_project_list` + `project.project` | 项目列表契约 |
| project.lifecycle.transition | odoo_model + 生命周期 action | `project.project` | 生命周期流转规则 |
| construction.plan.manage | odoo_model + 计划 actions | `project.plan` 相关 | 计划管理契约 |
| construction.plan.report | odoo_action + odoo_model | 计划汇报 action | 计划汇报契约 |
| cost.budget.manage | odoo_model + 预算 actions | 预算模型 | 预算管理契约 |
| cost.boq.manage | odoo_model + BOQ actions | 工程量清单模型 | BOQ 契约 |
| cost.profit.compare | odoo_model + 对比计算 | 成本/收入模型 | 盈亏对比契约 |
| cost.progress.report | odoo_action + odoo_model | 进度填报 action | 进度填报契约 |
| contract.expense.track | odoo_model + 合同 actions | 支出合同模型 | 合同跟踪契约 |
| contract.income.track | odoo_model + 合同 actions | 收入合同模型 | 合同跟踪契约 |
| contract.settlement.audit | odoo_model + 结算 actions | 结算模型 | 结算审计契约 |
| equipment.plan.manage | odoo_model + 设备 actions | 设备模型 | 设备计划契约 |
| labor.plan.manage | odoo_model + 劳务 actions | 劳务模型 | 劳务计划契约 |
| governance.runtime.audit | odoo_model + 审计 actions | 治理模型 | 审计契约 |

> 未列出的 defer 项待核实 Provider 与契约；exclude 项不进入能力目录。

## 2. 组合能力依赖图（B4）

组合能力只依赖引用已发布原子能力，不复制实现：

```text
construction.plan.manage
  -> project.read
  -> plan.read / plan.update
  -> plan.report

cost.budget.manage
  -> project.read
  -> budget.read / budget.update
  -> cost.read

cost.boq.manage
  -> project.read
  -> boq.line.read / boq.line.write

cost.profit.compare
  -> project.read
  -> cost.read
  -> revenue.read
  -> compare.calc

equipment.plan.manage
  -> project.read
  -> equipment.read / equipment.update

labor.plan.manage
  -> project.read
  -> labor.read / labor.update
```

## 3. 组合能力判定原则（防过度设计）

“项目成本分析”是否应成为正式组合能力，必须同时满足：

1. 有独立契约（明确的输入输出，不只一次页面拼装）。
2. 有复用价值（被多个场景或产品引用）。
3. 有可验证产出（不是只把多个查询结果并排展示）。

若只在单一产品场景中按固定步骤编排、无独立复用与验证价值，则保持为工作场景编排，
不提升为 L2 组合能力。
