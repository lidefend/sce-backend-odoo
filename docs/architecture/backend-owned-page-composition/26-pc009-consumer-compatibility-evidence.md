# 26 · PC-009 Consumer Compatibility Evidence

## Consumers

- V2 Contract Decoder / Store。
- 页面结构消费者。
- 旧版本消费者。

新增字段：

- `fieldOwnership`
- `pageComposition`

## Status

NOT_VERIFIED

## Reason

尚未通过实际旧消费者测试证明新增字段不会破坏旧页面。源码结构显示新增字段为可选，
但缺少运行回归证据。

