# 261 · BNVA-02C-02B-03 · sc.payment.execution 业务身份与 Section 矩阵

## Identity 字段定义证据

- `name = fields.Char(string="单据号")` → 本对象单号。
- `document_no = fields.Char(string="来源单号")` → 来源单据号，非本对象身份。

结论：Identity Summary 建议 **`['name']`**，不纳入 `document_no`（来源引用）。

## 9 个原生 Group → 产品 Section 候选（含完整字段成员）

| 原生 Group | 字段成员 |
| --- | --- |
| payment_main 办理类型 | business_category_id / execution_flow_label / name |
| payment_basis 付款依据 | payment_request_id / project_id / operation_strategy / partner_id / payment_request_partner_id / actual_payee_partner_id / payment_request_partner_relation / contract_id |
| payment_amount 付款金额 | date_payment / paid_amount / planned_amount / invoice_amount / currency_id |
| payment_note 办理说明 | payment_method / handler_name / document_no / note / cancellation_kind / reversal_reason |
| receipt_account 收款账户 | receipt_account_name / receipt_bank_name / receipt_account_no |
| payment_account 付款账户 | payment_account_name / payment_bank_name / payment_account_no / bank_account |
| payment_attachment 附件 | attachment_ids |
| payment_responsibility 资金责任 | company_contractor_responsibility_summary_id / state / arrival_unprocessed_amount / arrival_over_processed_amount / self_funding_balance |
| payment_source_trace 来源追溯 | payment_family / source_kind / push_result / kingdee_document_no / creator_name / created_time / active |

无 notebook；关系字段（payment_request_id/project_id/partner_id/contract_id）不入 Identity。

