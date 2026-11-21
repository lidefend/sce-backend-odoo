# Business entry matrix 132 declared surface (2026-11-22)

## Result

The prior acceptance universe contained 91 action-bearing rows plus one
declared scene carrier, for 92 matrix units. The approved product organization
and formal product policy both define 132 released pages.

This batch adds the 40 missing action declarations. The resulting universe is:

- 131 action-bearing CSV rows;
- 1 registered non-action scene carrier;
- 132 total units, exactly matching
  `config/product_scenario_organization_v1.json`.

The 40 added rows are marked `pending`. Existing evidence is not reused for
them, and no runtime page, menu, action, ACL, model, contract, or fixture is
changed.

## Guard

`scripts/verify/business_entry_matrix_universe_guard.py` fails closed when:

- the scenario organization is not 132 pages;
- action rows are not 131;
- the registered scene carrier is not exactly one;
- action and scene carriers overlap;
- any scenario page is missing or any matrix row is undeclared;
- an action row lacks action/model/role authority/rendering metadata;
- the formal product policy no longer declares 132 standard pages.
- the acceptance fixture source no longer declares the same 46 scenario keys.

Run:

```bash
make verify.frontend.business_entry.matrix.universe
```

The incremental planner maps the entire `business_entry_matrix_*` and
`test_business_entry_matrix_*` family to the evidence-scope unit target, so a
new matrix guard cannot fall through as an unmapped verification tool.

Runtime execution remains incremental. The newly added 40 entries are pending
and must be executed against the registered acceptance environment before any
132-page completion claim.

## Validation

- `make verify.frontend.business_entry.matrix.universe`: 5 tests passed.
- `make verify.frontend.role_surface_exposure_declaration.guard`: 10 tests passed.
- `make verify.frontend.business_entry.evidence_scope.unit`: 72 Python tests
  plus route, reuse-identity, observation-binding and namespace cases passed.
- `make ci.local.iteration`: passed with 8 affected targets.
- Read-only matrix scope: `units=132`; 40 added action rows are
  `never_recorded`, not passed.

## Runtime boundary

The acceptance fixture source already declares all 46 current scenario keys,
but `sc_frontend_acceptance` still contains the legacy 17 coarse enablement
keys. Re-freezing the product snapshot does not replay fixture enablement.
Therefore the new 40 pages cannot enter any current role navigation until the
fixture data is reconciled on the exact acceptance database.

That reconciliation is a separate governed fixture write and requires explicit
owner confirmation of the target database, expected inserts, backup, readback
and rollback.

## Narrow reconciliation entry

`make acceptance.frontend.business_scenes.reconcile` defaults to a read-only
plan. The read-only coverage proof shows that the existing 17 legacy scenarios
cover 79 pages, while 22 published current scenarios cover the remaining 53,
including all 40 newly added pages. The two sets are therefore complementary.

The tool only targets local profile database `sc_frontend_acceptance` and:

- preserves all 17 legacy `business.v1:<coarse-key>` enablements for the two
  fixture companies;
- creates or enables only the 22 current scenarios present in the published
  composition, excluding the legacy keys;
- refuses any other enabled key outside that authorized scope;
- requires `APPLY=1` and
  `SC_ACCEPTANCE_BUSINESS_SCENES_CONFIRM=RECONCILE_ACCEPTANCE_BUSINESS_SCENES_132`
  before writing.

### Corrected dry-run

The first proposed migration would have disabled the legacy keys and enabled
all 46 fixture scenario choices. Read-only release evaluation proved it unsafe:
only 22 of the 46 are present in the active published composition. Disabling
the legacy keys would remove the 79 pages they currently carry.

The accepted dry-run plan is:

- preserve all 17 legacy scene enablements;
- insert 22 published current scenario enablements per company;
- 44 planned inserts total;
- 39 enabled scenarios expected per company;
- 17 legacy + 22 current scenario page union = 132.

No database write has been performed for this corrected plan.
