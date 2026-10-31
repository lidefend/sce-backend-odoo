# 20 · Guard Evidence Gap Analysis

## Gap classification

- A SOURCE_NOT_FOUND：配置或源码缺失。
- B EVIDENCE_NOT_COLLECTED：采集器未运行。
- C RUNTIME_NOT_VERIFIED：未做运行时验证。
- D CONSUMER_CHAIN_NOT_VERIFIED：前端消费链未验证。
- E RULE_IMPLEMENTATION_INCOMPLETE：Guard 规则未完整实现。
- F HISTORICAL_REFERENCE_MISSING：历史对照证据缺失。

## Current distribution

| Rule | Gap |
| --- | --- |
| PC-001 | B |
| PC-002 | B |
| PC-003 | B |
| PC-004 | B |
| PC-005 | E |
| PC-006 | PASS |
| PC-007 | D |
| PC-008 | C |
| PC-009 | C |
| PC-010 | F |

## Key finding

多数 NOT_VERIFIED 来自证据未采集和消费链未验证，不是 Guard 逻辑误判。PC-005
属于 Guard 规则实现不完整，需要后续解析 slot.fieldRefs 后才能判定。

