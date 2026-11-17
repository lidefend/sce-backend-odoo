# FE run binding retirement (2026-11-18)

## Boundary

- Formal Product Layer: P4
- Layer Target: active-run indexing and exact merged-branch retirement
- Module: repository delivery lifecycle
- Standard vs User-Specific: platform standard

PR #923 integrated the frontend feature at source head
`8f121dda0e2fd6642ed6a95df9663ffef5d7724e` into main commit
`43a9b9a4bf6170f8202d6f649799049f80b12189`. PR #922 similarly integrated
the prior cleanup branch at `9fc0202613352423d2187d75828dd09362785464`.

Both branches remain bound in `.agent/active-runs.json`, so the governed
branch cleanup entry correctly refuses to create dangling run state.

## Scope

This batch:

- removes the two stale exact merge bindings;
- registers its own bounded cleanup run;
- permits self-retirement only when the active binding belongs to a bookkeeping
  run whose PR changed only `.agent/` or `docs/` paths and whose exact source
  head is already merged.

The cleanup entry still refuses unmerged branches, protected branches,
non-bookkeeping product bindings, source/remote/main drift and occupied
worktrees. It never deletes worktrees, databases, runtime state or evidence.

## Verification

Verification is recorded in the run's non-zero offline receipts:

- `verify.workspace.worktree.guard`
- `verify.agent.ledger.unit`
- `verify.frontend.dev.incremental.unit`
- `verify.docs.links`

Observed results:

| Check | Result |
| --- | --- |
| focused bookkeeping self-retirement tests | PASS; 3 cases |
| `verify.workspace.worktree.guard` | PASS; 155 tests |
| `verify.agent.ledger.unit` | PASS; 18 tests plus full ledger guard |
| `verify.frontend.dev.incremental.unit` | PASS; 169 tests |
| `verify.docs.links` | PASS; 5 tests plus repository link audit |
| `ci.local.iteration` | PASS; 4 affected targets with non-zero collection |
| `ci.delivery.freeze.prepare` | PASS; generated content-bound evidence is current |

The first increment-planner attempt blocked because the two P4 cleanup paths
had no registered owner. That was a `validation_tool_defect`; the planner now
routes both paths to `verify.workspace.worktree.guard`, with a direct mapping
regression test.

Exact-head publication and remote CI remain pending until the clean candidate
is committed.
