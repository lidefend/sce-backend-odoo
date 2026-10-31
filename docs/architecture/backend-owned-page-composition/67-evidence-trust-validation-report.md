# 67 · Evidence Trust Validation Report

## 结论

Evidence Collector 独立、Evidence Contract 可验证、手写证据不再能直接产生 PASS。

## 五问回答

1. Collector 是否独立：是。`page_composition_evidence_collector.py` 独立于
   Guard，只依赖 Evidence Contract 模块。
2. Evidence Contract 是否具备可验证性：是。身份、范围、时间、摘要、等级与
   验证状态均被强制校验，摘要与来源文件 SHA-256 比对。
3. 手写证据是否仍能直接产生 PASS：否。未验证证据恒为 UNVERIFIED，Guard 只对
   VERIFIED 且范围匹配的证据判定 PASS。
4. PC-007～PC-010 是否已具备可信证据输入条件：基础设施已具备；真实权限/运行时/
   旧消费者/历史身份证据仍需在 4G-02C 采集，当前五项规则仍 NOT_VERIFIED。
5. 是否具备进入 4G-02C 的条件：是。

## 十条可信度规则验证

| # | 规则 | 验证 |
| --- | --- | --- |
| 1 | evidence_id 唯一 | 重复 id → 第二个 INVALID |
| 2 | model/action/view 匹配 | 不匹配 → SCOPE_MISMATCH |
| 3 | repository_sha 记录基线 | 不一致 → STALE |
| 4 | 测试证据含实际结果 | 缺 source_location → INVALID |
| 5 | 运行时证据含观察来源 | RUNTIME_OBSERVATION 需 source_location |
| 6 | 历史身份有原始依据 | 缺 source_location → INVALID |
| 7 | 摘要可复核 | 摘要不匹配 → INVALID |
| 8 | 过期不得用于当前版本 | expires_at 已过 → STALE |
| 9 | 不得跨页面冒用 | 跨页 → SCOPE_MISMATCH |
| 10 | 人工声明不转运行时证据 | HUMAN_REVIEW 恒 UNVERIFIED |

## 端到端验证

```text
raw JSON → collector（perm-1 VERIFIED / handwritten-1 UNVERIFIED）
→ guard_evidence → Guard → PC-008 = PASS（仅 perm-1 生效）
evidence_trust.permission_evidence = {trusted:1, total:1, untrusted:0}
```

## 回归

Action 590 样例规则结果不变（overall NOT_VERIFIED，PC-006 PASS，其余
NOT_VERIFIED）；新增 `evidence_trust` 后 legacy fallback 手写字符串被标记为
untrusted，PC-007 仍 NOT_VERIFIED。

## 边界声明

Collector 验证的是证据来源完整性（digest / scope / freshness / type），不是
替代运行时再次观测。RUNTIME_OBSERVATION 的 VERIFIED 表示“已核验记录的运行时
证据产物完整性”；其业务结论仍由 Guard 规则与独立评审判定。
