# 65 · Evidence Contract Design

## 目标

把 Guard 从“消费手写 JSON、凭列表非空判定 PASS”升级为“只消费可验证证据”。
Evidence Contract 定义证据身份、来源、范围、时间、等级与验证状态，使每项证据
可追溯、可复核、不可跨页面冒用。

## 证据链

```text
真实证据来源（源码 / 测试 / 运行时 / 历史 / 人工）
    ↓
Independent Evidence Collector（采集、绑定范围、校验完整性）
    ↓
Evidence Contract（身份、范围、时间、等级、验证状态）
    ↓
Integrity Guard（仅对 VERIFIED 且范围匹配的证据判定 PASS）
```

## 字段（至少）

| 字段 | 含义 | 必填 |
| --- | --- | --- |
| evidence_id | 唯一标识 | 是 |
| evidence_type | A～E 五类 | 是 |
| source_type | 更细来源（artifact / perm_test / snapshot …） | 是 |
| source_location | 可复核来源（路径或引用） | 按类型 |
| collection_method | auto_collect / auto_verify / human_provided / unverifiable | 是 |
| collected_at | ISO 时间戳 | 是 |
| repository_sha | 实际基线 | 是 |
| model / action_id / view_id | 适用页面身份 | 是 |
| contract_version | 契约版本 | 是 |
| applies_to_rule | 目标规则 PC-007～PC-010 | 是 |
| verification_status | VERIFIED / UNVERIFIED / SCOPE_MISMATCH / STALE / INVALID | 派生 |
| evidence_grade | SOURCE_VERIFIED / STATIC_CHAIN_VERIFIED / RUNTIME_VERIFIED / NOT_VERIFIED | 派生 |
| content_digest | 内容 SHA-256 | 是（机器可验证证据） |
| collector_version | 采集器版本 | 派生 |

按类型必填：

- SOURCE_STATIC / TEST_EXECUTION / RUNTIME_OBSERVATION / HISTORICAL_REFERENCE：
  `source_location`。
- HUMAN_REVIEW：`review_basis`。

## evidence_type 五类

- SOURCE_STATIC：源码及静态调用链。
- TEST_EXECUTION：真实测试执行结果。
- RUNTIME_OBSERVATION：实际运行时请求/响应与消费链观察。
- HISTORICAL_REFERENCE：有明确来源的历史快照、节点身份与映射。
- HUMAN_REVIEW：人工审查结论，必须含审核依据。

## 验证状态优先级

```text
结构错误（缺字段/非法枚举/时间戳不可解析） → INVALID
范围不匹配（model/action/view 不一致）      → SCOPE_MISMATCH
过期（repository_sha 不一致 / expires_at 已过）→ STALE
HUMAN_REVIEW                               → 恒为 UNVERIFIED
摘要匹配                                   → VERIFIED
摘要不匹配                                 → INVALID
无法校验（无摘要/无来源）                    → UNVERIFIED
```

## evidence_grade 派生

仅当 `verification_status == VERIFIED` 时按 evidence_type 派生，否则恒为
NOT_VERIFIED：

| evidence_type | grade |
| --- | --- |
| SOURCE_STATIC | SOURCE_VERIFIED |
| TEST_EXECUTION | STATIC_CHAIN_VERIFIED |
| RUNTIME_OBSERVATION | RUNTIME_VERIFIED |
| HISTORICAL_REFERENCE | SOURCE_VERIFIED |
| HUMAN_REVIEW | NOT_VERIFIED |

## 可信度规则（10 条）

1. evidence_id 必须唯一。
2. model/action_id/view_id 必须与验证对象匹配。
3. repository_sha 必须记录实际基线。
4. 测试证据必须包含实际执行结果（source_location + 摘要）。
5. 运行时证据必须包含实际观察来源。
6. 历史身份必须有可追溯原始依据。
7. 内容摘要必须可复核。
8. 过期证据不得用于当前版本。
9. 不同页面证据不得交叉冒用。
10. 人工声明不得自动转换为运行时证据。

证据缺失、过期或范围不匹配时，拒绝用于 PASS 判定。

## Guard 消费接口

- Guard 只把 `verification_status == VERIFIED` 且 model/action/view 与页面一致的
  证据用于 PASS。
- 未验证/手写证据计入 `evidence_trust[*].untrusted`，不产生 PASS。
- 四个证据键：`legacy_fallback_sources`、`permission_evidence`、
  `version_compatibility_evidence`、`historical_node_identity_evidence`。
