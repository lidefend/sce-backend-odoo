# 352 · BNVA-03 Navigation Asset Lifecycle

## 两个入口面

- Navigation Entry：Menu / Workspace / Route（用户主动进入）。
- Invocation Entry：Button / Context / Wizard / Server Action（流程内触发）。

两者共同使用 Odoo Action，职责不同：一个 Action 可以没有菜单，但必须有可解释的调用来源。

## 17 个 ORPHAN_CANDIDATE 处置建议（不自动执行）

- 付款往来单位（1）：疑似历史遗留，确认是否被 sc.payment.execution 版本取代。
- 项目预算分项（6）：疑似 smart button 目标未接线，确认是否需上下文入口。
- 项目资料分项（4）：疑似被统一资料入口取代，确认后登记为历史资产。
- 成本/人力/材料/关系/变更（6）：逐项确认是否正式产品能力或历史遗留。

不自动新增菜单，不自动删除，等待业务确认。
