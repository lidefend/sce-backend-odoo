# 工作区最终收口（P4 运维治理）

- 批次：`WORKSPACE-FINAL-CLOSEOUT`
- 基线：`main` = `0430f1b98466a4d07c78619db5bc56d6c9416ed7`（PR #554 合并后，工作区干净）
- 责任层：P4 ops/交付治理；不涉及 P0/P1/P2/P3 产品语义，不涉及数据库、夹具、构建产物或部署。

## 背景

squash-aware 退役批次（PR #553/#554）修复了受管退役入口并退役了 3 个候选分支。
本轮对收口后的工作区做一次身份核对，发现两类**残留**，均无产品影响：

1. 本地仍有 7 个候选分支，其 tip 都有已合并 PR：
   - 3 个 `codex/*`（入口限定 `codex/*`）
   - 2 个 `audit/*` + 2 个 `fix/*`（入口拒绝，需走 `branch.cleanup.feature`）
2. `.agent/active-runs.json` 的两条映射都指向已不存在的分支（悬挂台账）。

## 处理与证据

所有退役都经**受管入口**，先 DRY-RUN 再 APPLY，全部为 `--force-with-lease` 精确 lease 删除，
无 `git push --delete`、无强删、无 force push。

### codex/*（`make branch.cleanup`）

| 分支 | 本地 SHA | origin/main | 判定 |
| --- | --- | --- | --- |
| `codex/daily-dev-acceptance-fixture-lane-20261004` | `fad6884b…` | `0430f1b9` | exact-head merged PR，`squash_verified=1` |
| `codex/daily-dev-mainline-redeploy-20261003` | `c524d267…` | `0430f1b9` | exact-head merged PR，`squash_verified=1` |
| `codex/daily-fixture-lane-runtime-closeout-20261004` | `f0304b1f…` | `0430f1b9` | exact-head merged PR，`squash_verified=1` |

### audit/*、fix/*（`make branch.cleanup.feature`，脚本允许清单含 `audit|fix`）

| 分支 | 本地 SHA | 合并 PR | merge commit ⊆ origin/main |
| --- | --- | --- | --- |
| `audit/gitee-formal-package-refresh-20261003` | `5d0a0a3c…` | #545 | 是（`a9020e86…`） |
| `audit/gitee-formal-package-refresh-closeout` | `49e19ec1…` | #546 | 是（`64efb6bf…`） |
| `fix/daily-dev-acceptance-fixture-runtime-20261004` | `0fea38cc…` | #549 | 是（`0250853e…`） |
| `fix/daily-dev-fixture-auth-verify-20261004` | `9a29cb49…` | #550 | 是（`8a77c237…`） |

退役后 `git branch` 仅剩 `main`；远端对应 ref 由各自 lease 精确删除。

### active-runs.json

- 移除 `codex/squash-aware-retirement-closeout-20261004`（分支已退役）。
- 移除 `codex/daily-fixture-lane-runtime-closeout-20261004`（本批退役）。
- 按既有先例（`release`/closeout 记录：退役分支不得留在索引）将索引清为 `{}`，使索引中
  不存在指向已删除分支的映射；历史 run 记录仍保留在 `.agent/runs/*`。

## 明确未做（保留为独立授权）

- origin 上仍有 **33** 个历史 `codex/*` 分支（`daily-runtime-sync-*`、`*-normalization-v1`、
  `tdesign-*`、`uc4-g0*` 等）。批量退役需要一份逐条 `reviewed_explicit` manifest（每条引用已合并
  PR 与精确 head SHA）与单独授权；本轮不执行，也不放宽 `branch.cleanup` 的 `codex/*` 约束。
- 不改动 `make branch.cleanup` 的 `codex/*` 限制，不改动审计/身份/工作树占用守卫。

## 验证

- L1/L2 定向：`verify.agent.resume.unit`、`verify.workspace.worktree.guard`（非零用例，见 run 回执）。
- 本批为元数据/文档改动，无浏览器矩阵、无夹具重置、无部署。
