# 357 · BNVA-04 Parallel Model & Duplicate Capability Audit

## 结论

未发现 sc.partner / sc.product / sc.employee / sc.purchase.order / sc.stock / sc.account / sc.company /
sc.user 等平行模型。sc.* 模型是行业工作流、汇总、计划或策略对象，通过组合依赖标准模型：

- sc.invoice.registration / sc.output.invoice.ledger / sc.invoice.category.summary → 组合 account.move。
- sc.material.stock.summary → 组合 stock。
- sc.partner.business.fact.line → 组合 res.partner。
- sc.product.policy / system.settings → 组合 product。
- sc.receipt.invoice.line → 组合发票行。

深度逐模型平行性复核（187 个 sc.* 的逐项比对）转入 04-02，本轮不做臆断。
