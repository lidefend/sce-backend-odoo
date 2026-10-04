# 载体引用历史分支退役（P4 运维治理）

- 批次：`REMOTE-BRANCH-CARRIER-RETIREMENT`
- 基线：`main` = `8cca49e20a62c314b6021bdc3c44fc9c2eebf686`（PR #556 合并后）
- 责任层：P4 ops/交付治理；无产品代码、契约、前端、数据库、夹具或部署改动。
- 前置：`REMOTE-BRANCH-BACKLOG-RETIREMENT`（批次验收完成，PR #556）。

## 背景

上一轮退役了 21 条 origin `codex/*` 引用。该轮 `retained` 列表中，
`codex/contract-work-reading-efficiency-v1` 已被证明合并，却**被运行时载体扫描命中**
而 fail-closed 跳过：

- `.agent/goals/CONTRACT-COLLECTION-WORK-ITEM-READING-EFFICIENCY.yaml:15`
  的 `baseline.branch` 仍是在用的分支名字面量。
- `.agent/runs/REMOTE-BRANCH-BACKLOG-RETIREMENT/run.json` 的 `completion.retained`
  也逐条列名（含该分支）。

守卫口径（`scripts/ops/retire_historical_branch_refs.py:CARRIER_ROOTS`=
`scripts, config, deploy, make, .agent, .github`）只认**实时引用**：`docs/` 下的迭代叙述
不算引用，`scripts/config/deploy/make/.agent/.github` 下任何仍含分支名字面量的受跟踪文件
都算。因此要退役该分支，必须先在同一个候选里清掉这两个载体引用；manifest 放在
`docs/ops/manifests/`（非载体根），分支名只出现在那里与本文档。

所有者授权（2026-10-04「同意授权」）：清载体引用并退役该条；其余 8 条仅做只读判定，
未获明确授权前不动。

## 内容级判定（只读）

口径：分支自身增量 = `git diff merge-base(tip, origin/main) tip` 的文件集；再逐文件
比较该文件在 `origin/main` 的当前取值与分支 tip 的取值。

- 分支 tip = `7cf6cf8976faf8496d626cae8e00e8d853424d6e`；
  merge-base = `e9f78ff079817ebcd6154e77e872cefbaf62bf81`（= 该 goal 记录的原 baseline）。
- 自身增量 9 个文件；其中 5 个在 `origin/main` 已同值，4 个仍不同。
- **关键**：这 4 个文件在 **squash 提交 `731c7e6d43f64e4f8e764c67880be6943afcee15`
  （PR #470，单亲，父 = merge-base）** 的取值与分支 tip **逐字节相同**。
  即 PR #470 是 squash 合并，分支内容已完整进入 main；tip 非 main 祖先仅因后续
  `ed36ba45`/`7cf6cf8976` 两个分支侧提交，而这两个提交只改 `.agent` 记录与
  freeze 证据，不产生缺失的产品内容。

4 个仍不同文件及其在 main 上的后续演进（证明“已被取代”而非“丢失”）：

| 文件 | main 上晚于 #470 的改动 |
|---|---|
| `addons/smart_construction_core/views/core/contract_views.xml` | #471、#525 |
| `docs/frontend_productization/rendering-detail/component-driver-takeover-inventory-v1.json` | #525、#526、#527、#533、#543 等 33 次 |
| `docs/ops/iterations/delivery_context_switch_log_v1.md` | 24 次 |
| `frontend/apps/web/src/components/business/MyWorkApprovalWorkspace.vue` | #525（官方模板渲染接管） |

结论：该分支的产品内容**已并入 main 且被后续主线工作取代**，退役不丢失任何未并入内容。

## 本轮改动

1. `.agent/goals/CONTRACT-COLLECTION-WORK-ITEM-READING-EFFICIENCY.yaml`：
   去掉 `baseline.branch` 的实时分支名字面量，改为 `main` + 有日期的退役/取代说明；
   并把该 goal 从 `active` 收敛为 `completed`，附 `closure` 证据块
   （原名保留在 Git 历史与本文档中，不重写提交历史）。
2. `.agent/runs/REMOTE-BRANCH-BACKLOG-RETIREMENT/run.json`：`retained` 只保留
   真实的 8 条，新增 `carrier_referenced_followup` 指向本轮（不含字面量）。
3. 新增受管 manifest：`docs/ops/manifests/historical_branch_retirement_carrier_20261004.json`
   （单条 `reviewed_explicit`）。
4. 新增本轮 goal/run/记录，并把 `.agent/active-runs.json` 绑到本轮分支。

## 执行顺序（fail-closed）

先经普通 PR 车道合并“清载体”候选 → `main` 上不再有该分支名的运行时引用 →
再以 `make branch.retire.historical` 绑定**精确 manifest SHA-256** 与**已验证恢复 bundle**
执行 APPLY。先合并后退役，避免“已删引用但载体清理失败”的不一致状态。

## 证据与绑定

- manifest（受管跟踪）：`docs/ops/manifests/historical_branch_retirement_carrier_20261004.json`
- `manifest_sha256` = `a918d75e4d1fe5ef06f6d8d1149177c675519ff2e84d239cbf869250fe1b8878`
  （目录中保存的即被授权并执行的同一字节内容）
- 恢复 bundle：`.runtime/retire/historical-branch-retirement-carrier-20261004.bundle`
  （`git bundle verify` PASS，`head_count=1`，
  sha256 `a3ab356ba71d2fbe3cb55dba866ea46d081da2a96b94682d41e7fcd6f9411598`）
- 报告（本机 `.runtime/retire/`）：`dry-run-carrier.json`（eligible=1 skipped=0）、
  `bundle-prep-carrier.json`（`bundle_prepared`）、`apply-report-carrier.json`
  （`completed`，1 条 `retired`：`remote_deleted` + `local_absent_confirmed`）、
  `origin-recheck-carrier.txt`
- 目标远端 tip：`7cf6cf8976faf8496d626cae8e00e8d853424d6e`（origin，退役前复读）
- 退役后远端复读：`git ls-remote --heads origin 'refs/heads/codex/*'` = 8 条，
  即“无 exact-head 合并 PR”的 8 条，本轮未动。

## 已执行结果

- L1：`verify.agent.resume.unit` 30、`verify.branch.retire.historical` 30、
  `verify.branch.governance.consistency` 16，全部 passed；`make ci.local.iteration` PASS；
  `make ci.delivery.freeze.prepare` PASS（无生成报告漂移）。
- 索引收口：`.agent/active-runs.json` 已把本轮分支绑定到本轮 run；
  本轮 run 的 `completion` 记录了 manifest/bundle 摘要与 origin 复读计数。

## 未处理（需明确授权）

其余 8 条 origin `codex/*` 的只读判定见本轮 run 的 `completion.read_only_adjudication`，
本轮**不删除**任何一条。
