# 159 · BNVA-019 Stage 3C-03C-02B · 兼容回归

## 通过

- `python3 -m py_compile`（变更文件）与 `git diff --check`。
- `verify.unified_page_contract.v2.assembler`。
- `verify.unified_page_contract.v2.runtime`（23 + 135）。
- `test_form_structure_field_ownership`（3）。
- `test_ui_contract_v2_boundaries`（160）。
- `test_unified_page_contract_v2_mobile_compact`（135）。
- `verify.node_component_validation.unit`（160 + 48 + cache）。
- `verify.contract.entry_equivalence.guard`（10）。
- `verify.business_config.formal_list.unit`。
- `make ci.local.iteration`（L1，dirty scope）。
- `make ci.local.quick`（HEAD `12f0e53363fa4d6a44719a4a01ed8113344c7f57`，签发回执）。

## 既有失败（排除，非本轮引入）

- `verify.form_structure_authority_unification.unit`：
  `test_uc1_contract_native_declarations_and_semantic_opt_in` 校验 P1 原生 XML
  `contract_views.xml` 首组标题（期望 `身份与基本资料`，实际 `合同身份`），与本轮
  P0 ownership fallback 无关；相关文件均不在改动集。

## 缓存 pin

- `ASSEMBLED_CONTRACT_CACHE_VERSION`：
  `ui-contract-v2-native-persisted-relation-dependencies-v25-legacy-fallback-retirement`
- `ASSEMBLED_CACHE_INPUTS_SHA256`：
  `12b56f924df9f33f0e07ea8d7ec95966bbb4051dfd16ff7f8881b2b4e61a0650`

