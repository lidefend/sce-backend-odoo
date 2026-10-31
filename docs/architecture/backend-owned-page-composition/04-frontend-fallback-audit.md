# 04 · Frontend Fallback Audit

## Second structure authority

`useRecordFormFieldSchemas.ts`：

```ts
buildLegacyLayoutNodes({
  order: [],
  visibleFields: contractVisibleFields.value,
  fallbackFieldNames: [...coreFieldNames, ...advancedFieldNames],
})
```

`buildLegacyLayoutNodes` 在 `order=[]` 且没有 field nodes 时，会 fallback 到
`visibleFields` 或 `fallbackFieldNames`。

## Consumers

- `coreFieldNames` / `advancedFieldNames` 来自 `useRecordContractSemantics`，
  按 surface role 从契约字段语义生成。
- 正式页面仍可能通过该 fallback 获得字段集合。

## Conclusion

前端仍存在第二套业务结构生成路径。它可能在契约字段分组缺失时静默补齐页面字段，
这正是 B1 身份重复的上游风险。

