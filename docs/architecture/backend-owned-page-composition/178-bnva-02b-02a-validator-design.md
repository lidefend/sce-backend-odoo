# 178 · BNVA-02B-02A · 完整性校验器设计

## 设计原则

- 纯函数、无 Odoo 依赖，可离线单测。
- 复用现有校验词汇与入口（`_runtime_contract_validation`），不建立第四套体系。
- 三级诊断：ERROR / WARNING / NOT_VERIFIED；NOT_VERIFIED 不自动转 PASS。
- Shadow：只附加诊断，不改变现有发布阻断与运行时跳过行为。

## 校验对象

`views.form` 的：composition_mode、sections[]、identity_fields、native_group。

## 边界

- JSON Schema 合法性：现有 schema guard。
- 配置结构完整性：本校验器。
- 发布准入：02B-02B 接入，本轮不阻断。
- 运行时消费有效性：`_runtime_contract_validation` 既有 reasons。

