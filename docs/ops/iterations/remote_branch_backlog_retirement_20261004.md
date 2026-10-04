# 远端历史分支积压退役（P4 运维治理）

- 批次：`REMOTE-BRANCH-BACKLOG-RETIREMENT`
- 基线：`main` = `e0d31a120cb245a83cb6ff49fd0105b3459df268`
- 责任层：P4 ops/交付治理；无产品代码、契约、前端、数据库、夹具或部署改动。

## 背景与授权

工作区收口（`WORKSPACE-FINAL-CLOSEOUT`，PR #555）完成后，origin 上仍有 30 个历史
`codex/*` 引用。只读盘点结论：

- **22 个**有 exact-head 已合并 PR（分支 tip == 该 PR 的 `headRefOid`）。
- **8 个**没有该证明：`backend-contract-lifecycle-authority-v1`、
  `contract-governance-closure-v1`、`form-information-architecture-audit-v1`、
  `long-running-business-iteration`（merge 发生在 #124/#125 但 head 不同）、
  `p0-scene-component-bridge-v1`、`p0-ui5-scene-foundation-recovery-v2`、
  `p0-ui5-scene-foundation-spike-v1-recovered`、`tdesign-enterprise-ui-foundation-v1`。

所有者授权（选项 1，2026-10-04）：只退役 22 个已证明合并的分支；8 个待判定分支保留。
其中 `codex/contract-work-reading-efficiency-v1` 虽已证明合并，但被运行时载体扫描命中
（`.agent/goals/CONTRACT-COLLECTION-WORK-ITEM-READING-EFFICIENCY.yaml` 引用了该分支名），
守卫 fail-closed 跳过，故**实际退役 21 条**，该条与 8 条一并保留。

## 证据与绑定

- manifest（受管跟踪）：`docs/ops/manifests/historical_branch_retirement_20261004.json`
- `manifest_sha256` = `2d0e2a37b1bcd85256800d5a00eb13f7e9078cf562f0a28a5ee967167216a006`
  （目录中保存的即被授权并执行的同一字节内容）
- 恢复 bundle：`.runtime/retire/historical-branch-retirement-20261004.bundle`
  （21 MB，`git bundle verify` PASS，`head_count=21`，
  sha256 `636eb1410f807ca69d6c5cc2a6908d01d4616a49ede2823bdf7affa797a1669d`）
- 报告（本机 `.runtime/retire/`）：`dry-run.json`（eligible=21 skipped=0）、
  `bundle-prep.json`（`bundle_prepared`，21）、`apply-report.json`（`completed`，21 条
  全部 `retired`，逐条 `--force-with-lease` 精确 tip lease + `local_absent_confirmed`）。
- 远端复读：apply 后 `git ls-remote --heads origin 'refs/heads/codex/*'` 仅剩 9 条
  （8 条无证明 + 1 条载体命中），与预期一致。

## 逐条 `reviewed_explicit` 依据

每条 manifest 条目声明 `containment: reviewed_explicit`，其 `evidence` 绑定
“remote tip `<sha>`” 与 “merged PR #`<n>` headRefOid=`<sha>`”；即 squash 合并下
无法用祖先关系证明，改由**精确 head 的已合并 PR** 证明。该模式只替代祖先证明：
SHA 漂移、开放 PR、被检出、运行时载体引用与 manifest SHA-256 绑定仍全部 fail-closed。

## 未做 / 保留

- 未退役 8 条无证明分支：需逐条判定“已用尽/被取代”还是“未合并需保留”，不得直接删除。
- 未退役 `codex/contract-work-reading-efficiency-v1`：需先处置 `.agent` 载体引用。
- 未放宽 `make branch.cleanup` 的 `codex/*` 约束，未放宽任何身份/漂移/审计守卫。
