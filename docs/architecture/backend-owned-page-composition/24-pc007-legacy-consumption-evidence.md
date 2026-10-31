# 24 · PC-007 Legacy Fallback Evidence

## Evidence

`useRecordFormFieldSchemas.ts` 调用：

```ts
buildLegacyLayoutNodes({
  order: [],
  visibleFields,
  fallbackFieldNames: [...coreFieldNames, ...advancedFieldNames],
})
```

`buildLegacyLayoutNodes` 在 `order=[]` 且无 field nodes 时，使用
`visibleFields` 或 `fallbackFieldNames`。

## Status

NOT_VERIFIED

## Reason

已确认源码调用链和 fallback 条件，但尚未逐页面证明运行时实际进入 fallback。

## Evidence levels

- 源码存在：PASS
- 调用链可达：PASS（useRecordFormFieldSchemas → buildLegacyLayoutNodes）
- 运行时实际消费：NOT_VERIFIED

