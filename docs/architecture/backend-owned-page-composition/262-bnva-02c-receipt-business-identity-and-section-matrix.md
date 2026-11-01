# 262 · BNVA-02C-02B-03 · sc.receipt.income 业务身份与 Section 矩阵

## Identity 字段定义证据

- `name = fields.Char(string="单据号")` → 本对象单号。
- `document_no = fields.Char(string="来源单号")` → 来源单据号。

结论：Identity Summary 建议 **`['name']`**，不纳入 `document_no`。

## 7 个原生 Group + notebook

| 原生 Group | 字段成员 |
| --- | --- |
| receipt_main 办理主信息 | name / receipt_flow_label / source_origin / source_kind / business_category_id / date_receipt / document_no |
| receipt_project 项目与合同 | project_id / legacy_project_name / company_id / operation_strategy / partner_id / contract_id / payment_request_id 等 |
| receipt_income_items 收款事项 | receipt_type / income_category / payment_method / bill_no / invoice_ref 等 |
| receipt_account 收款账户 | receiving_account / receiving_account_name / receiving_account_no / receiving_bank_name |
| receipt_amount 金额与抵扣 | amount / deducted_invoice_amount / deducted_tax_amount / settlement_amount / currency_id |
| receipt_note_attachment 说明与附件 | note / attachment_ids / reject_reason |
| receipt_source_trace 来源追溯 | legacy_source_model / legacy_record_id / creator_name / created_time / active 等 |
| notebook 责任余额 | company_contractor_responsibility_* 5 字段 |
| notebook 台账 | treasury_ledger_id |

notebook（责任余额/台账）是独立布局层级（只读业务区域/关联数据视图），不压平为普通
Section；需在 02B-02 明确其表现为只读区域还是独立子视图。

