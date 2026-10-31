# 90 · P0 Field Ownership Producer Implementation

## 状态

P0 批次（选项 A）+ 显式 identity 声明 + P1 项目声明已落地，待模块升级做运行时
验证。

## 已实现

1. 生产者：`ui_contract_v2_form_structure.py::build_form_structure_contract`
   新增 `derive_field_ownership`，从 `field_roles`（fallthrough）与
   `configured_roles`（configured_field_groups）派生 `fieldOwnership`；
   `native_authority` 返回空 `fieldOwnership`。
2. slot 键：`unified_page_contract_v2_assembler.py::_page_composition_contract`
   读 `slots[].slot`（兼容 `id`）。
3. group 键：同函数读 `groups[].name` / `groups[].group`（兼容 `id`）。
4. source 提升：`ui_contract_v2.py` 在构建 `form_structure_contract` 后，把
   `fieldOwnership` 提升到 `source_contract["field_ownership"]`（assembler
   读取位置）。
5. 显式 identity：`form_structure_authority.py` 捕获声明中的 `identity_fields`，
   `build_form_structure_contract` 优先使用显式声明，不再依赖泛化字段名候选。

## 语义

ownerSlotRef / ownerGroupRef 使用 builder 运行时权威 slot/group 命名：

```text
identity 字段 -> slot:primary_facts, group:identity
relation 字段 -> slot:primary_facts, group:relations
```

不再使用冻结 Schema 的 `slot:identity`（见 89 号文档裁定）。

## 验证状态

- 语法检查通过（3 个改动文件）。
- 新增 3 项生产者单测通过（含显式 identity_fields 覆盖）。
- 既有 115 项 standalone 测试通过（62 view_orchestrator + 53 guard/evidence）。
- Odoo 车道 `contract_assembly_determinism` 两次 PASS（3 tests）。
- XML 数据文件格式校验通过。

## P1 声明

`smart_construction_core/data/view_orchestration_form_section_contract_data.xml`
新增 `business_config_contract_project_overview_form_structure_v1`，为
590/1776 声明 `identity_fields: [name, project_code, user_id, manager_id, owner_id]`。

## 待办

1. Odoo 车道跑 assembler 相关测试。
2. 模块升级 `smart_construction_core`，运行项目概览契约测试，重跑 Guard。
3. 浏览器复核 590/1776：slots 非空、fieldOwnership 出现、shadow overlap 收窄。
