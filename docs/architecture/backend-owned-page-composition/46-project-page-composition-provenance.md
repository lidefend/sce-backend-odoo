# 46 · Project Page Composition Provenance

## Actual structure sources

Action 590 / 652 两个项目入口的 V2：

```text
formStructureContract.slots = []
fieldGroups = false
layoutContract.containerTree = 存在
```

当前页面渲染：

```text
data-form-composition = legacy-form-section
detail composition adopted = true
NativeFormTreeRenderer 实例 = 30
```

## Finding

- V2 `slots` 不是页面结构的实际来源。
- `layoutContract.containerTree` 是 NativeFormTreeRenderer 的直接输入。
- Legacy FormSection 仍可能通过 `buildLegacyLayoutNodes` 生成另一套字段节点。

因此页面结构来源需要进一步区分：

1. NativeFormTreeRenderer：消费 `layoutContract.containerTree`。
2. Legacy FormSection：消费 `useRecordFormFieldSchemas.layoutNodes`，
   其 fallback 来自 `buildLegacyLayoutNodes`。

