# 198 · BNVA-02B-02C-01 · 运行时解析审计

## 链路

`ui.business.config.contract` → `_effective_view_orchestration_contracts` →
`form_structure_authority.resolve_form_structure_governance` → Adapters →
`unified_page_contract_v2_assembler`。

## 优先级（`view_orchestration_apply_order_key`）

`边界层 > action 特异 > view 特异 > role 特异 > priority > version_no > id`。

边界层整数值：generated_baseline=10 < industry_standard=20 < user_preference=30
< tenant_lowcoding=40；后应用者覆盖先应用者。

因此：代码种子（product_release → industry_standard=20）被用户低代码配置
（lowcode → tenant_lowcoding=40）覆盖。

## 结论

- 两种来源汇入同一模型：是。
- 作用域优先级正确：是（层 > 特异 > priority）。
- 同一作用域多条 active：可能存在，由 apply_order 解析，无去重强制。
- published / active / classification 在运行时被区分（只取 active+published）。

