# 07 · Field Ownership Schema Design

## Recommendation

唯一推荐方案：在现有 V2 顶层新增 `fieldOwnership`，采用 map 结构，键为
稳定字段引用，值为字段所有权记录。

## JSON shape

```json
{
  "fieldOwnership": {
    "field:project_code": {
      "ownerSlotRef": "slot:identity",
      "ownerGroupRef": "group:identity"
    },
    "field:user_id": {
      "ownerSlotRef": "slot:identity",
      "ownerGroupRef": "group:identity"
    },
    "field:owner_id": {
      "ownerSlotRef": "slot:basic_information",
      "ownerGroupRef": "group:basic_information"
    }
  }
}
```

## Fields

### fieldRef

- 形式：`field:<field_code>`。
- 使用契约字段代码，不直接使用任意 Odoo 字段名。

### ownerSlotRef

- 形式：`slot:<slot_id>`。
- 指向 `formStructureContract.slots[].id` 的稳定身份。
- 每个主展示字段必须有 ownerSlotRef。

### ownerGroupRef

- 形式：`group:<group_id>`。
- 指向 `dataContract.dataMeta.fieldGroups.groups[].id`。
- identity 字段允许省略 ownerGroupRef；业务 Section 字段必须提供。

### displayRole

`fieldOwnership` 不承载 `displayRole`。主展示归属由 `ownerSlotRef` 唯一表达。
其他展示投影（只读摘要、关联引用、明细引用）由 `formStructureContract.slots`
的字段引用与 slot 角色表达，不通过第二条 ownership 记录模拟。

正式页面不允许给 `displayRole` 设隐式默认值。

## Identity

Identity 必须由 `formStructureContract.slots` 显式声明，不得由字段名推断。

## Projection rule

- `fieldOwnership` 始终只记录唯一 primary owner。
- 只读摘要等辅助投影必须在 slot 中显式声明。
- 不允许通过多份 ownership 记录表达同一字段的多个展示投影。

