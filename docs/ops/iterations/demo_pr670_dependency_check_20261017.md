# Demo line dependency check: PR #670 — 2026-10-17

Read-only check. Nothing was rebased, resolved, pushed, upgraded, seeded or
deployed in this step.

## State read from the platform

- PR #670 `fix(daily-runtime): duty 载体与身份收口，恢复 demo 链与附件连续性语义`,
  state `OPEN`, not draft.
- Head branch `fix/daily-runtime-payload-import-closeout-20261016`, head
  `7eec5f47f8fc4090375331d71bcd4df10b5e604c` (last commit
  `2026-10-17T10:17:30+08:00`).
- `mergeStateStatus = DIRTY`, `mergeable = CONFLICTING`.
- Merge base with `origin/main` is `41c7a9dd4c6a854dc344ca1d7f4033186f66c35a`;
  the branch is 2 commits ahead and 23 commits behind current `origin/main`
  `5dbf503d514040fbfddaddd056cecda7ae460876`.

## Checks

The recorded rollup is 9 success and 3 skipped (`classify`, `fast`,
`wait_for_candidate_checks`), including `merge_policy_gate`,
`professional_quality_gate`, `public_guard` and `frontend_release_gate`.

Those results are bound to the old head and the old base. Because the branch is
23 commits behind and does not merge cleanly, they are not evidence for a merge
of this branch into the current mainline. A fresh run is required after the
branch is synchronised.

## Conflicts

`git merge-tree --write-tree --name-only origin/main <head>` reports exactly two
conflicting paths:

- `docs/engineering_convergence/complexity_budget_report.md`
- `docs/engineering_convergence/split_plan_queue.md`

Both are generated artifacts (`scripts/ci/generate_complexity_budget_report.py`
and `scripts/ci/generate_split_plan_queue.py`, refreshed through
`make refresh.generated_reports`). They must not be hand-merged; synchronise the
branch with main and regenerate.

No product source file conflicts. `.agent/active-runs.json` auto-merges.

## Dependency relation to the merged performance batch

PR #671 was merged into main as `5dbf503d` and changed `app.menu.config`
invalidation plus performance evidence. #670 changes the daily-runtime duty
carrier, demo chain and attachment continuity scripts and does not touch
`app_nav_config.py`. The only shared surface is the generated-report and run
ledger area, which is exactly where the two conflicts sit. #670 therefore does
not depend on #671 semantically; it depends on being resynchronised with main.

## Required sequence before the Demo line can proceed

1. Synchronise `fix/daily-runtime-payload-import-closeout-20261016` with current
   `origin/main`, resolving the two generated reports by regeneration.
2. Re-run the required checks on the new head/base; treat the current rollup as
   stale.
3. Only then run the formal demo seed and representative business loops on
   `local.dev`, using the governed entries (`make local.dev.demo.seed`,
   `local.dev.demo.load`), with the runtime identity re-read first.

Constraint carried forward: no customer data may stand in for the demo dataset,
and the seed must not run against a runtime whose loaded code identity is stale
relative to the candidate under test.
