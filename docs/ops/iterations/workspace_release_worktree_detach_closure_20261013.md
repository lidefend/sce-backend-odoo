# Workspace: restore the branch-preserving detach lane for a residual `release/*` worktree (P4)

Run: `.agent/runs/WORKSPACE-RELEASE-WORKTREE-DETACH-CLOSURE/run.json`
Branch: `fix/workspace-release-worktree-detach-closure`
Baseline: `fc4164a5333600aa48836e3dd7a922401c1801f8` (`main` == `origin/main`)
Date: 2026-10-13

## Purpose

One governed ops scaffold, the linked worktree
`sce-backend-odoo-mainmode` (`release/daily-main-mode-20261011` @ `a0afb331`), had no
governed removal route:

- The branch-deleting entry `make workspace.worktree.cleanup` accepts only the ordinary
  topic prefixes `feature|fix|refactor|audit|codex`. `release/*` is **deliberately**
  excluded, because a protected release-line branch must never be deleted by a cleanup
  sweep. That exclusion is intentional and is **not** touched here.
- The branch-preserving detach path (`CLEAN_WORKTREE_KEEP_BRANCH=1`) is documented as
  the route that "only removes the worktree directory and verifies the local branch
  reference is unchanged", so it is the one route that may remove a protected
  `release/*` worktree directory.

PR **#482** (2026-09-16, an unrelated material-form topic) incidentally tightened
`detach_worktree()` to require an archived-evidence receipt and did not update the
allowlist text. Because a protected `release/*` worktree has no branch-deleting cleanup
route, that change removed its only removal channel. This batch restores the documented
contract.

The whole-workspace sweep `make workspace.retain-main-only` is **not** used: three runs
are still registered active/verification_pending in `.agent/active-runs.json`, and a
sweep would destroy their live carrier branches. Scope is limited to removing this one
release worktree while retaining every other branch.

## Change (`P4` ops tool only)

`scripts/ops/safe_worktree_cleanup.py`:

- Documented at `ALLOWED_BRANCH` that the ordinary deletion candidates are the topic
  prefixes only and `release/*` is intentionally excluded (removed only via detach).
- `detach_worktree()` no longer requires a receipt: the retained branch still owns
  every commit and `plan_detach` already pins an exact expected HEAD on a clean,
  non-primary linked worktree. A **supplied** receipt is still verified file-by-file,
  fail-closed.

`scripts/ops/test_safe_worktree_cleanup.py` (offline unit locks):

- `test_detach_without_evidence_receipt_keeps_branch` — `release/*`, no receipt,
  `apply=True`, directory removed, branch reference kept.
- `test_detach_with_mismatched_evidence_receipt_is_still_denied` — a wrong receipt is
  still rejected (`HEAD mismatch`) and the directory survives.
- `test_release_topic_is_not_branch_deleting_cleanup_eligible` — anti-regression:
  `plan_cleanup` rejects `release/*` with `not cleanup-eligible`.

`docs/ops/codex_execution_allowlist.md` — documents the detach no-receipt contract, the
sole-channel rule for `release/*`, and the #482 revision note.

`docs/ops/codex_workspace_execution_rules.md` — states the receipt requirement binds only
the branch-deleting path.

## Boundary

- Formal Product Layer: **P4** ops delivery tool. No P0/P1/P2 product semantics, no
  frontend rendering rule, no low-code runtime configuration, no environment/database/
  credential/fixture authority.
- Blast radius: one cleanup tool, its offline unit suite, two ops docs, and `.agent`
  metadata. Branch-deletion protection is **not** weakened and no gate is relaxed.

## Results

| Layer | Entry | Result |
| --- | --- | --- |
| L1 | `verify.workspace.worktree.guard` | 140 offline tests PASS |
| L1 | `verify.branch.governance.consistency` | PASS |
| L1 | `verify.agent.ledger.unit` | PASS |

## Residual worktrees (not cleaned in this batch)

- The three topic branches carried by the still-registered runs
  (`audit/daily-dev-mainline-product-acceptance-closeout-20261009`,
  `audit/fe-contract-runtime-00-20261012`, `fix/payment-request-chain-alignment-20261013`)
  are live carriers and stay.
- Local branch `audit/daily-dev-full-product-acceptance-20261013` is not in the active
  index and is not an `origin/main` ancestor; its carrier was retired separately and it
  is out of scope here.

## Mainline integration and terminal retirement (2026-10-13)

- The reviewed candidate `7c8e7f4bca75f2c85d351e63462967618fc0950b` merged through the
  protected PR flow: **PR #652**, squash commit
  **`0f13a23878d5996c549476a0c2a232e69c15d18c`**; base `main` advanced from `fc4164a5`.
- Pre-merge binding check: `headRefOid=7c8e7f4b`, `mergeStateStatus=CLEAN`,
  `mergeable=MERGEABLE`, `isDraft=false`. The four required checks
  (`public_guard` / `merge_policy_gate` / `professional_quality_gate` /
  `frontend_release_gate`) all `pass` on the exact head; the merge-lane
  `ci.local.quick` prerequisite **REUSE**d the exact-head receipt
  (`.git/codex/evidence/ci.local.quick/7c8e7f4bca75….json`).
- Post-merge readback: PR `state=MERGED`, `mergedAt=2026-10-13T03:04:30Z`,
  `mergeCommit=0f13a238`; local `main == origin/main == 0f13a238`, worktree clean.
- **Residual removal**: the `sce-backend-odoo-mainmode` worktree directory was removed
  through the restored governed detach entry
  (`make workspace.worktree.cleanup CLEAN_WORKTREE_KEEP_BRANCH=1
  CLEAN_WORKTREE_EXPECTED_HEAD=a0afb331… APPLY=1`). Readback: directory **removed**,
  branch `release/daily-main-mode-20261011` @ `a0afb331` **retained**, and
  `git worktree list` shows only the primary worktree.
- Its ignored `.runtime/final-acceptance/daily-deployed/*.json` were copied
  (non-destructively) to the external workspace archive
  `/home/lidefend/workspace/.codex-evidence/workspace-archives/20261013/main-mode-residual-daily-deployed/`
  before removal:

  | File | SHA256 |
  | --- | --- |
  | `bundle-sync.json` | `e5bd9191de88b87cdad163ab57b73765687041aa8a5f1d8bde7cb31323124075` |
  | `published-face-converge.json` | `8a530b905995d6ff12d810b4be7fa682e45190d2dfb2466033fd0985efea5750` |
  | `source-revision-align.json` | `d5b902d31bf8aee4fa02f9cbe6eb86c6f7d264c9ebf253741a500e98a23d5554` |

  The primary worktree holds newer copies of the same paths; this archive is a
  by-reference snapshot, not a parallel ledger.
- **Terminal retirement**: this goal/run is flipped to `completed`, and
  `.agent/active-runs.json` no longer binds
  `fix/workspace-release-worktree-detach-closure`; no index entry points at the merged
  branch. Per the `pr.merge.local_quick_gate` design, `.agent`/`docs` bookkeeping must
  normally ride with an adjacent product candidate; this topic is substantively
  complete and has **no** adjacent candidate, so it follows the gate's explicit
  instruction (`PR_MERGE_BOOKKEEPING_TERMINAL_RETIRE=<reason>`) with one real
  exact-head Quick for the whole batch.
- Boundary: the merge does **not** trigger a product deployment; no version release or
  product delivery is claimed. The `release/*` branch-deletion protection is unchanged
  and no other registered run or its carrier branch was touched.
