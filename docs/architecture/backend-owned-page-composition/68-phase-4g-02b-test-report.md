# 68 · Phase 4G-02B Test Report

## 环境

- branch：`feature/pc01-r2-identity-status`
- HEAD：`a9cd2fd5879d8a5358c2ad737602e0ae72644555`
- collector / contract：`1.0.0`

## 结果

```text
test_page_composition_evidence_contract.py  Ran 18 tests  OK
test_page_composition_integrity_guard.py    Ran 12 tests  OK
```

## 15 类场景覆盖

| # | 任务要求 | 用例 |
| --- | --- | --- |
| 1 | 合法静态源码证据 | test_valid_static_source_evidence |
| 2 | 合法测试执行证据 | test_valid_test_execution_evidence |
| 3 | 合法运行时证据 | test_valid_runtime_evidence |
| 4 | 人工声明不能冒充运行时 | test_human_review_cannot_masquerade_as_runtime |
| 5 | model/action/view 不匹配 | test_scope_mismatch |
| 6 | repository_sha 不匹配 | test_repository_sha_mismatch_is_stale |
| 7 | evidence_id 重复 | test_duplicate_evidence_id_invalid |
| 8 | 内容摘要不一致 | test_content_digest_mismatch_invalid |
| 9 | 证据过期 | test_expired_evidence_stale |
| 10 | 空证据 | test_empty_evidence_bundle |
| 11 | 手写 JSON 输入 | test_handwritten_json_does_not_become_trusted |
| 12 | 缺少采集来源 | test_missing_collection_source |
| 13 | 历史身份缺少原始依据 | test_historical_reference_without_original_basis |
| 14 | 不同页面证据交叉冒用 | test_cross_page_evidence_rejected |
| 15 | Collector 异常处理 | test_collector_invalid_input_handled |

附加 Guard 可信消费用例：

- 未验证证据不产生 PASS。
- VERIFIED 且范围匹配证据产生 PASS。
- VERIFIED 但范围不匹配不产生 PASS。

## 端到端

collector CLI → bundle → guard_evidence → Guard CLI 全链路验证通过；PC-008
仅对 VERIFIED 权限证据判定 PASS。

## Verdict

READY_WITH_CONSTRAINTS

- Collector 独立：成立。
- Evidence Contract 可验证：成立。
- 手写证据不再直接 PASS：成立。
- PC-007～PC-010 可信输入条件：基础设施就绪，真实证据待 4G-02C 采集。
- 进入 4G-02C 条件：具备。
