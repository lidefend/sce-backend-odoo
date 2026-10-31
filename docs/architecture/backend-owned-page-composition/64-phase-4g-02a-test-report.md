# 64 · Phase 4G-02A Test Report

## 环境

- branch：`feature/pc01-r2-identity-status`
- HEAD：`a9cd2fd5879d8a5358c2ad737602e0ae72644555`
- Guard 版本：`1.0.0`
- 测试文件：`scripts/verify/test_page_composition_integrity_guard.py`

## 结果

`python3 scripts/verify/test_page_composition_integrity_guard.py`

```text
Ran 12 tests in 0.003s
OK
```

## 用例清单

| 用例 | 场景 | 结果 |
| --- | --- | --- |
| test_empty_slots | slots 为空 | PASS |
| test_single_field_slot | slots 有一个字段 | PASS |
| test_multiple_slots_each_single_field | slots 有多个字段 | PASS |
| test_same_field_multiple_slots_without_ownership | 同字段多 slot 且无 ownership | PASS |
| test_invalid_auxiliary_role_fails | 辅助 role 不合法 → FAIL | PASS |
| test_auxiliary_role_executes_without_name_error | 辅助 role 合法可执行 | PASS |
| test_owner_slot_ref_valid_and_invalid_execute | ownerSlotRef 有效/无效可执行 | PASS |
| test_null_field_values | 输入字段值为 null | PASS |
| test_unexpected_input_types | 非预期输入类型 | PASS |
| test_payment_request_nine_slots_executes | slots=9 结构无 NameError | PASS |
| test_pc006_unaffected | PC-006 不受影响 | PASS |
| test_main_writes_reports_and_returns_zero | main 返回 0 且写 JSON/MD | PASS |

## 任务书十类场景覆盖

| # | 任务要求 | 覆盖用例 |
| --- | --- | --- |
| 1 | slots 为空 | test_empty_slots |
| 2 | slots 一个字段 | test_single_field_slot |
| 3 | slots 多个字段 | test_multiple_slots_each_single_field |
| 4 | 同字段多 slots | test_same_field_multiple_slots_without_ownership |
| 5 | slot role 合法 | test_auxiliary_role_executes_without_name_error |
| 6 | slot role 不合法 | test_invalid_auxiliary_role_fails |
| 7 | fieldOwnership 缺失 | test_same_field_multiple_slots_without_ownership |
| 8 | ownerSlotRef 有效及无效 | test_owner_slot_ref_valid_and_invalid_execute |
| 9 | 字段值为 null | test_null_field_values |
| 10 | 非预期输入类型 | test_unexpected_input_types |

slots=9 专项：`test_payment_request_nine_slots_executes` 构造与
payment.request / Action 649 / View 1773 相同量级的 9 slot 结构，确认不再
抛 NameError。

## 真实样例回归

`guard-sample-action590.json` 修复前后对比：

```text
overall = NOT_VERIFIED（不变）
PC-005 = NOT_VERIFIED（不变）
PC-006 = PASS（不变）
其余规则均 NOT_VERIFIED（不变）
```

## Shadow 退出码

`main()` 返回 0；Guard 未被 Makefile / scripts 引用，不参与任何既有 verify
退出码计算。本轮未改变该语义。

## 输出一致性

`--output-json` 与 `--output-markdown` 均正常写入；JSON 可解析，Markdown 含
全部 10 条规则行。

## 遗留（移交 4G-02C）

- `ownerSlotRef` 前缀（`slot:<id>`）与 slot 裸 id 不一致，导致 PC-005 主 slot
  排除失效。
- `fieldRefs` 为不可迭代标量时仍可能 `TypeError`。

以上不阻塞 4G-02A 验收，但必须在 4G-02C 规则对齐时处理。
