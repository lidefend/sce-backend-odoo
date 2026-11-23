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

Frontend source changes select the full-source systemic static scan through
the planner. It is no longer an unconditional prerequisite of every lane, so a
backend-only iteration does not require an installed frontend toolchain.
Missing `eslint`, `vue-tsc` or `esbuild` blocks only a change set that actually
selects the corresponding frontend targets.

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
