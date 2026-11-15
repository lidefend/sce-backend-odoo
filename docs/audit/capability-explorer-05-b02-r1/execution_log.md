# CAP05-B02-R1 Execution Log

## Identity

- Worktree: `/home/lidefend/workspace/sce-backend-odoo-acceptance-scope-20261109`
- Branch: `audit/capability-explorer-05-b02-r1-20261116`
- Baseline: `96c42ab35550d4807d3bc070e75a06555c57de6f`
- Authoritative remote: `https://github.com/lidefend/sce-backend-odoo.git`
- Persistent runtime: `sc-local-dev / sc_dev_demo / ^sc_dev_demo$`

## Read-Only Recovery-Point Checks

| Check | Result |
| --- | --- |
| Manifest SHA256 | PASS: `bf9db35d4715f656521f9e5964fcdfdb905b3b7820958f5648d561769d08d316` |
| Database dump SHA256 | PASS: `0f416a23009a1e0678fa5e0a71eb19972854112bd112f2525bf03e6a790544b4` |
| Filestore SHA256 | PASS: `90ae7b1ce8bdb3829ca08e84ff0a370862eaf7662bed1221a2acc70f0e539686` |
| Manifest checksum entries | PASS |
| Gzip and tar member safety | PASS |
| `pg_restore --list` | PASS: custom format 1.14, dbname `sc_dev_demo`, 838 table-data entries |

The host has no `pg_restore`; the existing PostgreSQL 15.19 client inside
`sc-local-dev-db-1` read the dump from stdin. It did not connect to or restore
the database.

## Managed Entry Audit

`make local.test.prepare` passed with
`validated registered identity; no runtime writes`.

The available governed entries were reviewed:

- `local.test.*` can create the fixed disposable `sc_test` profile, but has no
  arbitrary snapshot-restore action.
- `local.sample.restore` requires the fixed daily-sample source bundle and
  targets `sc_dev_sample`; it does not accept this recovery point.
- release and acceptance restore entries target unrelated fixed profiles.

No suitable managed disposable restore target exists for this snapshot.
Therefore no temporary database was restored, directly or manually.

## Database Comparison

The authorized dump was streamed through `pg_restore --data-only` and compared
with the current database in one read-only `REPEATABLE READ` transaction. All
838 tables had a primary key and matching column lists. Full rows were reduced
immediately to SHA256 digests; business values were not exported.

Observed transaction start:
`2026-11-15 16:32:39.255418+00`.

Results:

- 3,050 inserted
- 3,896 updated
- 175 deleted
- 89 changed tables

Schema comparison covered tables, views, sequences, columns, inheritance,
defaults, non-constraint indexes and all constraints. No material definition
difference was found. Thirty sequence counters advanced.

## Filestore Comparison

The current filestore was read through the verified `sc-local-dev-odoo-1`
container. All 1,755 files matched the recovery point by relative path, size
and SHA256. All 928 filestore-backed attachment rows matched their physical
SHA1 checksums.

## Owner-Authorized Rebuild

Because the owner confirmed that the environment contains only demo data and
directed a rebuild, a pre-rebuild paired snapshot was created:

`make local.dev.snapshot`

Result: `PASS`, snapshot `20261115T163419Z`.

The rebuild was then executed through the registered entry:

`CONFIRM_LOCAL_DEV_DEMO_REBUILD=REBUILD_CURRENT_FEATURE_DEMO make local.dev.rebuild_demo`

Exact result: exit code `0`.

Observed successful checkpoints:

- database reset: `sc_dev_demo`
- base/bootstrap/product baseline install: PASS
- demo authority verification: PASS
- full release/demo seed: PASS
- Odoo and Nginx recreation and health: PASS
- `[local.env.health] PASS`
- `[local.dev.rebuild] PASS`
- `[verify.demo] PASS ALL on sc_dev_demo`

Post-rebuild read-only identity:

- `smart_construction_core=installed/17.0.0.182`
- `public tables=838`
- `construction_contract=98`
- `project_project=26`
- `payment_request=111`
- `ir_attachment=930`
- `sc_product_scenario=17`
- `sc_product_scenario_entry=78`
- `ir_ui_menu=720`
- `ir_act_window=744`
- `ir_actions=969`

## Non-Result Notes

- An initial `docker inspect --format` probe failed because one mount was a
  bind mount without `.Name`; the corrected inspect was read-only.
- The host lacked `pg_restore`; no package installation was performed.
- An exploratory menu comparison initially compared only the `en_US` scalar
  rather than full translated JSON. It was discarded and corrected to compare
  the complete field.
- An attachment check initially used SHA256 against Odoo's 40-character SHA1
  checksum field. It was corrected to SHA1 and all 928 stored attachments
  matched.

None of these diagnostic corrections changed a persistent database, service
or filestore.
