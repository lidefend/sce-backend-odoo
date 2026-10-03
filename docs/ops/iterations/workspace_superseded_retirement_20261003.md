# Superseded local topic retirement admission (P4)

Run: `.agent/runs/WORKSPACE-SUPERSEDED-RETIREMENT/run.json`
Branch: `fix/workspace-superseded-retirement`
Baseline: `43dec021db191779d1cb2a5d6ba51c74f8c00808` (`origin/main`, after PR #537)
Date: 2026-10-03

## Why

`make workspace.worktree.cleanup` admitted exactly two integration proofs:

- `ancestor`: the worktree HEAD is contained in `origin/main`.
- `squash`: a merged PR for the exact HEAD has a single-parent, tree-identical
  merge commit on `origin/main`.

`fix/agent-incremental-resume` (`sce-backend-odoo-agent-resume`, `44429fd70`)
satisfies neither: it exists only locally, has no merged pull request, and is not an
ancestor of `origin/main`. Its clean linked worktree therefore had no governed
removal route, which kept whole-workspace closure from finishing.

The only other entry able to retire it is `make workspace.retain-main-only`, but that
entry is defined for a pristine whole-workspace cleanup: it deliberately refuses while
*any* worktree, primary included, still holds ignored files, and a unit
(`test_primary_ignored_main_path_preserved_before_worktree_removal`) locks that
refusal. Narrowing that guard would relax an intentional fail-closed policy, so it was
rejected.

## Change

`scripts/ops/safe_worktree_cleanup.py` gains a third, explicitly opted-in admission
for the retirement-record path. Nothing about the ancestor or squash admission changes.

- New CLI flag `--superseded-retirement` (only valid together with
  `--retirement-record` and `--recovery-bundle`).
- New confirmation string `RETIRE_SUPERSEDED_LOCAL_TOPIC_WITH_RECOVERY`.
- `prove_integration(..., allow_superseded=...)` returns `kind="superseded"` only when
  every one of these holds, otherwise it keeps failing closed:
  1. `origin` has **no** `refs/heads/<branch>` (an unreadable `ls-remote` is a denial);
  2. the HEAD is **not** an ancestor of `origin/main`;
  3. for every path that differs from the baseline and exists in the baseline, the
     newest commit touching it from the topic side is **not newer** than the newest
     commit touching it from `origin/main` (zero branch-newer files);
  4. the set of baseline-absent paths (files the topic adds) is returned so the
     reviewed record must enumerate it exactly.
- `make/codex.mk` exposes the lane as `CLEAN_WORKTREE_SUPERSEDED=1` (passed through as
  `--superseded-retirement`); it is mutually exclusive with
  `CLEAN_WORKTREE_KEEP_BRANCH=1`.
- `verify_retirement_record` accepts `integrationKind: "superseded"` entries: it requires
  the `supersededBy` block (`baseline`, empty `branchNewer`, exact `branchAdded`) to
  match the recomputed proof, keeps the `evidenceStatus: "absent"` disclosure, keeps
  the head/tree identity check and keeps the recovery-bundle hash, header and
  `list-heads` verification. Records without an `integration` field keep the legacy
  merged-PR shape, so the previously reviewed record stays valid.
- No remote write happens for a superseded topic: the entry denies if a live
  `origin/<branch>` exists, so the lease-guarded remote deletion is unreachable here.
- The primary worktree and its ignored files are never touched: this path removes one
  clean linked worktree and one local ref.

## Boundary

- Formal Product Layer: **P4** ops delivery tool. No P0/P1/P2 semantics, no frontend
  rendering rule, no low-code runtime configuration, no environment change.
- Blast radius: one cleanup tool, its offline unit locks, one reviewed record and one
  allowlist paragraph.

## Results

| Layer | Entry | Result |
| --- | --- | --- |
| L1 | `python3 -m unittest scripts.ops.test_safe_worktree_cleanup` | passed, 108 tests (was 84) |
| L1 | `make verify.workspace.worktree.guard` | passed, 116 tests |
| L1 | `make ci.local.iteration` | passed (run scope re-declared to include `make/codex.mk`) |

Retirement of the recorded worktree runs only after this candidate merges, through
`make workspace.worktree.cleanup` with the reviewed record and its external recovery
bundle.

## Reviewed record and external recovery

- Record: `docs/ops/iterations/workspace_worktree_superseded_retirement_v1.json`
  (`integrationKind: "superseded"`, `baseline: "origin/main"`, `branchNewer: []`,
  `branchAdded` = `.agent/goals/WEB-OFFICIAL-TEMPLATE.yaml` and
  `.agent/runs/WEB-OFFICIAL-TEMPLATE/run.json`; recomputed from
  `git diff --name-status --no-renames origin/main 44429fd70`, 120 baseline-only paths
  are deletions and are ignored, 425 shared paths have zero branch-newer files).
- Recovery bundle (outside both worktrees, never tracked):
  `/home/lidefend/workspace/.codex-evidence/workspace-archives/20261003/superseded-retirement/fix-agent-incremental-resume.bundle`
  `sha256=efb3332de10638c15ad35cea7d36d10befb2b46610dbc10f63e6018986ca361a`,
  `git bundle verify` reports a complete history and `list-heads` covers
  `44429fd706c065aa0660c4cd87c91c5fba162f1e`.

The bundle is created before the record pins its hash; the record is committed and
merged first, and the actual retirement (`APPLY=1`) runs only afterwards against the
then-current `origin/main`.
