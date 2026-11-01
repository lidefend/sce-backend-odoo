# 400 · BNVA-04 Tax Certificate Static Regression

## 原生事实验证

- ORM 模型：sc.tax.certificate.registration（tax_certificate_registration.py），state/方法/权限齐备。
- Form / Tree / Search：`view_sc_tax_certificate_registration_form` / `_tree` / `_search` 完整。
- 孤儿字段引用：NONE（04-06B 已删除 source_created_by / source_created_at）。
- 剩余 arch 字段：15/15 已声明（missing=NONE）。
- Action/View 绑定：`action_sc_tax_certificate_registration_user` 显式绑定 tree+form+search，
  groups = project_read / finance_read / finance_user / finance_manager。

## Contract 验证

- Productized Contract：`tax_certificate_registration_productized_form_v1`。
- composition_mode：native_semantic_surface。
- title：外经证登记；source：product_release；priority：700。
- identity_fields / sections / slots / fieldGroups / fieldOwnership / pageComposition：
  均未声明（结构权威交给原生 arch）。

## 结论

原生投影足够，稀疏契约只保留页面身份，不复制原生结构。静态回归 PASS。
