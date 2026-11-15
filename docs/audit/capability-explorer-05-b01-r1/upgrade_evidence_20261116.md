# CAP05-B01-R1 Isolated Upgrade Evidence

Status: `PASS_FOR_REPAIR_HEAD_60906AFB`

## Environment Boundary

- Project: `sc-local-b01-migration`
- Database: `sc_b01_migration`
- Role: dedicated disposable migration-verification database
- `sc_dev_demo`: not used
- B02 recovery point: not restored or modified
- Existing `sc_clean`: not used

The historical starting states were created by checking out the exact historical
commit in the dedicated verification worktree, running the governed
`local.clean.rebuild` entry, and then returning to the repair branch for the
upgrade. The logs and pre/post database fingerprints are archived with this
report.

## Positive Matrix

| Path | Starting state | Result | Scenario rows | Entry rows | Runtime user binding | Unique constraint |
| --- | --- | --- | --- | --- | --- | --- |
| `172 -> 182` | table absent | PASS | 17 | 78 | 0 | `(scenario_id, menu_id)` |
| `174 -> 182` | table present, legacy constraint | PASS | 17 | 78 | 0 | `(scenario_id, menu_id)` |
| `179 -> 182` | table present, legacy constraint | PASS | 17 | 78 | 0 | `(scenario_id, menu_id)` |

In all three paths:

- `smart_construction_core` reached `17.0.0.182 / installed`.
- `smart_core` reached `17.0.1.1.19 / installed`.
- The legacy menu-only unique constraint is absent.
- The runtime user-management menu has no business-scenario binding.
- No ACL, Record Rule, existing Menu, user-company relation or group membership
  was deleted or changed.

The 172 path added the two scene ACLs and the business-scene menu introduced
after 172. Odoo also changed `res_currency.sequence` from 1 to 6 while loading
current module data; the company currency identity remained unchanged. These
facts are recorded as required data refresh, not as zero-diff.

## Focused Test

`make verify.smart_construction_core.migration_compatibility.orm`

- Result: PASS
- Tests: 13
- Identity: `smart_construction_core.tests`
- Coverage includes:
  - versions 172/173 with an absent table are compatible no-ops;
  - modern versions 174/179/180/182 with an absent table fail closed;
  - empty, null, malformed and two-part versions fail closed;
  - existing tables retain the original ALTER/DELETE behavior;
  - a missing runtime-user XMLID does not delete unrelated entries;
  - the runtime user-management menu is not scenario-bound.

## Real Negative Integration

A separate 174 baseline was rebuilt in the dedicated disposable environment.
The scenario-entry table was then removed to create an invalid modern state
without changing the installed module version.

Observed result:

- Upgrade exit code: 2
- Error: `SCENARIO_ENTRY_TABLE_MISSING_INVALID_STATE`
- Module after failure: `17.0.0.174 / installed`
- Transient `to upgrade` rows after failure: 0
- Scenario-entry table after failure: absent

This proves that the fail-closed branch rejects an invalid modern state and does
not advance the module version or leave a transient upgrade state.

## Evidence Accounting

The complete command logs are gzip-compressed under `evidence/`; use
`gzip -dc <file>.log.gz` to read the original bytes. Raw database fingerprint
snapshots are gzip-compressed under `evidence/raw/`; they contain only technical
ACL, rule, menu, company, user-company and group-membership fingerprints and
identities. `SHA256SUMS` records tracked compressed bytes and the SHA256 of each
original uncompressed log and fingerprint.

## Not Verified

- An actual malformed installed-version database was not created. That would
  require fabricating `ir_module_module.version`, which the task explicitly
  prohibited. The branch is covered by focused tests instead.
- Deployment and end-user acceptance are not claimed by this evidence.
