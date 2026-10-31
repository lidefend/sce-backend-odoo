# 89 · Field Ownership Slot Convention Mismatch

## 实施中发现的根因

P0 派生实现（`form_structure_authority.py` 新增 `field_ownership` 派生）在单元
测试中通过，但端到端核对暴露一处此前未识别的约定不一致：

冻结 Schema（07/10 号文档）：

```text
fieldOwnership[field:<code>].ownerSlotRef = slot:identity
```

运行时 `build_form_structure_contract`（`ui_contract_v2_form_structure.py`）
实际产出：

```text
slot:primary_facts
  group:identity   (role=identity)
  group:relations  (role=relation)
  group:terms      (role=term)
slot:amount_progress
slot:collaboration
slot:details_source
```

即：identity 的运行时 slot 是 `primary_facts`，不是 `identity`。

## 后果

若按冻结 Schema 的 `slot:identity` 派生 ownership，会生成指向不存在 slot 的
引用，assembler 会输出 `PAGE_COMPOSITION_SLOT_REF_INVALID`（V2），页面被判
`incomplete`。

## 为什么 fieldOwnership 从未被产出

`fieldOwnership` 有消费端（assembler），但生产端从未实现；而生产端的缺失源于
冻结 Schema 与运行时 builder 的 slot 命名从未对齐。这不是漏写一个字段，而是
需要一次明确的结构命名裁定。

## 需要裁定

两个选项：

A. 以运行时为准：`field_ownership` 的 `ownerSlotRef` 使用 builder 实际 slot
   （`slot:primary_facts`），identity 用 `group:identity` 表达。
B. 以冻结 Schema 为准：调整 builder，把 identity slot 改名为 `slot:identity`，
   使 runtime 与冻结 Schema 一致。

选项 B 影响所有走 fallthrough 的页面（slot 渲染身份变化），需要全量回归；
选项 A 不动渲染、只改 ownership 派生约定，但偏离 07/10 号文档字面。

## 当前实现状态

- P0 派生 + source 提升 + 4 项单测已落地，62 项既有测试通过。
- 改动对现有页面惰性：无页面声明 sections，`field_ownership` 恒为空，提升为
  空操作，故无回归。
- 在裁定前不得继续 P1 声明，否则会产生无效 slot 引用。
- 按选项 A 回退了基于 section 键的派生与提升，代码已还原到裁定前状态。

## 建议

采用选项 A 并更新 07/10 号文档的 `ownerSlotRef` 示例为 builder 实际 slot，或
采用选项 B 并做全量回归。请裁定后继续。

## 选项 A 裁定后追加发现（实施时暴露）

核对 assembler `_page_composition_contract` 与 builder 的键名，还发现两处此前
未识别的键不一致：

1. builder/normalizer 产出 `formStructureContract.slots[].slot`，但 assembler
   读 `slots[].id`（slot_ids 恒为空）。
2. builder group 用 `name`，`source.field_groups` 用 `fields`/`title`，而
   assembler 读 `dataMeta.fieldGroups.groups[].id`（group_ids 恒为空）。

因此选项 A 的正确实现是三条一致化，而非一条：

```text
a. 派生：fieldOwnership 从 build_form_structure_contract 的 field_roles /
   configured_roles 派生（slot/group 为运行时权威），不再从 section 键派生。
b. slot 键：_page_composition_contract 读 slots[].slot（兼容 id）。
c. group 键：field_groups 与 form_structure groups 统一为稳定 id，并让
   _page_composition_contract 读该 id（兼容 name/group）。
```

这三条必须在同一次 P0 批次中一起落地并用 assembler 测试验证，单条落地都会
产生 V2/V3 无效引用诊断。当前工作树已还原：`form_structure_authority.py` 与
`ui_contract_v2.py` 无 diff，错误派生的测试文件已删除。
