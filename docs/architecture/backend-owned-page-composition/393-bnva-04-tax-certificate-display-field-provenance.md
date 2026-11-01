# 393 · BNVA-04 Tax Certificate Display Field Provenance

## 被审计对象

sc.tax.certificate.registration 原生视图中的两个展示字段引用：

- tree：`<field name="source_created_by" string="录入人" optional="hide"/>`、
  `<field name="source_created_at" string="录入时间" optional="hide"/>`。
- form：「录入来源」group 内 `<field name="source_created_by" string="录入人" readonly="1"/>`、
  `<field name="source_created_at" string="录入时间" readonly="1"/>`。

## 模型侧事实

- sc.tax.certificate.registration 模型未声明 `source_created_by` / `source_created_at`。
- 模型未声明其常见规范来源 `creator_name` / `created_time`。
- 模型没有 `source_origin` / `legacy_source_model` / `legacy_source_table` /
  `legacy_record_id` / `legacy_document_state` 等迁移来源概念。
- 模型 `_inherit = ["mail.thread", "mail.activity.mixin"]`，未继承任何提供这些字段的 Mixin。

## 全仓库字段声明事实

`source_created_by` / `source_created_at` 是逐模型声明的计算存储展示字段，仅在 4 个模型上
以裸名声明：

- payment.request（payment_request.py）
- sc.invoice.registration（invoice_registration.py）
- sc.self.funding.registration（self_funding_registration.py）
- sc.material.acceptance（material_acceptance.py）

不存在任何公共 Mixin / AbstractModel 声明这两个字段。

## 与展示协议的关系

`sc.formal.display.copy.sources` 只是登记「展示副本字段 → 规范来源字段」的排除协议，
不提供字段。其中只有 sc.invoice.registration 把 `source_created_by → creator_name`、
`source_created_at → created_time` 登记为展示副本；tax 两个模型均未登记 `source_created_*`。

## 结论

sc.tax.certificate.registration 的 `source_created_by` / `source_created_at` 是孤儿字段引用：
既不是共享协议提供的虚拟字段，也不是本模型声明的字段，更无规范来源。证据指向
`VIEW_DECLARATION_CORRECTION`（详见 395）。
