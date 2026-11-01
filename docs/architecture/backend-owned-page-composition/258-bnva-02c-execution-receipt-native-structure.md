# 258 · BNVA-02C-02B-02 · execution / receipt 原生结构审计

## 结论

两者原生 form view 已具备命名 group + 字段，无需恢复 retired title-only 配置。

## sc.payment.execution（view_sc_payment_execution_form）

命名 group：办理类型(payment_main) / 付款依据(payment_basis) / 付款金额
(payment_amount) / 办理说明(payment_note) / 收款账户(receipt_account) /
付款账户(payment_account) / 附件(payment_attachment) / 公司-承包人资金责任
(payment_responsibility) / 来源与系统追溯(payment_source_trace)。

Identity 候选：`name`（办理类型组）、`document_no`（办理说明组）。

## sc.receipt.income（view_sc_receipt_income_form）

命名 group：办理主信息(receipt_main) / 项目与合同(receipt_project) / 收款事项
(receipt_income_items) / 收款账户(receipt_account) / 金额与抵扣(receipt_amount) /
说明与附件(receipt_note_attachment) / 来源追溯(receipt_source_trace)，加 notebook
(责任余额 / 台账)。

Identity 候选：`name`、`document_no`（办理主信息组）。

## 重建方向

两个页面均可采用 `native_semantic_surface`（委托原生 group）+ 显式
`identity_fields`，或 `entry_semantic_surface` 显式映射原生 group。不与
payment.request 共享同一份结构定义；收款与付款执行可共享规范、不共享结构。

