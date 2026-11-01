# 246 · BNVA-02C-02A-R · 19 条 form_sections_v1 归属矩阵

## 结论

19 条全部 `source=product_release`、title-only（section 无 fields）。分为：

- **13 条 active → PRODUCT_CORE**（缺 Section.fields，属产品完整性缺口）：
  sc.financing.loan / sc.tax.deduction.registration / sc.fund.account.operation /
  sc.material.purchase.request / sc.material.inbound / sc.labor.request /
  sc.labor.settlement / sc.subcontract.request / sc.subcontract.settlement /
  sc.equipment.request / sc.equipment.settlement / sc.material.rental.order /
  sc.material.rental.settlement。均存在 action+view（多数有 menu）。
- **6 条 active=False → RETIRED**：sc.payment.execution / sc.receipt.income /
  sc.invoice.registration / sc.labor.usage / sc.subcontract.register /
  sc.equipment.usage。

无 TENANT_CUSTOMIZATION；title-only 不是低代码定制，而是产品默认模板未补字段。

