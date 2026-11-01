# 179 · BNVA-02B-02A · 校验器实现

## 新增

- `addons/smart_core/core/business_structure_integrity.py`
  `validate_business_structure(payload, *, model_fields=None, native_groups=None)`。
- `scripts/verify/business_structure_integrity_shadow.py`：五样本 shadow 报告。
- `addons/smart_core/tests/test_business_structure_integrity.py`：11 项单测。

## Shadow 接入

`ui_business_config_contract._runtime_contract_validation` 返回体新增
`structure_diagnostics`（不影响 `valid`），发布阻断行为不变。

## 校验码

FORM_STRUCTURE_EMPTY / SECTION_MISSING / SECTION_KEY_MISSING /
SECTION_TITLE_MISSING / SECTION_FIELDS_EMPTY / SECTION_FIELD_INVALID /
FIELD_MULTIPLE_SECTION / IDENTITY_MISSING / IDENTITY_FIELD_INVALID /
IDENTITY_NOT_IN_SECTION / NATIVE_GROUP_UNRESOLVED / NATIVE_GROUP_UNVERIFIED。

