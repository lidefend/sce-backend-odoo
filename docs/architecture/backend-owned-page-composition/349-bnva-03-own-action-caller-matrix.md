# 349 · BNVA-03 Own Action Caller Matrix

17 个 smart_construction_core 无菜单动作，逐个核对：均仅在定义文件出现一次，无 button /
smart button / `ref=` / `env.ref` / JS action service 引用。最终分类全部为 ORPHAN_CANDIDATE。

| Action | Model | 业务领域 |
| --- | --- | --- |
| action_payment_request_counterparty_payment | payment.request | 付款（往来单位付款，疑似被 sc.payment.execution 版本取代） |
| action_project_budget_labor / machine / material / measure / subcontract / tax | project.budget | 项目预算分项 |
| action_sc_comprehensive_cost_summary | sc.comprehensive.cost.summary | 成本 |
| action_sc_hr_salary_payment | sc.hr.salary.payment | 人力 |
| action_sc_material_stock_summary | sc.material.stock.summary | 材料 |
| action_sc_p1_relationship_review_queue / suggestion | sc.p1.relationship.* | 关系治理 |
| action_sc_project_document_archive / quality / safety / self_inspection | sc.project.document | 项目资料 |
| action_sc_site_variation | sc.site.variation | 项目变更 |
