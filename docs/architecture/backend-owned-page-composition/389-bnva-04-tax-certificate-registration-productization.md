# 389 · BNVA-04 Tax Certificate Registration Productization

## 业务事实

- Model：sc.tax.certificate.registration（外经证登记），`_inherit = mail.thread, mail.activity.mixin`，
  `_check_company_auto = True`，`_order = validity_start_date desc, id desc`。
- 原生视图：search / tree / form 完整（`view_sc_tax_certificate_registration_search`、
  `_tree`、`_form`）。
- Action：`action_sc_tax_certificate_registration_user`（外经证登记），显式绑定 tree+form+search，
  groups = project_read / finance_read / finance_user / finance_manager。
- Menu：`menu_sc_tax_certificate_registration_user`，父级 `menu_sc_invoice_tax_user_group`。
- 业务字段：name（单据编号，sequence）、company_id、project_id、taxpayer_name、taxpayer_identifier、
  tax_report_management_no、cross_region_business_address、validity_start_date / validity_end_date、
  prepaid_tax_date、tax_payment_certificate_no、state、handler_id、attachment_ids、note。
- 状态生命周期：draft → registered → completed，registered → cancelled。
- 业务方法：action_register（finance_user）、action_complete（finance_manager）、action_cancel
  （finance_user）；`write` 禁止直接改 `state`；`create` 强制 draft 起点 + 单据编号序列；
  validity 区间约束；`unique(company_id, tax_report_management_no)`。
- 权限：`ir.model.access.csv` 四条角色入口 + `sc_record_rules.xml` 五条记录规则。
- Vue 消费链：正式产品菜单策略 `formal_business_product_menu_policy_v1.json`、业务分类映射
  `business_category.py`、表单策略 `_tax_certificate_policy()`、`handling_entry_catalog.py`、
  `formal_entry_metadata_extensions.py`、`scoped_business_models.v1.json` 均已登记。

## 原生投影是否足够

足够。Action 已显式绑定 form/tree/search 并声明角色组；原生 arch 已表达登记身份、跨区域经营、
有效期、预缴税与完税凭证、附件、备注与状态条。无需新增 `ir.actions.act_window.view` 绑定，
也不重新声明 Identity / Section / FieldOwnership。

## 最小产品化

- 新增 productized contract：`tax_certificate_registration_productized_form_v1`，
  `composition_mode=native_semantic_surface`，`title=外经证登记`，source=product_release，published，
  priority=700（对齐兄弟 `tax_deduction_registration_productized_form_v1`）。

未复制 sc.quality.issue 的业务结构；仅复用同一契约机制，业务身份独立。

## 审计风险（记录，不在本批修）

原生 tree/form 引用 `source_created_by` / `source_created_at`，但 sc.tax.certificate.registration
未声明这两个字段（兄弟 sc.tax.deduction.registration 经 `sc.formal.display.copy.sources` 协议
并自带展示字段）。属模型层的存量原生视图字段解析风险，运行时渲染验证保持 NOT_RUN，待字段归属问题闭合。
