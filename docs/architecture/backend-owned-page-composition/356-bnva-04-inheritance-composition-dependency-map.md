# 356 · BNVA-04 Inheritance / Composition / Dependency Map

## smart_construction_core 模型分布

| 前缀 | 数量 | 归类 |
| --- | --- | --- |
| sc.* | 187 | INDUSTRY_OWNED_MODEL（行业工作流/汇总/计划，组合标准模型） |
| project.* | 41 | 项目域扩展/组合 |
| construction.* / tender.* / payment.* | 10 / 10 / 6 | 行业业务对象 |
| 其他 | 23 | 待细查 |

## 关系分类

- `_inherit`：260 处（MODEL_INHERITANCE）。
- `_inherits`：2 处（DELEGATION_INHERITANCE）。
- 大量 many2one/one2many（BUSINESS_COMPOSITION）。
- DIRECT_REUSE：project.project、purchase.order、stock.picking、account.move、product.product、res.partner、hr.employee 等被直接复用。
