# 22 · PC-005 Projection Validation

## Implementation

PC-005 现在基于：

- `formStructureContract.slots[].fieldRefs`
- `slots[].groups[].fieldRefs`
- `slots[].role`
- `fieldOwnership`

判定逻辑：

1. 构建 field -> slot 集合。
2. 单 slot 字段跳过。
3. 多 slot 字段必须有 fieldOwnership primary owner。
4. 其他 slot role 属于辅助语义集合时进入 NOT_VERIFIED，否则 FAIL。

辅助语义集合：

```text
summary, context, relation, detail, activity, audit
```

## Behavior

- 无 slot 数据：NOT_VERIFIED。
- 多 slot 且无 ownership：NOT_VERIFIED。
- 多 slot 且辅助 role 不明：FAIL。
- 多 slot 且辅助 role 明确：NOT_VERIFIED（不直接 PASS，需进一步语义证据）。

