# 426 · BNVA-04 PR #790 Native Projection Differential

## native_view_projection.py

- PR #790：419 行；Feature：536 行。
- 两者类/函数一致：NativeFieldOccurrence、NativeContainer、NativeView、_structural_identity、
  _native_locator、project_native_view、derive_native_field_ownership、build_native_form_structure_contract。
- Feature 额外新增：_nearest_ancestor_ref、_relation_descriptor、business_home_ref、
  collect_business_containers。
- test_native_view_projection.py：PR #790 9 个测试方法，Feature 全部包含并新增 5 个
  （重复字段多分组、布局标签容器、native_attributes、relation_descriptor、内部属性不泄漏）。

## 分类

STRICT_EVOLUTION——Feature 完整继承并扩展 PR #790 能力，无丢失增量。
