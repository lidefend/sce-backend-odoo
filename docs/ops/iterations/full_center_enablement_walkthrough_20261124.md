# Full Center Enablement and Business Entry Walkthrough

Status: active

## Objective

Enable every released business center for the local demo enterprise and run
the complete declared formal business-entry matrix once, so repeated blockers
are identified from one authoritative inventory rather than discovered one at a
time.

## Layer declaration

| Item | Declaration |
| --- | --- |
| Formal Product Layer | P0 identity + P1 industry landing + P3 runtime configuration + P4 verification |
| Layer Target | Layered landing repair, local demo center activation and the 132-entry acceptance matrix |
| Module | `smart_core`, `smart_construction_core`, `smart_construction_scene`, frontend formal entries, verification scripts |
| Standard vs User-Specific | Local demo enterprise runtime choice |
| Why Here | Landing availability is generic; landing order is industry policy; enablement is enterprise data; execution is verification |
| Why Not Elsewhere | Product source must not permanently activate all centers; frontend must not infer missing enablement or repair contract gaps |
| Blast Radius | Identity landing selection, released landing policy, local company 1 enablement, all declared entries |

## Responsibility split

| Layer | Owned paths | Explicit exclusion |
| --- | --- | --- |
| P0 | `identity_resolver.py` and its focused landing assertions | No construction role names or menu policy |
| P1 | Role landing order, product menu source, locked menu policy, industry contract tests | No generic resolver rewrite or enterprise activation |
| P3 | Local company center/scenario activation | No source or seed change |
| P4 | Run index, batch record, focused test registration and matrix evidence | No product semantics, demo seed or frontend fallback |

## Target

- Project: `sc-local-dev`
- Database: `sc_dev_demo`
- Company: `1`
- Principal: `wutao`
- Role: `business_config_admin`
- Source SHA: `49eaed0281f733d08e1f891324fa0d08cf03fa33`
- Expected catalog: 132 released pages, 46 released scenarios, 10 business centers

## Execution

1. Enable all ten released business centers through
   `scenario.activation.centers.set`.
2. Read back persisted company enablement and navigation.
3. Run the full 132-entry matrix with `SC_ENTRY_SCOPE_FULL=1`.
4. Classify every failure before editing source.

## User-flow blocker 1: completed initialization still landed on setup

After all 46 scenarios were enabled, Workbench was present in navigation, but
the configuration administrator's landing candidates still prioritized
`enterprise.setup`.

Target behavior:

- Before Workbench is enabled, initialization remains the safe landing.
- Once Workbench is enabled and admitted by final route authority, login lands on
  `workspace.home`.
- The Enterprise Initialization menu remains available inside Product
  Configuration for later maintenance.
- A declared platform-safe candidate must not be selected merely by its name;
  it wins only when present in the admitted scene set.

## Layered validation

| Layer | Entrypoint | Result |
| --- | --- | --- |
| P0 | `make verify.identity_resolver.landing.unit` | 2 tests PASS |
| P1 | `make verify.role_surface.landing.contract.unit` | 33 tests PASS |
| P4 planning | `make verify.frontend.dev.incremental.unit` | 237 tests PASS |
| P1 runtime | `make verify.daily.permission_truth.capability.orm` | pending exact-main candidate |
| P4 matrix | `make verify.frontend.business_entry.matrix.incremental` | blocked until exact deployed identity |

The existing P0 test file has two unrelated historical failures. They are not
used as pass evidence and are not modified by this batch; the registered P0
target runs only the landing assertions owned by this change.

## Exclusions

- No daily or production enablement.
- No demo data rebuild.
- No frontend source changes.
- No demo fixture changes.
- No unrelated repair of historical P0 test debt.
