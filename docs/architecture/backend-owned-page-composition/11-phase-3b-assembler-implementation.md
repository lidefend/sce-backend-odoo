# 11 · Phase 3B Assembler Implementation Report

## Status

READY_WITH_CONSTRAINTS

## Changes

- `unified_page_contract_v2_assembler.py`：
  - 新增 `_page_composition_field_codes`。
  - 新增 `_page_composition_contract`。
  - 在 `ui.contract` / `native_form_projection` 组装后调用。
  - 输出 `contract["fieldOwnership"]` 与 `contract["pageComposition"]`。

## Behavior

### ownership present

- 校验 fieldRef / ownerSlotRef / ownerGroupRef。
- 检测重复 primary。
- 输出 `class=formal` 或 `class=incomplete`。

### ownership absent

- 显式 `legacy_compatible=true`：输出 `class=legacy_compatible`。
- 未标记：输出 `class=unclassified_historical`。
- 两种情况均输出 `PAGE_COMPOSITION_FIELD_OWNERSHIP_MISSING` warning。
- 不中断现有页面。

## Validation coverage

V1 / V2 / V3 / V4 / V5 / V6 / V10 / V12 已实现基础校验。
V7 重复投影校验仍受限于 slot fieldRefs 未完整解析，V9 以
`permissionSemanticsPreserved=true` 声明，V11 复用现有 contractVersion。

## Known limits

- 尚未接入 `Page Composition Integrity Guard`。
- 尚未迁移任何正式页面到 Formal Page。
- 尚未收缩 Legacy fallback。
- 未分类历史页面仅输出诊断，不改变运行行为。

