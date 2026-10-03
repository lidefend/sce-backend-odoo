# Squash-aware branch retirement entry alignment (2026-10-04)

## Purpose

The governed cleanup entries assumed a branch tip becomes an ancestor of `main`
after merge. Under the owner's squash-merge PR rule that is never true: a squash
merge lands a new commit, so the reviewed branch tip is unreachable from `main`.
The effect was a fail-closed-but-unusable gate: `retire_historical_branch_refs.py`
inventoried 287 remote branches as `contained=0`, and `make branch.cleanup` used
`git branch -d` (ancestry only), so no already-merged branch could be retired.

This change aligns both entries with the squash reality **without relaxing any
identity, drift, open-PR, worktree-occupancy or evidence guard**.

## Scope (P4 / ops governance)

- `make/codex.mk`: `branch.cleanup` now delegates to the governed
  `scripts/ops/branch_cleanup_safe.sh` with SHA-bound inputs
  (`EXPECTED_BRANCH_SHA`/`EXPECTED_MAIN_SHA`), a `CLEAN_BRANCH_REMOTE` selector
  and the existing `APPLY`/`CLEAN_BRANCH_CONFIRM` confirmation. Its own `codex/*`
  prefix restriction is preserved (narrower than canonical, never wider).
  `branch.cleanup_safe.sh` already accepts a branch whose tip is contained in the
  bound `main` **or** whose exact head has a merged PR, and still refuses force,
  protected branches, checked-out branches and unreadable remotes.
- `scripts/ops/retire_historical_branch_refs.py`: manifest entries may declare
  `"containment": "reviewed_explicit"` with a `reviewed_explicit` object carrying
  the owner `authorization` and a `YYYY-MM-DD` `reviewed_at`. This replaces
  **only** the ancestry proof; SHA drift, open PRs, checked-out branches,
  runtime carriers, related-work evidence, the manifest SHA-256 binding and the
  recovery-bundle "every declared tip obtainable" requirement all still fail
  closed. Unknown containment modes are rejected.
- `docs/ops/codex_execution_allowlist.md`, `docs/ops/historical_branch_retirement_runbook.md`:
  document the two entries and the `reviewed_explicit` contract.

## Evidence

- `python3 -m unittest scripts.ops.test_retire_historical_branch_refs` → 30/30
  (21 original + 9 new, including a negative baseline that a squash-shaped tip is
  skipped under default `ancestry`, and positive/negative cases proving
  `reviewed_explicit` still skips SHA drift, open PRs, checked-out branches and
  runtime carriers, and rejects missing authorization/date and unknown modes).
- `python3 -m unittest scripts.ops.test_safe_worktree_cleanup` → 115/115
  (adds a recipe assertion that `branch.cleanup` delegates to the governed script
  and contains no `git branch -d`/`git push origin --delete`).
- `scripts/verify/branch_governance_consistency_guard.py` → PASS (canonical regex
  markers and shell guards unchanged).

### Independent review (read-only, separate executor)

Reviewed the frozen candidate against the baseline. Verdict: no guard was
relaxed; the `branch.cleanup` recipe expansion, the `reviewed_explicit`
fail-closed parsing, the non-zero/negative tests and the generated report were
confirmed correct. Findings actioned here:

- Added `docs/engineering_convergence/complexity_budget_report.md` to the run
  `scope`: `ci.delivery.freeze.prepare` regenerates it (line-count reordering),
  and its absence made the run `reconcile`, which would have blocked
  `ci.local.iteration`.
- Fixed a continuation-indent regression in `codex_execution_allowlist.md`
  introduced by this change.
- Documented in the runbook that the merge proof for `reviewed_explicit` is
  supplied externally by the owner and is not re-verified by the tool, so each
  such entry's `evidence` must cite the merged PR number and exact head SHA.

## Status

- Batch: candidate under this branch; see the run record for the current layer.
- No reference was deleted by this change. It only makes the governed entries
  able to express a reviewed squash-merged retirement in a later authorized run.

## Remaining backlog

The ~287-branch remote backlog still needs its own reviewed manifest (each entry
bound to a full SHA and an owner review) before `make branch.retire.historical`
can retire anything. This change removes the structural blocker; it does not
perform the retirement.
