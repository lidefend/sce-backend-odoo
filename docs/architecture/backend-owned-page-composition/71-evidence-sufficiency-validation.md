# 71 · Evidence Sufficiency Validation

## 四个独立概念

| 维度 | 含义 |
| --- | --- |
| Evidence VERIFIED | 证据来源完整性（digest / 范围 / 时效）经核验 |
| Rule PASS | 可信证据足以证明规则成立 |
| Rule NOT_VERIFIED | 证据不足或证据不充分 |
| Rule FAIL | 存在明确违反规则的事实 |

这四者不得混用：VERIFIED 只是前提，不自动产生 PASS。

## 充分性门禁

- `_trusted_items`：只保留 `verification_status == VERIFIED` 且范围匹配的证据。
- `_sufficient_items`：在可信证据上追加规则级 type / coverage 过滤。
- 每条规则声明允许的 evidence_type 与必要 coverage（见 70 号文档）。

## 验证

- `test_verified_scope_matched_evidence_passes`：VERIFIED + 充分 coverage → PASS。
- `test_verified_but_insufficient_permission_evidence_does_not_pass`：VERIFIED
  但 coverage 仅 smoke → NOT_VERIFIED。
- `test_permission_runtime_observation_pass`：RUNTIME_OBSERVATION + 权限覆盖 → PASS。
- `test_version_regression_pass` / `test_historical_mapping_pass`：对应充分证据
  → PASS。

## PC-008 专项

即使 TEST_EXECUTION 证据已 VERIFIED，也必须覆盖：

```text
server_permission_mechanism
authorized_access
unauthorized_denied
```

否则 PC-008 保持 NOT_VERIFIED，`permissionSemanticsPreserved=true` 始终只是声明。

## evidence_summary

每个证据键输出 `total / trusted / sufficient / verified_insufficient / untrusted`，
明确区分“证据已验证”与“证据足以证明规则”。
