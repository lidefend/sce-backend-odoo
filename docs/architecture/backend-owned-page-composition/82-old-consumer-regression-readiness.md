# 82 · Old Consumer Regression Readiness（PC-009）

## 结论

旧消费者回归可执行性：NOT_VERIFIED

## 现状

- 仓库中不存在 `old_consumer_regression` 命名的既有测试（仅 Guard 的 coverage
  标记字符串引用该概念）。
- 已识别的旧消费链：`v2/client.ts`（Decoder 入口）、`v2/store.ts`、
  `useRecordFormFieldSchemas.ts`、`NativeFormTreeRenderer.vue`。

## 缺口

1. 无现成回归测试入口，需新增（属 P4 测试，不在本轮执行）。
2. 新增字段（fieldOwnership / pageComposition / containerTree）对旧消费者的
   兼容性未通过实际测试证明。
3. 590/1776 与 652/944 的 action/view 隔离未验证。

## 下一批

在 4H-02B 授权新增只读回归测试，覆盖旧 Decoder / Store 消费新契约、缺字段时
旧行为符合兼容政策、两入口不串用。
