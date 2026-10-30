# PC-02 · 收入/支出双表单 P1/P2 静态质量报告

结论类型：STATIC_VERIFICATION。

## 1. 变更范围

仅修改 `addons/smart_construction_core/views/core/contract_views.xml` 中两个已发布入口：

- `view_construction_contract_income_form`（收入合同，construction.contract.income，action 680）
- `view_construction_contract_expense_form`（支出合同，construction.contract.expense，action 681）

未改模型、金额计算、ACL、record rule、审批逻辑；未新增 Vue 组件。

## 2. P1 身份带

两套表单统一：

- `subject` 合同名称（主标题，身份组首位）
- `name` 平台合同编号（只读）
- `document_status` 单据状态（只读，独立）
- `business_category_id` 业务分类
- `partner_id` 相对方 / `project_id` 关联项目
- `state` 生命周期 statusbar 保留；`validation_status` 独立保留（invisible）
- `type` 保持只读且不可见（方向由子模型固定 out/in，不重复展示）

## 3. P2 金额带

两套表单统一补充/标注：

- 原始金额：`amount_untaxed` / `amount_tax` / `amount_total`
- 合同变更：`amount_change`（新增，readonly；当前恒 0，表示“待接入”而非“无变更”）
- 最终合同价：`amount_final`（明确标签）
- 合同结算：`settlement_amount`（已结算）+ `settlement_balance`（新增，未结算）
- 资金履约：收入表单保留开票/收款；支出表单保留付款/历史承接

## 4. 静态验证结果

| 检查 | 结果 |
| --- | --- |
| XML 良构 | PASS |
| 两表单身份/金额字段齐全 | PASS（subject/name/document_status/business_category_id/partner_id/project_id/amount_change/amount_final/settlement_amount/settlement_balance/state/validation_status） |
| type 只读隐藏 | PASS |
| git diff --check | PASS |
| verify.contract.structure_lock | PASS（domains=14） |

## 5. 冻结边界

- 变更单 amount_delta 是否汇总到 amount_change：NOT_VERIFIED
- 结算金额是否允许超过最终合同价：NOT_VERIFIED
- 历史付款与新系统付款边界：NOT_VERIFIED

## 6. 待运行时验收

两套表单需在 candidate 环境分别完成四视口 + 真实字段值 + 履约表达验收；尚未执行，不标记 PASS。
