# 251 · BNVA-02C-02B-01 · Section.fields 业务确认矩阵（13 条）

13 条 active title-only 均缺字段成员。字段成员只能依据原生视图事实与明确业务声明
提出候选，不得按字段名启发式自动确定。全部待产品负责人确认（NEEDS_BUSINESS_REVIEW）。

| external_id | model | 现有 section 标题（title-only） |
| --- | --- | --- |
| sc_financing_loan_form_sections_v1 | sc.financing.loan | 贷款信息/还款信息/贷款账户/银行/期限 |
| sc_tax_deduction_registration_form_sections_v1 | sc.tax.deduction.registration | 扣款/开票/预缴/抵扣/发票/材料 9 段 |
| sc_fund_account_operation_form_sections_v1 | sc.fund.account.operation | 详情/项目间借贷 |
| sc_material_purchase_request_form_sections_v1 | sc.material.purchase.request | 材料信息 |
| sc_material_inbound_form_sections_v1 | sc.material.inbound | 材料信息 |
| sc_labor_request_form_sections_v1 | sc.labor.request | 施工单位/合同信息/工种信息 |
| sc_labor_settlement_form_sections_v1 | sc.labor.settlement | 汇总信息/方单详情 |
| sc_subcontract_request_form_sections_v1 | sc.subcontract.request | 方单详情 |
| sc_subcontract_settlement_form_sections_v1 | sc.subcontract.settlement | 汇总信息/方单详情 |
| sc_equipment_request_form_sections_v1 | sc.equipment.request | 机械设备明细 |
| sc_equipment_settlement_form_sections_v1 | sc.equipment.settlement | 机械设备租赁清单/结算费用清单 |
| sc_material_rental_order_form_sections_v1 | sc.material.rental.order | 租赁材料清单 |
| sc_material_rental_settlement_form_sections_v1 | sc.material.rental.settlement | 结算材料租赁清单/结算费用清单 |

每段需确认：稳定 key、产品标题、字段成员、原生 Group 映射、slot、唯一 primary
owner。不因存在原生 Group 就认定业务 Section 完整。
