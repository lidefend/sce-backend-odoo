# CAP05-B01-R1 Migration Lifecycle Repair

Status: `PENDING_MERGE_DECISION`

## Scope

Repair only the two pre-migration precondition checks:

- `smart_construction_core/migrations/17.0.0.180/pre-migrate.py`
- `smart_construction_core/migrations/17.0.0.181/pre-migrate.py`

The repair distinguishes a valid pre-174 schema from an invalid modern or
unknown-version state. It does not move migration stages, refactor the
migration framework, or modify capability, ACL, scene, release or enterprise
state.

## Research Basis

- Research branch: `audit/capability-explorer-05-b01-migration-20261116`
- Research HEAD: `50a2eb1c2913b62027a990682aa54e45ab9585ad`
- Research tree: `defa41be6082a572e0a7fef69f2aaa528e1783bd`
- Product baseline: `main@96c42ab35550d4807d3bc070e75a06555c57de6f`

## Publication Baseline Sync

After implementation and isolated verification, `main` advanced through
unrelated PR #892 to
`70d01d8fa52c76dc3a296f0431e39be79b98dab5`. The unpublished repair branch was
replayed with the governed `workspace.branch.sync-main` entry using generated
evidence regeneration. The recovery bundle is:

`/home/lidefend/workspace/sce-backend-odoo/.git/codex-recovery/branch-sync/fix-capability-explorer-05-b01-r1-20261116-314ca079cc79bb28d9830a80d3dcad0c03d3600a.bundle`

The sync preserved the repair patch identities, regenerated the overlapping
generated reports, and produced no semantic conflict or remaining merge-tree
conflict against current `origin/main`.

## Tested Source and Final Candidate Identity

- Real isolated upgrade candidate:
  `60906afbfe2763598c70d7115f6753b5112e8a8f`
- Real upgrade candidate tree:
  `74bb881a4c91c68cdccf05536d14b55656280a92`
- Final code/CI candidate before this documentation-only closeout:
  `fe23a66e0dca1aa21066ec834d40da94d6f9f7fc`
- Final code/CI candidate tree:
  `a5acf4b5e7cd25b2868e6afb6d666d6d920ab8d7`
- PR: `#893`

Six of the seven listed source and validation dependencies have identical Git
blob IDs between the tested and final candidates. The only differing blob is
`scripts/verify/frontend_dev_incremental.py`: the governed main sync added
three unrelated frontend-performance paths to an existing rule.

Both historical and final revisions of that verifier were loaded and
`select_targets()` was called for every affected B01 path. The resulting target
sets were identical for all seven paths, including
`verify.smart_construction_core.migration_compatibility.orm`,
`verify.agent.resume.unit`, and `verify.frontend.dev.incremental.unit`.

Therefore the real upgrade evidence remains valid. It is reused on the basis of
byte-identical migration logic, migration tests and upgrade tooling, plus
proven semantic equivalence of the one changed validation-dependency blob.
The complete blob map and comparison are recorded in `migration_matrix.json`.

## Implementation

Both pre-migrations first test for
`public.sc_product_scenario_entry`. If the table exists, the original
operation runs unchanged. If it is absent:

- a recognized version below `17.0.0.174` is a compatible no-op;
- a recognized version at or above `17.0.0.174` raises;
- a missing or unparsable version raises.

Version ordering uses `odoo.tools.parse_version`.

## Verification

Completed against repair HEAD
`60906afbfe2763598c70d7115f6753b5112e8a8f`:

| Check | Result | Evidence |
| --- | --- | --- |
| Focused migration/ORM suite | PASS, 13 tests | `make verify.smart_construction_core.migration_compatibility.orm` |
| Agent ledger | PASS, 18 tests | `make verify.agent.ledger.unit` |
| Direct `172 -> 182` | PASS | `evidence/172-upgrade-both-modules-pass.log.gz` |
| Direct `174 -> 182` | PASS | `evidence/174-upgrade-pass.log.gz` |
| Direct `179 -> 182` | PASS | `evidence/179-upgrade-pass.log.gz` |
| Modern version with absent table | PASS fail-closed | `evidence/negative-modern-missing-table-upgrade-fail.log.gz` |
| Malformed-version branch | PASS unit-only | focused migration/ORM suite |

The complete matrix and database fingerprint deltas are recorded in
`migration_matrix.json` and `upgrade_evidence_20261116.md`.

An initial 172 upgrade invocation selected only `smart_construction_core`.
The repaired migrations completed, but the later current 182 post-migration
failed with `ROUTE_FACT_DECLARATION_FORBIDDEN: sc_web_route` because the
historical `smart_core` module had not also been selected for upgrade. The
successful matrix invocation upgraded both changed modules
(`smart_core,smart_construction_core`) together. This invocation correction is
not classified as a migration-guard failure.

For every successful path, the final database had:

- `smart_construction_core = 17.0.0.182`;
- 17 product scenarios and 78 entries;
- zero bindings for `menu_sc_runtime_user_management`;
- no legacy menu-only unique constraint;
- `UNIQUE (scenario_id, menu_id)`.

The 172 path gained two scene ACLs and one business-scene menu that were
introduced after 172. No existing ACL, Record Rule, Menu, user-company relation
or group membership was lost or changed. Odoo's own
`res_currency.sequence` changed from 1 to 6 during current-data loading; the
company currency relation did not change.

## Negative Verification

A dedicated 174 disposable database was modified so that
`sc_product_scenario_entry` was absent while the installed module version
remained `17.0.0.174`. The upgrade failed explicitly with
`SCENARIO_ENTRY_TABLE_MISSING_INVALID_STATE`, exited with code 2, left the
module at `17.0.0.174 / installed`, left no transient `to upgrade` state, and
did not recreate the table.

Creating an actual database with a malformed version was intentionally not
performed because that would require fabricating `ir_module_module.version`.
That case is `PASS_UNIT_ONLY`, not claimed as a real integration pass.

## Remote CI and Independent Review

PR #893 was based on
`70d01d8fa52c76dc3a296f0431e39be79b98dab5` and passed all four required
workflows at code/CI head
`fe23a66e0dca1aa21066ec834d40da94d6f9f7fc`:

- `public_guard`: SUCCESS
- `merge_policy_gate`: SUCCESS
- `professional_quality_gate`: SUCCESS
- `frontend_release_gate`: SUCCESS

The backend impact suite, including all four backend shards and coverage
verification, also passed. Independent exact-head review concluded `APPROVE`
with no S0-S2 findings.

## Stop Boundary

Current status is `PENDING_MERGE_DECISION`. Deployment and user acceptance were
not performed. This closeout does not authorize or perform merge.
