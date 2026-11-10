# Capability Provider & Dependency Binding v1（CAP-01B · B3 + B4）

状态：候选映射，待架构复核

## 1. Provider Binding（B3）

| capability_key | Provider 类型 | Provider 引用 | 契约来源 |
|---|---|---|---|
| project.initiation.create | odoo_intent + odoo_action + odoo_model | `project.initiation.enter` + `action_project_initiation` + `project.project` | 立项 form/list 契约；旧 key 为兼容别名 |
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

组合能力只依赖引用候选目录中已存在的原子能力，不复制实现。模型内部读写
（project.read / budget.read / boq.line.read / compare.calc 等）是 Provider 内部操作，
不单独发布，也不作为依赖引用：

```text
construction.plan.manage
  -> project.list.open          # 项目读取（查询能力）
  -> construction.plan.report   # 计划汇报

cost.budget.manage
  -> project.list.open

cost.boq.manage
  -> project.list.open

cost.profit.compare
  -> project.list.open

equipment.plan.manage
  -> project.list.open

labor.plan.manage
  -> project.list.open
```

## 3. 组合能力判定原则（防过度设计）

“项目成本分析”是否应成为正式组合能力，必须同时满足：

1. 有独立契约（明确的输入输出，不只一次页面拼装）。
2. 有复用价值（被多个场景或产品引用）。
3. 有可验证产出（不是只把多个查询结果并排展示）。

若只在单一产品场景中按固定步骤编排、无独立复用与验证价值，则保持为工作场景编排，
不提升为 L2 组合能力。

## 4. 引用闭合 vs 资格闭合

| 检查 | 含义 | 现状 |
|---|---|---|
| Reference Closure | 组合能力依赖的每个 key 都能在候选目录中找到 | CAP-01B 已验证通过 |
| Qualification Closure | 所有依赖均具备允许的发布资格 | 推迟到 CAP-01C |

本阶段只能证明依赖身份引用闭合，不能证明组合能力已具备发布条件。组合能力
不得因为依赖 key 能找到，就被误认为可发布；资格闭合必须等 CAP-01C 逐项评估。

## 5. Identity Boundary（BE-U03）

能力与入口使用同一份投影时，也必须保留不同身份：

| 身份 | 维护权威 | 允许表达 | 不得表达 |
| --- | --- | --- | --- |
| `business_capability` | `smart_construction_core.services.capability_registry` | 稳定能力键、Provider、角色/组要求、能力状态、资格引用 | 从菜单存在性推导能力资格 |
| `entry_compatibility_alias` | 原生菜单/动作或场景入口的产品策略投影 | `construction.menu.*`、`catalog.menu.*`、目标页面、发布阶段和入口展示 | 独立业务能力、Provider 完成度、执行授权 |

`construction.menu.*` 与 `catalog.menu.*` 键继续兼容现有发布产物，但不得进入业务能力
registry。菜单别名携带 `business_capability=false`，`qualification_authority` 指向有效
产品发布，而不是菜单本身。最终数据库目录收敛与旧键迁移是后续独立工作，不能把本节的
身份标注解释为迁移已经完成。
