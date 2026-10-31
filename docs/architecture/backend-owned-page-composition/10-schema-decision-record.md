# 10 · Schema Decision Record

## Status

READY_WITH_CONSTRAINTS

## Recommendation

采用 `REUSE + MINIMAL EXTEND`：

- 复用 `formStructureContract.slots` 表达页面结构。
- 复用 `dataContract.dataMeta.fieldGroups.groups` 表达字段分组。
- 新增 `fieldOwnership` 表达唯一主展示归属。

## Exact minimal structure

```text
fieldOwnership[field:<field_code>]
  ownerSlotRef: slot:<slot_id>
  ownerGroupRef: group:<group_id> (identity 可省略)
```

## Entry condition for Formal Page

1. `formStructureContract.slots` 存在且非空。
2. `fieldOwnership` 覆盖所有主展示字段。
3. 所有引用有效。
4. 每个字段只有一条 ownership 记录；辅助投影由 slot 显式声明。
5. 不依赖隐式 Legacy fallback。
6. 服务端权限边界未改变。

## Next assembler change scope

- 解析并验证 `fieldOwnership`。
- 与 `formStructureContract.slots` / `fieldGroups` 交叉校验。
- 将 `fieldOwnership` 输入 V2 客户端。
- 增加诊断错误 envelope。

