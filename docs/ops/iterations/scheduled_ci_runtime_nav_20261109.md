# SCHEDULED-CI-RUNTIME-NAV-20261109

## Scope

- Formal Product Layer: P4 ops delivery tool.
- Layer Target: scheduled frontend navigation observation.
- Baseline: `346c194e765808727584466d69ab0d2b0605b7b8`.
- No backend menu, ACL, role, product or database changes.

## Root failure

Scheduled `frontend_release_gate` run `42529817408` observed 89 runtime
navigation identities while the static expectation remained at 63. The other
scheduled failures consumed this frontend failure through their fact-check
dependencies.

The static expectation is no longer accepted as the runtime navigation oracle:
runtime navigation is composed from product release, scenes, roles, ACL and
company context. Maintaining a separate hand-written 63/89 set creates a gate
that becomes stale whenever the product evolves.

## Change

- Page identity browser audit continues to inspect every runtime navigation
  surface, including page identity, console errors, HTTP errors, accessibility
  and responsive samples.
- Static expected/missing/unexpected set equality is removed.
- Runtime navigation is still required to be non-empty, structurally valid and
  duplicate-free.
- Release audit and evidence bundle apply the same observation invariants.
- The runtime scene-aware expectation gate remains scheduled for
  `FE-NAV-CAPABILITY-RELEASE-01`.

## Results

Current candidate results:

| Check | Result |
| --- | --- |
| Runtime navigation observation tests | PASS, including duplicate and structural identity rejection |
| Release navigation/release audit | PASS, 16 + 18 + 10 + 31 tests/scenarios |
| Release evidence bundle | PASS, 10 tests |
| Frontend incremental planner | PASS, 94 tests |
| `ci.local.iteration` | PASS, 4/4 affected targets |

The exact logs and hashes are indexed in the run JSON.

The dynamic expected navigation projection remains outside this CI-fix batch.
`FE-NAV-CAPABILITY-RELEASE-01` will replace observation-only validation with a
runtime scene/product expectation and separate actual-vs-expected comparison.
