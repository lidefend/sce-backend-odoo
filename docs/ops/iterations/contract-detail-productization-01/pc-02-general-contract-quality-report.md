# PC-02 · 综合合同 P1/P2 静态质量报告

结论类型：STATIC_VERIFICATION。

## 1. 变更范围

仅修改 `addons/smart_construction_core/views/core/general_contract_views.xml` 的
`view_sc_general_contract_form`（sc.general.contract，权威入口 action_sc_general_contract）。
未改模型计算、ACL、record rule、审批逻辑；未新增 Vue；未改权威导航。

## 2. P1 身份带

- `contract_name` 合同名称（主标题）
- `contract_no` 合同编号（只读）
- `contract_direction` 合同方向（income/expense）
- `contract_type` 合同类型
- `name` 登记单号（只读辅助）
- `project_id` 关联项目
- `state` 生命周期 statusbar 保留；`validation_status` 独立保留（invisible）
- `partner_id` 往来单位（合同方区）

不再引用 `subject`/`document_status`/`business_category_id`/`type`。

## 3. P2 五层金额带

- 原始合同金额：`amount_untaxed` + `tax_id`/`tax_rate` + `amount_total`（标注为含税/最终执行金额，避免误认为两个独立金额）
- 合同变更：`change_amount_total` + `change_rate`
- 最终合同价：`amount_total`
- 合同结算：`settlement_amount`
- 资金履约：`invoice/received`（income）、`paid`（expense），按 `contract_direction` 适配

不新增/伪造 `amount_final`、`settlement_balance`、`amount_tax`。

## 4. 静态验证结果

| 检查 | 结果 |
| --- | --- |
| XML 良构 | PASS |
| 原字段完整 | PASS（无缺失，arch 内无重复） |
| git diff --check | PASS |
| verify.contract.structure_lock | PASS（domains=14） |

## 5. 冻结边界

- 变更单是否汇总到最终合同价：NOT_VERIFIED
- 结算金额是否允许超过最终合同价：NOT_VERIFIED
- 历史付款与新系统付款边界：NOT_VERIFIED

## 6. 待运行时验收

需在 candidate 环境按权威 Action 完成视图加载 + 四视口 + 真实字段值 + 履约方向验收；尚未执行。
