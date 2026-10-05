# Daily Acceptance Navigation Contract Drift (2026-10-06)

## Trigger

While recording the command-line `DB_NAME` constraint for
`release.daily_dev.acceptance.publish`, the two daily-acceptance ops runbooks
were found to state that the daily product navigation baseline **requires**
`ACCEPTANCE_NAV_MIN_ACTIONS=100` and `ACCEPTANCE_NAV_MAX_ACTIONS=115`.

That statement contradicted the value the acceptance lane actually enforces.

## Facts

| Source | min_actions | max_actions | Role |
| --- | --- | --- | --- |
| `config/frontend/acceptance_environments_v1.json` `profiles.daily.navigation_policy` | 90 | 90 | contract authority |
| `scripts/verify/daily_dev_acceptance_env_guard.py` | 90 | 90 | fail-closed runtime guard (reads the contract) |
| `make/dev.mk` `DAILY_ACCEPTANCE_NAV_MIN/MAX_ACTIONS` | 90 | 90 | derived from the contract |
| `docs/ops/dev_acceptance_release_runbook_v1.md` | 100 | 115 | **stale** |
| `docs/ops/environment_tiers_unified_runbook_v1.md` | 100 | 115 | **stale** |
| `scripts/verify/environment_topology_guard.py` required tokens | 100 | 115 | **stale**, and it kept the stale docs "green" |

The daily matrix observed on `sc-root` at `626836ad` passed with the
contract-derived `90/90` (product menu release gate standard/preview `90/90`,
`DEV_ACCEPTANCE_RELEASE_PROBE` navigation PASS).

## Divergence point

- `401bcb3b` ("feat: establish clean product baseline") introduced
  `ACCEPTANCE_NAV_MAX_ACTIONS=115` into `environment_tiers_unified_runbook_v1.md`.
- `b6b8a0e6` (merge of PR #574) set `profiles.daily.navigation_policy` to
  `min_actions = max_actions = 90` in the contract config.
- PR #574 did **not** update the two runbooks or the topology guard's literal
  tokens, so the documentation and the doc-consistency guard kept pinning the
  pre-#574 `100/115` while the runtime enforced `90/90`.

Because `environment_topology_guard.py` only asserted the presence of the
literal `100/115` strings, `make verify.environment.topology.guard` stayed green
against the stale documentation — the guard was self-consistent with the drift
instead of with the contract.

## Correction

1. Both runbooks now state the contract values `ACCEPTANCE_NAV_MIN_ACTIONS=90`
   and `ACCEPTANCE_NAV_MAX_ACTIONS=90`.
2. `scripts/verify/environment_topology_guard.py` no longer hardcodes the two
   numbers: it derives `ACCEPTANCE_NAV_MIN_ACTIONS` / `ACCEPTANCE_NAV_MAX_ACTIONS`
   from `config/frontend/acceptance_environments_v1.json`
   `profiles.daily.navigation_policy`, so the runbook requirement and the
   contract can no longer diverge silently. If the contract cannot be resolved
   the guard fails closed with an explicit error.

## Boundaries

- The acceptance policy values, gates, thresholds, assertions, fixtures, probe
  and frontend are unchanged; this correction only aligns documentation and a
  doc-consistency guard with the existing contract authority.
- The guard is not weakened: it still requires the tokens to be present in the
  runbook, now with the contract-derived values.
- The daily-server matrix at `626836ad` is reused as-is; no runtime or database
  write happens in this batch.
