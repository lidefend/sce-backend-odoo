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
- Main base: `05762e9628c6b8c40045f66e5438c5a37d187441`
- Expected catalog: 132 released pages, 46 released scenarios, 10 business centers

## Mainline sync

The initial mixed candidate at `f510eeb8f0344a725e5c800abe9cd6bea1ee9b25`
was split into P0, P1 and P4 responsibility commits before synchronization.
The governed sync replayed those commits onto current `origin/main`
`05762e9628c6b8c40045f66e5438c5a37d187441`, producing candidate
`ad5a07a5d44c91ebce4eee99a9e78b0968e38f7d` plus a metadata-only child
commit. Recovery bundle:

`/home/lidefend/workspace/sce-backend-odoo/.git/codex-recovery/branch-sync/audit-full-center-enablement-walkthrough-20261124-f510eeb8f0344a725e5c800abe9cd6bea1ee9b25.bundle`

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
| P1 runtime | `verify.scene.company_route_scope_cache.orm` via `make ci.local.iteration` | 9 tests PASS |
| Cross-layer | `make ci.local.iteration` | 12 affected targets PASS |
| P4 matrix | `make verify.frontend.business_entry.matrix.incremental` | 132 entries executed; product failures recorded |

Original incremental receipt:

`.runtime/frontend-dev-validation/executions/20261124T010836Z-3353955-611667263/receipt.json`

The receipt binds `ad5a07a5d44c91ebce4eee99a9e78b0968e38f7d` plus the two
metadata-document edits made after synchronization. Those edits do not alter
the checked source or tool inputs.

## Matrix tooling efficiency correction

The first execution strategy was serial and spent 45–75 seconds per failing
entry. The root causes were `networkidle` navigation, fixed post-navigation
sleeps, optional diagnostic `getAttribute` calls with the default 30-second
timeout, and no reuse of the already observed negative-role closure.

The P4 probe now:

- waits for declared surface/error states instead of network idleness;
- bounds every optional diagnostic attribute read;
- exposes per-entry duration;
- partitions the read-only matrix across four independent browser workers;
- forces write-bearing checks to remain serial;
- reuses the bound negative-role closure and skips unrelated candidate logins.

Measured result for the complete 132-entry matrix:

- 4 shards, 33 entries each;
- wall time `10:10:47` → `10:18:07` (7m20s);
- aggregate entry execution 1,568.4s;
- 132/132 entries navigated successfully;
- 20 entries passed the initial surface-level pass.

Evidence:

`.runtime/agent-runs/FULL-CENTER-ENABLEMENT-WALKTHROUGH-20261124/full-matrix-parallel/summary.json`

The initial run used a 12-second surface timeout. Sixty-five entries timed out
without console or response errors. They were re-executed incrementally against
the same source and frontend bundle with a declared 25-second timeout:

`.runtime/agent-runs/FULL-CENTER-ENABLEMENT-WALKTHROUGH-20261124/unknown-presentation-r2/summary.json`

Combined status for the 132 unique entries:

| Status | Count |
| --- | ---: |
| checked | 89 |
| surface-error | 1 |
| scene-error | 19 |
| unknown-presentation | 20 |
| assertion-failed | 3 |

The dominant confirmed failure is relation cell normalization:
`field.project_id.relation_label` appears on 41 entries, with additional
`owner_id`, `company_id`, `user_id`, `partner_id`, `department_id`, `plan_id`,
and related collection cases. A bounded browser capture proved that
`api.data` already returns valid Odoo tuples, for example
`owner_id=[71, "德阳市城市某某建设投资集团有限公司"]`, and the contract declares
both `display_field=owner_id` and `value_field=owner_id`.

The defect therefore belonged to the generic frontend list consumer: it wrapped
an already complete `[id, label]` tuple again as `[[id, label], [id, label]]`.
A second P0 correction preserved Odoo `false`/`null`/`0` relation cells as empty.
The backend relation projection was not missing, and no frontend model-specific
fallback was added.

After both P0 fixes were deployed as `fd87c45cc1d62c4225c06ec71b24d60e4b5fd1f0`
with frontend bundle
`6df74b2fad1176e1f8f66c25dc880842981aadd9028742f765b42a98174b2f82`,
only one relation contract gap remained:

- `field.journal_group_ids.relation_identity`

The other 23 previously affected relation entries no longer failed with
relation-label or many2one-identity errors. Remaining failures are mostly
separate action/view presentation or scene-state gaps.

## Contract V2 strict-decode mainline update

The remaining action/view failures were paused pending the dedicated Contract V2
strict-decode fix. Mainline PR #993 (`193d382c61b12e66a2974bada6fb334f5b9d6417`)
now supplies the canonical `fieldCode`/`fieldType` decoder alignment, monetary
precision retention, legal semantic declaration and attachment-role closure.

The branch was replayed onto this exact mainline by the governed sync entry:

- previous HEAD: `053166bd02bb62be935f3ca991b8d75a3f198e7e`
- new HEAD: `acaee8f4e9868a7b7fcee03065d2fc6c9cb46a6a`
- recovery bundle:
  `/home/lidefend/workspace/sce-backend-odoo/.git/codex-recovery/branch-sync/audit-full-center-enablement-walkthrough-20261124-053166bd02bb62be935f3ca991b8d75a3f198e7e.bundle`

The next runtime pass must rebuild the frontend at the synchronized candidate,
deploy it to `sc-local-dev`, and rerun only entries affected by the strict
descriptor update and the still-open presentation declarations.

The six remaining `unknown-presentation` entries are:

- `smart_construction_core.menu_sc_runtime_user_management`
- `smart_construction_core.menu_sc_plan`
- `smart_construction_core.menu_sc_quality_rectification`
- `smart_construction_core.menu_sc_quality_recheck`
- `smart_construction_core.menu_sc_safety_rectification`
- `smart_construction_core.menu_sc_settlement_order`

The existing P0 test file has two unrelated historical failures. They are not
used as pass evidence and are not modified by this batch; the registered P0
target runs only the landing assertions owned by this change.

## Exclusions

- No daily or production enablement.
- No demo data rebuild.
- No frontend source changes.
- No demo fixture changes.
- No unrelated repair of historical P0 test debt.
