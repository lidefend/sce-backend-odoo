# 87 · PC-01 Backend Declaration Design

## 目标

为项目详情（project.project / Action 590 / View 1776）补齐业务组合声明：
`formStructureContract.slots` + `fieldOwnership`，使页面从 `unclassified_historical`
具备 Formal 准入基础。

## 已确认机制

`smart_core/handlers/ui_contract_v2.py::_form_structure_governance`：

- 读取 `source.views.form.governance.view_orchestration.form_structure_projection`。
- 该投影不存在时，回落到 `form_structure_authority = native_authority`。
- `build_form_structure_contract` 对 `native_authority` 返回
  `structureAuthority = container_tree` + `slots = []`。
- 只有 `governance.field_groups`（dict）存在时，才产出 `native_form_slots` +
  `configured_form` slot。
- `fieldOwnership` 由 assembler 从 `source.get("field_ownership")` 读取。

事实：当前项目详情（590/1776）无任何 `ui.business.config.contract` 记录，因此
slots=0、fieldOwnership 缺失。

## 已确认模型字段

```text
name(char, required)  project_code(char, readonly)  user_id(m2o)  manager_id(m2o)
owner_id(m2o)  business_nature(char)  phase_key(selection)  project_type_id(m2o)
cost_manager_id(m2o)  doc_manager_id(m2o)
```

## 声明设计（DRAFT，需按 View 1776 实际 arch 复核）

### field_groups（产出 slots）

```text
identity:
  name, project_code, user_id, manager_id, owner_id
business_information:
  business_nature, phase_key, project_type_id
responsibility:
  cost_manager_id, doc_manager_id
```

### field_ownership（唯一主归属）

```text
field:name            -> slot:identity, group:identity
field:project_code    -> slot:identity, group:identity
field:user_id         -> slot:identity, group:identity
field:manager_id      -> slot:identity, group:identity
field:owner_id        -> slot:identity, group:identity
field:business_nature -> slot:business_information, group:business_information
field:phase_key       -> slot:business_information, group:business_information
field:project_type_id -> slot:business_information, group:business_information
field:cost_manager_id -> slot:responsibility, group:responsibility
field:doc_manager_id  -> slot:responsibility, group:responsibility
```

## 载入路径（应用前需确认）

两条候选：

1. P1 数据记录：新增 `ui.business.config.contract`（`smart_construction_core/data`），
   在 `contract_json` 中声明 `form_structure_projection`（含 `field_groups` +
   `form_structure_authority`）与顶层 `field_ownership`。
2. P1 代码扩展：在 `smart_construction_core/core_extension.py` 对
   project.project form 注入 `form_structure_projection` 与 `field_ownership`。

应用前必须确认：`field_ownership` 最终落在 assembler 读取的 `source` 顶层，且
`field_groups` 经 `form_structure_projection` 进入 governance。

## 验证计划

1. 模块升级（受管 `local.dev.*` / acceptance 车道）。
2. 重跑 Guard：预期 PC-001/002/003/004 转 PASS，PC-005 依投影语义判定。
3. 浏览器观察：`data-form-composition` 仍为 official-standard-form，slots 非空，
   shadow overlap 收窄。
4. 定向测试：新增 P1 契约测试，锁定 slots 与 fieldOwnership。

## 风险

- 错误的字段归属会把重复主展示入口带入 Formal，违反 PC-005。
- 必须按 View 1776 真实 arch 复核字段集合，不得按字段名或创建入口推断。

## 状态

设计待应用；正式写入产品配置需在受管车道执行，不在此轮直接改动。
