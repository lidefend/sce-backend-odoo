# 远端历史分支积压退役 B（P4 运维治理）

- 批次：`REMOTE-BRANCH-BACKLOG-RETIREMENT-B`
- 分支：`fix/remote-branch-backlog-retirement-20261005`
- 基线：`main` = `b6fe93f451bd29d356f9f07bb8ba223ee53ed195`（PR #567 后干净主线）
- 责任层：P4 ops/交付治理；无产品代码、契约、前端、数据库、夹具或部署改动。

## 背景与授权

`REMOTE-BRANCH-BACKLOG-RETIREMENT`（2026-10-04）退役了 21 条已证明合并的 `codex/*`
引用后，origin 仍积压约 258 条历史分支。其 `next_exact_step` 明确：剩余积压需"单独授权
的 P4 变更接受 reviewed explicit list，或 owner 政策决定"。本批次即该授权后的执行。

owner 授权（选项 1，2026-10-05）：退役**仅**那些远端 tip 精确等于某个已合并 PR
`headRefOid` 的历史 origin 分支；无该证明者保留。181 条清单经 owner 逐项审核。

## 只读盘点结论（origin，expected-main `b6fe93f4`）

- **181** 条可执行：tip == 已合并 PR 的 `headRefOid`（squash 合并，tip 非 main 祖先），
  本地引用已不存在（纯远端删除），无工作树占用、无开放 PR（当前开放 PR=0）。
  前缀：fix 146 / feature 28 / audit 6 / refactor 1。
- **显式排除**：
  - 50 条无匹配已合并 PR（未合并工作，必须保留；含 8 条 `codex/*`）。
  - 19 条 `release/*`（结构性受保护）。
  - 5 条非治理前缀（`backup/*` ×2、`feat/*` ×3）。
  - 3 条被运行载体引用阻断，需另开 P4 清载体：
    `audit/historical-branch-asset-retirement-v1`（`.agent/goals/HISTORICAL-BRANCH-ASSET-RETIREMENT.yaml:17`）、
    `fix/atomic-release-publication-contract` 与 `fix/controlled-merge-expected-head-guard`
    （`scripts/verify/test_branch_governance_consistency_guard.py` 测试夹具）。

## 证据与绑定

- manifest（受管跟踪）：`docs/ops/manifests/historical_branch_retirement_20261005.json`
- `manifest_sha256` = `9d59ee32ea2b4444bda943e3a981243f0d4a88a42f55d54500ccc9a8d87277e5`
- 恢复 bundle：`.runtime/retire/historical-branch-retirement-20261005.bundle`
  （`git bundle verify` PASS，完整历史，`head_count=181`，
  sha256 `132c1a66e88cd8647285569f748b5d128995ec7dbacf811deab2eb50dd3e8005`）
- 报告（`.runtime/retire/`）：`dry-run-20261005.json`（eligible=181 skipped=0）、
  `bundle-prep-20261005.json`（`bundle_prepared`，181）、
  `apply-report-20261005.json`（`completed`，181 条全部 `retired`，逐条
  `remote_deleted` + `local_absent_confirmed`）。
- 远端复读：apply 后 `git ls-remote --heads origin` 由 259 → **78**；
  181 条目标引用 **0 条残留**；排除集完整保留。

## 逐条 `reviewed_explicit` 依据

每条 manifest 条目声明 `containment: reviewed_explicit`，`evidence` 绑定
"remote tip `<sha>`" 与 "merged PR #`<n>` headRefOid=`<sha>`"。该模式**仅**替代
祖先证明：SHA 漂移、开放 PR、被检出、运行时载体引用与 manifest SHA-256 绑定
全部照旧 fail-closed，本批次 0 skip 即逐条通过上述守卫。

## 未做 / 保留

- 未退役 50 条无证明分支：需逐条判定"已用尽/被取代"还是"未合并需保留"。
- 未退役 19 条 `release/*`、5 条非治理前缀。
- 未退役 3 条载体引用分支：需先清载体（另一 P4）。
- 未放宽任何身份/漂移/审计守卫；未直接操作容器或绕过 DENY。
