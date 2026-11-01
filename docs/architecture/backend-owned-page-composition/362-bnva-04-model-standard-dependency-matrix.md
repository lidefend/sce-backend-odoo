# 362 · BNVA-04 Model Standard Dependency Matrix

## 继承与组合

- `_inherit` 标准模型：project.project ×7、purchase.order ×2、account.move/line/tax、stock.picking/move、
  product.template、hr.job/department、res.partner.category/bank、mail.notification。
- `_inherits`：仅 2 处（委托继承少用）。
- 组合：187 个 sc.* 中 50 个为 menu+contract 的核心业务对象，通过 many2one/one2many 依赖标准模型。

## 结论

标准模型作为业务事实与生命周期权威，行业模型以继承 + 组合扩展，无标准模型的平行复制。
