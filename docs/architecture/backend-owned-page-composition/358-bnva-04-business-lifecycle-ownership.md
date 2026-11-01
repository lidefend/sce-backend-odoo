# 358 · BNVA-04 Business Lifecycle Ownership

## 原则

- 标准模型负责标准业务身份与生命周期（project.project、account.move、purchase.order、
  stock.picking、product.product、res.partner、hr.employee）。
- 行业模型负责行业业务流程、专业字段与产品默认配置，不重复拥有标准生命周期。

## 17 个孤立候选

这些动作多绑定 industry-owned 模型（project.budget、sc.project.document、sc.site.variation、
sc.p1.relationship.* 等），本身不与标准模型冲突；其生命周期归属在 04-02 结合业务评审。
