# Active-run index dangling-binding closeout (2026-10-06)

Run: `ACTIVE-RUN-INDEX-DANGLING-CLOSEOUT`
Branch: `codex/active-run-index-dangling-closeout-20261006`
Baseline: `main` `4b2c37343a92b239f31f55aac3901be211079430` (after PR #582)

## Scope

Metadata only (P4 `engineering_context_run_index`): retire the dangling
`.agent/active-runs.json` bindings so no mapping points at a branch that no
longer exists. No run/goal record, product artifact, contract, database, fixture
or runtime is changed.

## Context

The formal-surface run closeout (PR #582) retired the binding of the merged
`fix/settlement-provenance-entry-creator-v1` branch, but three older pre-existing
bindings still pointed at branches that are absent both locally and on `origin`
(verified with `git ls-remote --exit-code --heads origin <branch>`):

- `codex/daily-dev-user-acceptance-closeout-20261005`
  (`DAILY-DEV-USER-LEVEL-ACCEPTANCE`, run `active`)
- `codex/daily-runtime-candidate-return-v1`
  (`DAILY-RUNTIME-CANDIDATE-RETURN`, run `completed`)
- `codex/remote-branch-backlog-retirement-c-20261005`
  (`REMOTE-BRANCH-BACKLOG-RETIREMENT-C`, run `completed`)

The fourth pre-existing binding is live and is preserved:
`codex/daily-acceptance-lane-selfconsistency-v1` exists on `origin` and its
`DAILY-ACCEPTANCE-LANE-SELFCONSISTENCY` run is still `active`.

A dangling index entry is inert for gate resolution (the resolver looks up only
the current branch), but it is exactly the drift the earlier
`ACTIVE-RUN-INDEX-CLOSEOUT` rounds removed; this batch finishes that cleanup
without touching the referenced run or goal records.

## Changes

- `.agent/active-runs.json`: the three dangling bindings are removed; the one
  live binding is kept.
- The referenced run and goal records are left untouched on `main`.

## Evidence

- Branch absence for the three bindings: `git ls-remote --exit-code --heads
  origin <branch>` returns non-zero (absent) for each, and no local branch
  exists; the live binding's branch is present.
- `make verify.agent.resume.unit` (offline L1).
- `make ci.local.iteration` L1 entry with `outside_scope=[]`.
- No product artifact, contract, database, fixture or runtime is changed.

## Outcome (2026-10-06)

- `.agent/active-runs.json` keeps only the live
  `codex/daily-acceptance-lane-selfconsistency-v1` binding.
- `make verify.agent.resume.unit` passed 30/30.
- `make ci.local.iteration` PASS `change_state=dirty coverage=L1_only` with
  `outside_scope=[]` (log
  `.runtime/agent-runs/ACTIVE-RUN-INDEX-DANGLING-CLOSEOUT/iteration.log`).
- Four-layer status: batch accepted (this metadata change); mainline integration
  pending the ordinary PR lane; deployment `not_run`; product delivery `not_run`.

## Index and freeze order

As in the earlier `ACTIVE-RUN-INDEX-CLOSEOUT` precedent, the index stayed bound
to this closeout branch while the L1 receipts were recorded, and the final commit
removes this batch's own binding too (so that retiring the closeout branch leaves
no dangling mapping). The frozen HEAD then runs one `ci.local.quick` (Quick does
not depend on the run binding); afterwards `make ci.local.iteration` reports
`unregistered`, which is the accepted behaviour documented by that precedent.
