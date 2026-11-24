# Dual-lane fast iteration

Status: active

The backend and frontend lanes use the same cross-layer planner, run record,
target selector and execution receipt store. They only apply different target
scopes.

## Entries

| Entry | Scope |
| --- | --- |
| `make ci.local.backend.iteration` | backend-only plus shared contract/governance targets |
| `make ci.local.frontend.iteration` | frontend-only plus shared contract/governance targets |
| `make ci.local.iteration` | complete cross-layer target set |

The union of the backend and frontend channel target sets must equal the full
iteration target set. Shared targets intentionally appear in both channels.
Unknown paths and full module baselines retain their existing fail-closed and
`deferred_remote` behavior.

## Contract handoff

When the frontend channel contains shared contract targets, it requires a
passed backend channel receipt for the same run, source identity and exact
contract-target set. A failed, incomplete, stale or cross-run backend receipt
cannot be reused. The frontend channel then executes only its frontend-specific
remaining targets.

Frontend changes without shared contract targets can execute directly.

## Execution-path ownership

The planner owns target selection; Make entries only provide the fixed local
preflight and invoke that planner.

| Surface | Local owner | Remote owner |
| --- | --- | --- |
| Demo/product data | Only mapped demo or product targets | Exact affected module/frontend integration |
| Verification-lane audit | Selected only for Make/workflow/registry/planner changes | Required workflow/control-plane gates |
| `make/ci.mk` | Lane policy + planner tests | Full workflow-contract control-plane check |
| Planner-only changes | Planner unit; no unrelated run-context test | Exact-head workflow contract |
| Full lane-coverage receipt | Covers its internal audit subcheck | No local re-execution |

Unknown paths and invalid paths remain fail-closed. A covering receipt is valid
only for the same run and exact source identity.

## Remote precision

The plan and execution receipt include `remoteIntegrationScope`, derived from
the same `config/ci/path_ownership_v1.json` authority used by CI risk
classification and backend impact selection. The projection records whether
the exact-head backend module lane, frontend release lane or control-plane tool
owners are required; it does not choose a second remote scope.

Backend runtime and test-only paths both require the exact-head backend module
integration lane. A test-only change still runs its changed classes locally
through `verify.changed_tests.orm`; the remote planner remains responsible for
the owning module and transitive consumer coverage. Unknown or invalid paths
fail closed.

Remote entries consume exact base/head identities:

- `backend_impact_plan.py` selects modules from the exact Git trees;
- `backend_test_suite.yml` verifies the frozen plan digest and exact HEAD;
- `frontend_release_gate.yml` checks out and re-proves the exact HEAD before
  running the risk-selected lane.

Scheduled release is a separate identity from both the local lanes and the
ordinary PR integration lane. It runs on the same scheduled slot against exact
`main` head/tree: public guard full history scan, professional full, nested
backend full all modules, frontend full release, merge-policy aggregation and
the release-condition artifact. Its result is candidate-build eligibility
only (`deployment_ready=false`); it cannot be reused as a PR's exact-head
integration result, and a local candidate audit cannot be reused as the
scheduled result.

An authorized owner can run the same full main release set outside cron through
`make release.main_full EXPECTED_MAIN=<exact-sha>`. The target dispatches all
five workflows, rejects adopted/old runs, reads back the newly created
`workflow_dispatch` run for each workflow, and waits until all five succeed.
This is `operator_full_audit`, not `scheduled_mainline`; both remain distinct
from PR integration and deployment authority.

Frontend source changes select the full-source systemic static scan through
the planner. It is no longer an unconditional prerequisite of every lane, so a
backend-only iteration does not require an installed frontend toolchain.
Missing `eslint`, `vue-tsc` or `esbuild` blocks only a change set that actually
selects the corresponding frontend targets.

Remote frontend ownership now distinguishes runtime from tooling:

- `frontend_runtime_changed=true` retains standard/full frontend runtime checks;
- tooling-only changes keep `frontend_changed=true` for owner tool checks but
  use `frontend_mode=skip` for the frontend runtime lane;
- a `make/ci.mk` diff may use skip only when all changed bytes are proven to be
  inside `ci.local.iteration`, `ci.local.backend.iteration` and
  `ci.local.frontend.iteration` target blocks, or inside the
  `verify.ci.scheduled_gates` recipe body.

For backend test-only changes, remote `scope_mode=focused` is now effective:
the plan carries exact changed ORM selectors and exact changed pure-Python test
files, and execution is narrowed to the modules that own those changed tests.
Unchanged dependency consumers are not rerun. Production code, test helpers,
deleted tests, mixed changes and missing selector coverage still use the full
impacted-module plan.

## Measured inner loop

On the P4 routing candidate:

| Entry | Measured wall time |
| --- | ---: |
| `make ci.local.iteration` | 4.89-5.03s |
| `make ci.local.backend.iteration` | 5.05s |
| `make ci.local.frontend.iteration` | 4.94s |
| Demo-only fixed prelude | 3.07s |

These measurements are observations, not fixed SLAs. Re-run only the target
whose declared inputs changed.

## Daily order

Backend configuration or contract work:

```text
make ci.local.backend.iteration
```

Frontend work consuming that contract:

```text
make ci.local.frontend.iteration
```

Mixed or final cross-layer review:

```text
make ci.local.iteration
```

Live contract readback, fixture writes, module upgrades and browser acceptance
remain governed operational steps. This lane only chooses and executes the
already-registered local target responsibilities.
