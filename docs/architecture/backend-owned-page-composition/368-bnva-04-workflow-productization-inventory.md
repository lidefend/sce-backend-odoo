# 368 · BNVA-04 Workflow Productization Inventory

69 个“有菜单、无 Productized Contract”的 workflow 模型，按原生视图完整性细分：

| 视图完整性 | 数量 | 组成 |
| --- | --- | --- |
| form + tree + search | 50 | 核心业务 workflow（真正产品化候选） |
| form + tree（无 search） | 17 | 配置/字典/策略/技术对象（sc.dictionary、sc.capability、sc.product.policy、sc.workflow.def 等） |
| tree only | 2 | sc.workflow.log、sc.workflow.workitem（技术工作流日志） |

## 结论

69 个模型都不是“没有页面”——它们都有菜单和原生视图。没有 Contract 不等于没有页面，只是说明
自定义 Vue 前端尚未通过契约消费它们。产品化问题应聚焦 50 个核心 workflow 是否需要统一契约。
