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
- The first full-lane rerun exposed a separate P4 probe defect:
  `frontend_my_work_approval_browser.mjs` recorded transient button geometry,
  exceeding the `playwright_vendor_coupling_guard` baseline of zero. The probe
  now records the public action facts only; the guard baseline was not raised.
- The explicit full local gate exposed two baseline verification defects:
  the Page Contract schema guard omitted the already-declared optional
  `noticeContract` surface, and 43 active guards had no machine-checkable
  wire-or-retire disposition.
- The schema guard now recognizes `noticeContract`; every newly dispositioned
  guard is registered as `file-consumed`, not ignored or retired.
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
| `ci.local.iteration` | PASS, 9/9 affected targets |
| Playwright vendor coupling guard | PASS, baseline unchanged |
| Unified Page Contract v2 schema guard | PASS, 4 tests |
| Guard registry audit | PASS, 24 tests; 212/212 unwired dispositioned |

The exact logs and hashes are indexed in the run JSON.

The dynamic expected navigation projection remains outside this CI-fix batch.
`FE-NAV-CAPABILITY-RELEASE-01` will replace observation-only validation with a
runtime scene/product expectation and separate actual-vs-expected comparison.

The initial manually dispatched full-lane run `42599816709` failed before runtime
evidence generation on the probe geometry guard. That failure is classified as
`validation_tool_defect`, not a navigation or product regression, and the exact
head must be rerun after the probe fix is committed.

The probe fix was then validated by the full affected incremental set:
agent ledger, evidence bundle, navigation policy, standard preview and strict
typecheck all passed. `playwright_vendor_coupling` passed with its baseline
unchanged.

The first complete local run on `5e62e118f` passed 6/8 shards. The two failed
shards were isolated to the schema-guard expectation and guard-registry
disposition defects above. Both owning tools now pass; the complete local gate
must be rerun on the next clean commit before publication.
