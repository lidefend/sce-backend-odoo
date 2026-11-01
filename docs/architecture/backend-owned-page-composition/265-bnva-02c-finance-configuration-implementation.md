# 265 · BNVA-02C-02C · 财务页面配置实施

## 结果

- payment.request：`identity_fields=['name']` + 7 个 section key，零诊断（第二样板）。
- sc.payment.execution：新建主 action 配置
  `sc_payment_execution_productized_form_v1`（`action_sc_payment_execution`），
  `native_semantic_surface` + `identity_fields=['name']`。
- sc.receipt.income：`receipt_income_productized_form_v1` 增加
  `identity_fields=['name']`（`action_sc_receipt_income`）。

## 结构来源

execution / receipt 保持 `native_semantic_surface`：原生 form view 拥有 9/7 个命名
Group 及 receipt 的 notebook（责任余额/台账），配置只声明入口 title + Identity，
不重复声明原生 arch 字段（避免再次复制原生结构）。

## 验证

两配置 `validate_business_structure` diagnostics=[]；XML 可解析；`git diff --check`
通过。document_no 保留来源追溯语义，未纳入 Identity。未恢复 6 条 retired。

