# Workspace worktree closure: ancestor-integrated retirement (P4)

Run: `.agent/runs/WORKSPACE-WORKTREE-CLOSURE/run.json`
Branch: `fix/workspace-worktree-ancestor-retirement`
Baseline: `08759706b32743bce251473ff2fa1e85a36661b0` (`origin/main`, after PR #535)
Date: 2026-10-02

## Purpose

Whole-workspace cleanup was blocked by a gap in the governed worktree-cleanup entry,
not by a product defect:

- `make workspace.worktree.cleanup` with an archived-evidence receipt requires four
  archived evidence roles (`summary`/`identity`/`screenshot`/`review`). Legacy
  worktrees that never archived delivery evidence have none, and fabricating them is
  prohibited.
- The reviewed legacy-retirement path (record + external recovery bundle) admitted
  only a **squash** integration: a merged PR whose merge commit is a single-parent,
  tree-identical commit on `origin/main`.
- A topic integrated as a **real merge commit** is contained in `origin/main` but has
  no single-parent tree-identical commit, so it satisfied neither path. Its abandoned
  worktree directory therefore had no governed removal route.

## Change

`scripts/ops/safe_worktree_cleanup.py`:

- `prove_integration` keeps the ancestor fast path and now attaches the merged pull
  request of the exact HEAD when one can be read.
- The legacy-retirement path admits both `squash` and `ancestor` integration. An
  ancestor retirement additionally **requires** a verified merged pull request for the
  exact HEAD (otherwise it fails closed), so the reviewed record is still bound to the
  integration it retires.
- Record, bundle hash, remote-lease and destructive-order checks are unchanged.

`docs/ops/codex_execution_allowlist.md` documents the two admission proofs.
`docs/ops/iterations/workspace_worktree_legacy_retirement_v2.json` is the reviewed
record for the two integrated worktrees.

## Retired worktrees

| Worktree | Branch | Head | Integration | PR |
| --- | --- | --- | --- | --- |
| `sce-backend-odoo-contract-l4` | `fix/contract-supply-chain-attestation` | `e18fe9dc4` | squash | #535 |
| `sce-backend-odoo-agent-resume-github-recovery` | `fix/agent-resume-mainline` | `b6ea04f0d` | ancestor (real merge) | #524 |

External recovery bundles (created and `git bundle verify`-checked before the record
was committed):

- `.codex-evidence/workspace-archives/20261002/legacy-worktree-retirement/fix-contract-supply-chain-attestation.bundle`
- `.codex-evidence/workspace-archives/20261002/legacy-worktree-retirement/fix-agent-resume-mainline.bundle`

The live P4 topic `fix/agent-incremental-resume` (`sce-backend-odoo-agent-resume`) is
unmerged and deliberately not listed; it stays as the single platform worktree.

## Boundary

- Formal Product Layer: **P4** ops delivery tool. No P0/P1/P2 semantics, no frontend
  rendering rule, no low-code runtime configuration.
- Blast radius: one cleanup tool, its offline unit locks, one reviewed record and one
  allowlist paragraph. No module, port, volume, database or credential change.

## Results

| Layer | Entry | Result |
| --- | --- | --- |
| L1 | `verify.workspace.worktree.guard` | 92 tests PASS |

Retirement of the two worktrees runs only after this record is committed at the
primary worktree HEAD, i.e. after this candidate is merged.

## Closure outcome (2026-10-02, after PR #536)

PR #536 merged the ancestor admission as squash commit
`4a3d2cd357f3844937aa408456f396d2e8bf713e`, and both recorded integrated worktrees
were retired through `make workspace.worktree.cleanup` with their external recovery
bundles. Live worktrees went from four to one (`sce-backend-odoo-agent-resume`);
`origin/main` and the Gitee mirror main were both realigned to `4a3d2cd35`.

The same pass inventoried every remaining local topic ref and retired the superseded
ones. No ref was retired before proving it is superseded: for each branch, no file
that differs from `main` has a newer commit date on the branch side.

| Branch | Head | Superseded by | Remote |
| --- | --- | --- | --- |
| `fix/contract-slo-telemetry` | `2ad47f83f` | `main` (0 branch-newer files; topic landed via #533/#535) | local only |
| `fix/backend-contract-l4` | `c2410190f` | `main` (0 branch-newer files; topic landed via #533/#535) | local only |
| `fix/daily-official-template-acceptance` | `4ab1b5eab` | `main` `f9d2f1d9f` (identical tree, PR #527) | local only |
| `fix/scheduled-ci-full-lane-recovery` | `a0b793e41` | `main` `84aae65b8` (identical tree, PR #529) | local only |
| `feature/web-official-template-adoption` | `a621a9aca` | #525–#528 (0 branch-newer files) | `origin` at `5dbf6d074` (PR #525 head) |
| `fix/github-history-recovery` | `83ba64063` | ancestor of `main` (PR #523) | `origin` |
| `fix/workspace-worktree-ancestor-retirement` | `c7866f243` | exact-head merged PR #536 | `origin` |

Local refs were removed with `make workspace.branch.discard-local`
(`DISCARD_EXACT_LOCAL_BRANCH_KEEP_RECOVERY`); the two merge-proven refs additionally
had their `origin` branches deleted through `make branch.cleanup.feature` under the
`DELETE_EXACT_REVIEWED_BRANCH` lease. Recovery bundles were created and
`git bundle verify`-checked before each deletion, under
`.codex-evidence/workspace-archives/20261002/branch-retirement/`.

`fix/agent-incremental-resume` (`sce-backend-odoo-agent-resume`, `44429fd70`) is also
superseded — all 320 differing product files are older than `main`, zero newer, and
all 68 of its uniquely-authored product files are likewise superseded — but it is
**retained**. It is not contained in `origin/main` and has no exact-head merged pull
request, so neither the squash nor the ancestor admission applies and it has no
governed retirement path. Removing it requires either integration or a new reviewed
"superseded abandonment" capability; it is not silently dropped here.
