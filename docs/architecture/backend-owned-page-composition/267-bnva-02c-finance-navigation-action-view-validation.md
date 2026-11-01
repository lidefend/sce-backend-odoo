# 267 · BNVA-02C-02D · 财务导航链验证

静态追踪（XML）通过：

- payment.request：`menu_payment_request_receive` → `action_payment_request_receive`
  → model payment.request。
- sc.payment.execution：`menu_sc_payment_execution` → `action_sc_payment_execution`
  → model sc.payment.execution。
- sc.receipt.income：`menu_sc_receipt_income` → `action_sc_receipt_income`
  → model sc.receipt.income。

运行时可见性/服务端授权分离验证未执行（not_run）。

