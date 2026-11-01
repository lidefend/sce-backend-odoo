# 394 · BNVA-04 Display Copy Protocol Consumer Audit

## 协议定义

- `sc.formal.display.copy.sources` 是 AbstractModel，只提供 `_display_copy_source_fields()`，
  返回 `FORMAL_DISPLAY_COPY_SOURCES.get(self._name, {})`。它不声明任何业务字段。
- `FORMAL_DISPLAY_COPY_SOURCES` 是展示副本登记表：`{展示副本字段: 规范来源字段}`。
  登记的副本由共享编排层从表单 body 并集中排除，避免同一业务事实在同一上下文呈现两次。

## 登记表内容

| 模型 | 登记副本 → 规范来源 |
| --- | --- |
| sc.invoice.registration | note_display→note、invoice_attachment_text→attachment_ids、source_created_by→creator_name、source_created_at→created_time |
| payment.request | payment_request_attachment_text_display→attachment_ids |
| sc.material.inbound | material_inbound_attachment_text_display→attachment_ids |
| sc.tax.deduction.registration | deduction_bill_attachment_text→attachment_ids |

仅 sc.invoice.registration 登记了 `source_created_by` / `source_created_at`（规范来源
`creator_name` / `created_time`）。

## 协议消费者

- 生产唯一消费者：`smart_core/core/view_orchestrator.py` 的 `_display_copy_field_names()`，
  经 `_display_copy_source_fields()` 读取登记表，把已登记副本排除出表单并集。
- 协议不解析字段归属、不声明字段、不猜测副本（`test_unregistered_same_shape_projection_is_not_excluded`
  证明共享层只认声明，不按模型名或字段后缀猜测）。
- 契约侧不投影这些字段；`native_semantic_surface` 稀疏契约把结构权威交给原生 arch，
  字段列表为空，`source_created_*` 不出现在契约里。

## 测试消费者

- `test_form_structure_consumption.py`：登记副本有共存规范来源、副本值等于规范来源投影、
  登记副本不入表单并集、未登记同形投影不受影响。
- `test_receipt_income_native_lowcode.py`：sc.receipt.income 未接入协议的反例。

## 关键判定

`sc.formal.display.copy.sources` 是「排除」协议，不是「字段提供」协议。它不能为
sc.tax.certificate.registration 提供 `source_created_by` / `source_created_at`。
