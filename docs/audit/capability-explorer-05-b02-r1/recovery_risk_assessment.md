# Recovery Risk Assessment

Status: `OWNER_AUTHORIZED_REBUILD_COMPLETED`

## Decision

The owner determined that the persistent development database contains only
demo data and directed a rebuild. This supersedes `CAP05-D01` and accepts the
loss of state accumulated after the original recovery point.

The rebuild does not retroactively make the earlier out-of-scope upgrade a
strict isolated acceptance run. It closes the environment-remediation question
by replacing the observed state with a governed demo baseline.

## Pre-Rebuild Data Exposure

The full-table comparison found:

| Group | Inserted | Updated | Deleted |
| --- | ---: | ---: | ---: |
| Module/technical upgrade state | 1,110 | 3,594 | 143 |
| Runtime, message and audit data | 1,157 | 0 | 14 |
| Business or identity data, source unattributed | 783 | 302 | 18 |

A restore of the original recovery point would have removed all 3,050 current
rows absent from that point and reverted 3,896 updates. It would also have
reintroduced 175 rows absent from the current pre-rebuild database.

The 143 technical deletions include 141 `ir_act_window_view` primary-key
rewrites with zero semantic mapping difference. They are not 141 lost business
relationships.

## Preserved Recovery State

A paired pre-rebuild snapshot was created before any destructive operation:

`artifacts/local-dev/snapshots/20261115T163419Z/`

| Artifact | SHA256 |
| --- | --- |
| manifest | `01b836ccea85448cedd00005e2c28b2b30d3fdb6e2e147ea5bd4b4288c0592ca` |
| database dump | `b361b210ba9c7437f46cf5954ccf7cecff680a6cab757f9423ba39ae355b86ff` |
| filestore | `90ae7b1ce8bdb3829ca08e84ff0a370862eaf7662bed1221a2acc70f0e539686` |

The snapshot is outside Git and readable only by the current user. Restoring
it would overwrite the new demo baseline and therefore requires a new explicit
owner authorization. The audit did not restore it.

## Rebuild Result

The governed command
`CONFIRM_LOCAL_DEV_DEMO_REBUILD=REBUILD_CURRENT_FEATURE_DEMO make local.dev.rebuild_demo`
completed with exit code 0.

- project: `sc-local-dev`
- database: `sc_dev_demo`
- dbfilter: `^sc_dev_demo$`
- `smart_construction_core`: `installed / 17.0.0.182`
- public tables: 838
- projects: 26
- construction contracts: 98
- payment requests: 111
- attachments: 930
- `sc_product_scenario`: 17
- `sc_product_scenario_entry`: 78
- `ir_ui_menu`: 720
- `ir_act_window`: 744
- `ir_actions`: 969
- entry identity: `demo / sc_dev_demo / namespace ns_000000000002`
- persistent environment health: `PASS`
- `verify.demo`: `PASS ALL`

## Residual Risk

- Pre-rebuild business and runtime attribution remains unavailable because no
  complete operation log was retained.
- The newly rebuilt demo baseline is not itself a capability acceptance run.
- `CAP05-B01` remains blocked and is unaffected by this rebuild.
- `CAP05-R2` and `CAP05-R3` remain on hold.
- Restoring the pre-rebuild snapshot is destructive to current data and must
  not be performed without explicit owner authorization.
