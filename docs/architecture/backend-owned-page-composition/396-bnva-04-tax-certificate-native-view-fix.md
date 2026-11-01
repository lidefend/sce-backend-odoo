# 396 · BNVA-04 Tax Certificate Native View Fix

## 修复目标

sc.tax.certificate.registration 原生视图删除两个不存在的字段引用
（依据 393～395 的 VIEW_DECLARATION_CORRECTION 裁定）。

## 改动范围

仅 `addons/smart_construction_core/views/core/tax_certificate_registration_views.xml`。

- Tree：删除 `source_created_by`、`source_created_at` 两个 `optional="hide"` 列。
- Form：删除整个「录入来源」group（组内仅含上述两个孤儿字段，无其他有效业务字段）。

不新增替代字段，不修改业务模型，不留下空 Group，不引入虚假来源信息。

## 未修改

- Python 模型及计算字段。
- `sc.formal.display.copy.sources` 协议与 `FORMAL_DISPLAY_COPY_SOURCES`。
- Productized Contract（quality / tax 两个契约文件）。
- 公开 V2 Schema。
- NativeView Projection / Renderer。
- ACL / Record Rules。
- 其他财务模型（含 sc.tax.deduction.registration）。

## 兄弟模型风险登记（本轮不修改）

sc.tax.deduction.registration 的「迁移来源」页仍引用未声明的裸 `source_created_by` /
`source_created_at`。该模型已有 `creator_name` / `created_time`，展示副本应为
`deduction_bill_source_created_by` / `deduction_bill_source_created_at`。属同类缺陷，
需单独核对登记协议与实际消费者后另行安排，本轮仅登记。
