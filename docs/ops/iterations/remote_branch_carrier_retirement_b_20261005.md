# 载体引用清理与三条已合并分支退役（P4 运维治理）

- 批次：`REMOTE-BRANCH-CARRIER-RETIREMENT-B`
- 分支：`fix/remote-branch-carrier-retirement-20261005`
- 基线：`main` = `1a7db19faf9321d7199767e7fbe375cb82688517`（PR #568 后干净主线）
- 责任层：P4 ops/交付治理；无产品语义、契约、数据库、夹具或部署改动。

## 背景与授权

`REMOTE-BRANCH-BACKLOG-RETIREMENT-B` 退役 181 条后，origin 残留 78 头。其中三条
（`audit/historical-branch-asset-retirement-v1`、`fix/atomic-release-publication-contract`、
`fix/controlled-merge-expected-head-guard`）均已有 **exact-head 已合并 PR**，仅因运行时
载体文本引用被守卫 fail-closed 跳过。owner 授权（选项 1，2026-10-05）清理这些陈旧载体
引用后按受管入口退役。

## 载体清理（不放宽任何守卫/断言）

1. `.agent/goals/HISTORICAL-BRANCH-ASSET-RETIREMENT.yaml`：baseline `branch` 由已完成的
   交付分支名重指向 `main`，并加 note 说明（与 `codex/contract-work-reading-efficiency-v1`
   先例一致）。
2. `.agent/runs/REMOTE-BRANCH-BACKLOG-RETIREMENT-B/run.json`：保留清单中的三条字面名改为
   不含字面名的 followup 说明（先例：清理已完成 run 记录的保留清单项）。
3. `scripts/verify/test_branch_governance_consistency_guard.py`：假 git stub 输出的两条分支名
   改为**非真实**占位名 `fix/fixture-merge-guard-head`、`fix/fixture-atomic-release-head`；
   **未改动任何断言**，占位名仍匹配受管前缀正则。

清理后 `git grep -F` 对三条名在 `scripts config deploy make .agent .github` 均 0 命中。

## 证据与绑定

- manifest（受管跟踪）：`docs/ops/manifests/historical_branch_retirement_carrier_20261005.json`
- `manifest_sha256` = `d0969dea124671ae2b084182f6335bb7ec50301a647decaa2e3c331f45c04187`
- PR 证据：`audit/historical-branch-asset-retirement-v1` = PR #462（head `c0bed94d…`，2026-09-11 合并）；
  `fix/atomic-release-publication-contract` = PR #34（head `9566330f…`，2026-07-23 合并）；
  `fix/controlled-merge-expected-head-guard` = PR #31（head `921bf3c0…`，2026-07-23 合并）。
- 恢复 bundle：`.runtime/retire/historical-branch-retirement-carrier-b-20261005.bundle`
  （`git bundle verify` PASS，完整历史，`head_count=3`，
  sha256 `2be56d875f1a400f50edeec434249e1d517ce91db4c1fc58326becf69fa9a098`）
- 报告（`.runtime/retire/`）：`dry-run-carrier-b.json`（eligible=3 skipped=0）、
  `bundle-prep-carrier-b.json`（3）、`apply-report-carrier-b.json`（`completed`，3 条全部
  `retired`，逐条 `remote_deleted` + `local_absent_confirmed`）。
- 远端复读：origin 由 78 → **75** 头；3 条目标引用 0 残留。

## 未做 / 保留

- 未退役 3 条 `feat/`、`backup/` 内容已合并分支（前缀不在治理正则内，需 owner 前缀策略决定）。
- 未退役 19 条 `release/*` 与 52 条含真实未合并提交的历史分支。
- 未改任何守卫、断言、前缀正则或审计。
