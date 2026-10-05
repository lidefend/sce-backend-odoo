# Daily Acceptance Run Index Closeout (2026-10-06)

## Trigger

PR #584 (the command-line `DB_NAME` constraint plus the navigation
contract-drift correction) squash-merged into `main` at
`f253c4a07751993c5b80e12451e3a066ab1d9b72`.

The merged run record still described itself as `active` and
`.agent/active-runs.json` still mapped
`codex/daily-acceptance-entry-dbname-cli-constraint-v1` to it. Retiring that
branch next would leave a dangling binding in the run index.

## Correction

- `DAILY-ACCEPTANCE-NAV-CONTRACT-DRIFT` run and goal are marked `completed`,
  with the mainline result recorded (PR #584, merge commit `f253c4a0`).
- The retired branch's entry is removed from `.agent/active-runs.json`.
- The still-active `codex/daily-acceptance-lane-selfconsistency-v1` binding is
  preserved.

## Notes

- This is metadata only: no product, contract, gate, threshold, fixture, probe,
  runtime or database behaviour changes.
- The run and goal records stay on `main` as the historical evidence; only their
  status and the index mapping change.
