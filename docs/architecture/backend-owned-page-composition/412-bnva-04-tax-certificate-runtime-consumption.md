# 412 · BNVA-04 Tax Certificate Runtime Consumption

## L2 Contract（实测）

- 契约 `tax_certificate_registration_productized_form_v1` 已 published：
  model=sc.tax.certificate.registration，view_type=form，priority=700，active=true。
- composition_mode=native_semantic_surface；title=外经证登记；source_status=product_release；
  workflow_authority=null（对齐 tax 兄弟口径）。

## 孤儿字段（实测）

- sc.tax.certificate.registration.form 已加载；arch 中：
  `source_created_by=false`、`source_created_at=false`。
- 字段解析不再因孤儿字段报错（04-06B 修正已在运行时生效）。

## L3 / L4

- L3 Vue Renderer：前端正常服务，完整浏览器 DOM NOT_RUN。
- L4 业务交互：无业务记录，保存/重新进入/状态 NOT_RUN。

## 结论

税务凭证契约已真实加载，孤儿字段已彻底消失；L1/L2 PASS，L3/L4 NOT_RUN。
