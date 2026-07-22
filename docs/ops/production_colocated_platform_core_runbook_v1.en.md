# Production Colocated Platform Core Release Runbook v1

Chinese version: [production_colocated_platform_core_runbook_v1.md](production_colocated_platform_core_runbook_v1.md)

## Scope and stop points

This runbook applies only when both the production business and platform databases are `sc_production`. Formal execution requires separate production-change authorization and a new, non-overwriting paired database/filestore backup. R10E validates writes only on an isolated clone.

Never create a production `sc_platform_core`, copy development platform data, insert snapshots directly, read across databases implicitly, switch traffic, or enter R11 automatically.

## Read-only preflight

1. Pin the candidate image digest, Git SHA, `sc_production`, and the formal filestore volume.
2. Set `TARGET_DB=sc_production` and `PLATFORM_RELEASE_DB=sc_production` explicitly in the deployment template.
3. Run `release.production.db.preflight`; environment and `ir.config_parameter.smart_core.platform_release_db` must both equal the current database.
4. Verify read-only that `smart_core` is installed, product policies exist, and record the current snapshot and data baseline.
5. Verify Nginx remains locked to `sc_production` and client database inputs cannot alter registry selection.

## Paired backup and validation

Install `scripts/release/production_colocated_backup.py` and the `deploy/production-backup/` templates through a separately authorized operations change, then run:

```bash
python3 /opt/ops/production_colocated_backup.py backup
python3 /opt/ops/production_colocated_backup.py validate --backup-dir <immutable-backup-directory>
```

The tool rejects targets other than `sc_production`, creates a new timestamped directory without overwriting old backups, and validates database identity, non-empty files, the dump catalog, and SHA-256 checksums. Database and filestore are always paired.

## Isolated restore drill

Restore PostgreSQL and Odoo containers must differ from formal containers. The new database must use the `r10e_restore_*` namespace and must not already exist:

```bash
RESTORE_DB_CONTAINER=<isolated-postgres> \
RESTORE_ODOO_CONTAINER=<isolated-odoo> \
RESTORE_TARGET_DB=r10e_restore_<run_id> \
python3 /opt/ops/production_colocated_backup.py restore-drill \
  --backup-dir <immutable-backup-directory>
```

The drill compares business and `smart_core` platform table counts and source/restored filestore digests. Existing targets, non-isolated containers, or mismatches fail closed.

## Colocation parameter initialization

After a successful backup, write through the governed Odoo configuration model, never direct SQL:

```bash
SC_COLOCATED_PLATFORM_CONFIG_APPLY=I_ACKNOWLEDGE_COLOCATED_PLATFORM_CONFIGURATION \
PLATFORM_RELEASE_DB=sc_production TARGET_DB=sc_production \
make release.production.platform.configure
```

A repeat returns `changed=false`; an existing conflicting value is rejected.

## Active release snapshot initialization

Use only the active, version-controlled `sc.product.policy` in the current database and the existing `EditionReleaseSnapshotService`:

```bash
SC_COLOCATED_PLATFORM_SNAPSHOT_APPLY=I_ACKNOWLEDGE_COLOCATED_PLATFORM_SNAPSHOT_INITIALIZATION \
PLATFORM_RELEASE_DB=sc_production TARGET_DB=sc_production \
PLATFORM_RELEASE_PRODUCT_KEY=<approved-product-key> \
PLATFORM_RELEASE_VERSION=<approved-version> \
make release.production.platform.snapshot.initialize
```

Repeating the same product, version, and policy fingerprint creates no new snapshot. Wrong databases, missing policy, blocked preflight, or configuration conflicts stop execution.

## Acceptance and rollback point

- Run `production_menu_release_gate_guard.py`, all 103 HttpCases, the 45-request database matrix, and `make ci`.
- Confirm only `sc_production` connections, zero `sc_platform_core` or random database connections, and zero unhandled HTTP 500 responses.
- Confirm the active snapshot, policy, login route, attachments, and business counts against approved evidence.
- The rollback point is the immutable paired backup and previous image digest. On failure, stop the candidate and do not switch traffic; any formal restore needs separate authorization and the rehearsed restore path.
