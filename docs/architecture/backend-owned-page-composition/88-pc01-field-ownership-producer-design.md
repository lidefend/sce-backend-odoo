# 88 · PC-01 Field Ownership Producer Design

## 决定性发现

`fieldOwnership` 在冻结 Schema（07/10 号文档）中定义为字段唯一主归属；assembler
（Phase 3B，`unified_page_contract_v2_assembler.py::_page_composition_contract`）
已实现消费端（读 `source.field_ownership`、归一化、输出 `fieldOwnership` 与
`pageComposition`）。但全仓库没有任何生产者：

```text
rg field_ownership addons/
  -> 仅 assembler.py:753 读取、:818 写归一化结果
  -> form_structure_authority.py / view_orchestrator.py / handlers 均无生产
```

因此五个样本的 `fieldOwnership` 全部缺失，不是“配置没填”，而是“声明能力尚未实现”。

## 现状与目标的结构差距

`build_form_structure_contract` 现有三种形态：

```text
native_authority      -> structureAuthority=container_tree, slots=[]
field_groups          -> 单个 configured_form slot + N groups
entry_semantic_surface -> task_sections
```

冻结 Schema 要求的是 `identity slot + business section slots`，当前实现没有覆盖。
`resolve_form_structure_governance` 已解析 `sections`、`field_groups`、
`semantic_anchors`，但没有把它们转成 `field_ownership`。

## 实施方案（两层）

### P0 · smart_core 通用机制

在 `addons/smart_core/core/form_structure_authority.py::resolve_form_structure_governance`
末尾新增通用派生：

```text
field_ownership = {}
identity_fields = 声明中标记为 identity 的字段集合
对每个 section(section_key, fields):
  slot_id = "identity" if 该 section 是 identity 否则 section_key
  for field in fields:
    if field 已在 field_ownership: 记录 V4 冲突诊断
    else: field_ownership[f"field:{field}"] = {"ownerSlotRef": f"slot:{slot_id}",
                                                "ownerGroupRef": f"group:{section_key}"}
```

并把 `field_ownership` 提升到 source 顶层（assembler 读取位置）：

```text
source_contract["field_ownership"] = field_ownership
```

通用、无行业语义；identity 标记由 P1 声明提供。

### P1 · smart_construction_core 项目声明

为项目详情（590/1776）声明 sections，标记 identity：

```text
identity:            name, project_code, user_id, manager_id, owner_id
business_information: business_nature, phase_key, project_type_id
responsibility:       cost_manager_id, doc_manager_id
```

字段集合必须按 View 1776 实际 arch 复核（本轮已读取 arch，见 87 号文档；
`write_date`/`lifecycle_state`/`sc_approval_state` 等状态字段不属于业务归属）。

## 必须遵守的边界

- P0 只做通用派生，不编码 project / industry 字段。
- identity 标记来自 P1 声明，不由 P0 按字段名推断。
- 同一字段重复归属必须在生产者处产生 V4 诊断，不得静默覆盖。
- 辅助投影（summary/relation/detail）不得进入 field_ownership。

## 验证

1. 新增 P0 单测：field_groups → field_ownership 派生、identity 标记、V4 冲突。
2. 新增 P1 契约测试：项目详情 slots + fieldOwnership 与声明一致。
3. 模块升级后重跑 Guard：PC-001/002/003/004 预期 PASS。
4. 浏览器复核：`data-form-composition` 不变，shadow overlap 收窄。

## 状态

实现待执行。这是 P0 平台核心变更，需走受管车道（formal layer 声明 + 非零定向
测试 + 模块升级），不在只读取证范围内直接改动。
