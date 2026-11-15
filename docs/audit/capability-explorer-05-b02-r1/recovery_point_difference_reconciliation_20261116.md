# CAP05-B02-R1 Recovery-Point Difference Reconciliation

Status: `COMPLETE_FOR_OWNER_REVIEW`

## Scope

This batch compares the authorized `20261115T082948Z` recovery point with the
current persistent `local.dev` database and filestore. It is read-only with
respect to both objects and does not decide whether to restore or accept the
current environment.

## Fixed Identity

| Object | Identity |
| --- | --- |
| Recovery point | `artifacts/local-dev/snapshots/20261115T082948Z/` |
| Source SHA | `d176e2fd67fec87257114b207cec655ec8fa6e9d` |
| Manifest SHA256 | `bf9db35d4715f656521f9e5964fcdfdb905b3b7820958f5648d561769d08d316` |
| Database dump SHA256 | `0f416a23009a1e0678fa5e0a71eb19972854112bd112f2525bf03e6a790544b4` |
| Filestore SHA256 | `90ae7b1ce8bdb3829ca08e84ff0a370862eaf7662bed1221a2acc70f0e539686` |
| Current database | `sc_dev_demo` |
| Current module version | `smart_construction_core 17.0.0.182` |

## Execution Boundary

- The current database, current filestore and recovery point are read-only.
- Odoo must not be restarted and no module upgrade or business write is allowed.
- No restore, overwrite, deletion, table backfill or version forgery is allowed.
- A snapshot copy may be restored only into a separately governed disposable
  comparison environment that is not connected to the persistent service.
- `CAP05-B02` remains `BLOCKED` until the owner reviews this report.

## Results

### Integrity

`PASS`: the manifest, database dump and filestore archive match their fixed
SHA256 identities. The dump is readable as PostgreSQL custom format and the
filestore archive has no unsafe, linked or duplicate members.

### Schema

The recovery point and pre-rebuild database both contain 838 tables, 36 views,
670 sequences, 2,842 non-constraint indexes, 4,625 constraints and 11,285
columns. Normalized index, constraint and column-default definitions have no
differences. PostgreSQL remained at `15.19`. Thirty sequence counters advanced;
their definitions did not change.

### Records

All 838 tables had a primary key and matching column lists. The row-level
comparison found 89 changed tables:

- 3,050 inserted rows
- 3,896 updated rows
- 175 deleted rows

The conservative business/identity group contains 47 tables with 783 inserts,
302 updates and 18 deletes. Their operation type is proven, but source
attribution remains `UNATTRIBUTED` because no complete operation log exists.

`sc_product_scenario` and `sc_product_scenario_entry` are unchanged at 17 and
78 rows. Menu and window-action identities are unchanged; observed changes in
those tables are confined to technical timestamps. Odoo reconstructed 969
`ir_actions` base rows from the same 969 inherited action IDs.

### Filestore

Before the rebuild, all 1,755 files and 52,733,406 bytes matched the recovery
point by path, size and SHA256. All 928 stored attachments matched their
physical SHA1 checksums.

## Owner Remediation

The owner subsequently directed a rebuild because the database contains only
demo data. A paired pre-rebuild snapshot was created at
`artifacts/local-dev/snapshots/20261115T163419Z/`, then the governed
`local.dev.rebuild_demo` entry was executed.

The rebuild, persistent environment health check, entry identity reconciliation
and `verify.demo` all passed. The database now represents a fresh demo baseline.

This closes `CAP05-B02` as owner-authorized remediation by rebuild. It does not
retroactively validate the earlier persistent upgrade as a strict isolated
acceptance operation.

## Stop Boundary

Stop after recording the completed rebuild. `CAP05-B01` remains blocked and
`CAP05-R2`/`CAP05-R3` remain on hold.
