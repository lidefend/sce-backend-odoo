# 48 · Project Runtime Layout Source Report

## Evidence

- Native layout 来源：`resolveContractV2ContainerTree(store)` -> containerTree。
- Legacy layout 来源：`useRecordFormFieldSchemas.layoutNodes` -> `buildLegacyLayoutNodes`。
- 本页 native shell 存在，NativeFormTreeRenderer 已渲染。
- Legacy fallback 是否实际参与最终结构：NOT_VERIFIED。

## Conclusion

当前能确认 NativeFormTreeRenderer 从 V2 `layoutContract.containerTree` 消费结构。
但不能确认 Legacy `buildLegacyLayoutNodes` 是否同时影响最终 DOM，因此页面结构
权威性仍未完全证明。

