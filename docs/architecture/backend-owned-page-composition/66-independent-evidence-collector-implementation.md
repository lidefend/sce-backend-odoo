# 66 · Independent Evidence Collector Implementation

## 新增文件

- `scripts/verify/page_composition_evidence_contract.py`：Evidence Contract
  字段定义与 `validate_evidence_item`。
- `scripts/verify/page_composition_evidence_collector.py`：独立采集入口。
- `scripts/verify/test_page_composition_evidence_contract.py`：18 项测试。

## 修改文件

- `scripts/verify/page_composition_integrity_guard.py`：最小接口适配。
  - 新增 `_scope_matches` / `_trusted_items`。
  - PC-007～PC-010 只以 VERIFIED 且范围匹配的证据判定 PASS。
  - 报告新增 `evidence_trust`。

## Collector 职责

- 证据来源识别（evidence_type / source_type）。
- 采集范围校验（model/action/view 绑定）。
- 完整性摘要（SHA-256 与 source_location 比对）。
- 证据身份绑定（evidence_id 唯一、repository_sha）。
- 验证状态与证据等级派生。
- 输出 bundle + guard_evidence 投影。

## 使用

```bash
python3 scripts/verify/page_composition_evidence_collector.py \
  --input raw-evidence.json \
  --repository-sha <sha> \
  --contract-version 2.2.0 \
  --output bundle.json
```

`raw-evidence.json`：

```json
{
  "target_page": {"model": "payment.request", "action_id": 649, "view_id": 1773},
  "contract_version": "2.2.0",
  "items": [ { "...": "evidence item" } ]
}
```

## 输出

```text
collector_version / collected_at / repository_sha / contract_version / target_page
items[]（含 verification_status 与 evidence_grade）
summary（VERIFIED / UNVERIFIED / SCOPE_MISMATCH / STALE / INVALID 计数）
untrusted[]（非 VERIFIED 的 evidence_id）
guard_evidence{legacy_fallback_sources, permission_evidence, ...}
```

## 关键语义

- 手写 JSON 只作为待审核输入；无摘要或无法复核的证据恒为 UNVERIFIED。
- HUMAN_REVIEW 即使附摘要与文件也恒为 UNVERIFIED：文档存在不等于结论可信。
- 摘要不匹配 → INVALID（疑似篡改），不降级为 UNVERIFIED。
- 范围不匹配 → SCOPE_MISMATCH；基线不一致/过期 → STALE。

## Guard 最小适配

- PASS 条件从“列表非空”改为“存在 VERIFIED 且范围匹配的证据”。
- Action 590 手写 fallback 字符串现被计入 untrusted（PC-007 仍 NOT_VERIFIED）。
- Shadow 执行方式与 `main()` 退出码不变。
