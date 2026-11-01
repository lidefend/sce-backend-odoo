# 250 · BNVA-02C-02B-01 · Identity 业务确认矩阵（46 条 → 26 个模型）

## 判定口径

不按字段名/类型/顺序自动定 Identity；本矩阵只给字段池与置信等级，全部待产品
负责人确认。等级：A 已有明确事实；B 充分证据；C 证据不足。

## 通用观察（不据此自动赋值）

46 条配置的 section 首段几乎都以 `state` 开头，并含 `validation_status`、
`can_review`、`name`、`document_no` 等。`state/validation_status/can_review` 属
状态/技术字段，不是对象身份；`name` / `*_no` 是对象标识候选，仍需业务确认。
`partner_id/project_id/contract_id/requester_id/department_id/company_id` 属业务
关系或技术归属，不自动认定为 Identity。

## 矩阵（26 个 distinct 模型；每模型多条 action/view 记录共用一次业务决策）

| model | 字段数 | 首段字段池（候选，待确认） | 等级 |
| --- | --- | --- | --- |
| sc.document.admin.document | 38 | name / document_no / fact_type | C |
| sc.equipment.request | 32 | name / *_document_no_display | C |
| sc.equipment.settlement | 27 | name / *_document_status_display | C |
| sc.expense.claim | 46 | name / claim_type / direction / document_no | C |
| sc.financing.loan | 54 | name / loan_type / direction / document_no | C |
| sc.labor.plan | 17 | name | C |
| sc.equipment.plan | 18 | name | C |
| sc.attendance.checkin | 18 | name | C |
| sc.labor.request | 31 | name / *_document_no_display | C |
| sc.labor.settlement | 28 | name / *_document_no_display | C |
| sc.office.admin.document | 32 | name / document_no / fact_type | C |
| payment.request | 41 | name / type / date_request | C |
| purchase.order | 56 | name / partner_ref | C |
| sc.treasury.reconciliation | 32 | name / document_no / source_kind | C |
| sc.subcontract.plan | 20 | name | C |
| project.material.plan | 32 | name / date_plan | C |
| construction.contract | 20 | name / subject | C |
| sc.material.outbound | 21 | name / outbound_type | C |
| sc.material.rfq | 16 | name / rfq_date | C |
| sc.self.funding.registration | 20 | name / funding_type | C |
| sc.material.inbound | 20 | name / inbound_date | C |
| sc.fund.account.operation | 19 | name / operation_type | C |
| sc.settlement.adjustment | 28 | name / adjustment_type | C |
| sc.settlement.order | 63 | name / settlement_type / document_date | C |
| sc.subcontract.settlement | 31 | name / *_document_no_display | C |
| sc.subcontract.request | 15 | name | C |

结论：26 个模型全部等级 C（NEEDS_BUSINESS_REVIEW），需产品负责人逐模型确认对象
标识组合；执行器不写入 `identity_fields`。
