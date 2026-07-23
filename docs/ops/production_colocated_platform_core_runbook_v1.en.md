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

## Governed installation, triple backup, and validation

Do not bootstrap production with direct `scp`, `install`, or `systemctl`
commands. From an approved, clean `main` whose GitHub and Gitee identities
match, run the read-only preflight and then the separately authorized atomic
installer:

```bash
ENV=prod PRODUCTION_COMPOSE_PROJECT=sc_production TARGET_DB=sc_production \
BACKUP_TOOL_SOURCE_SHA=<approved-main-sha> EXPECTED_LIVE_MAIN_SHA=<same-sha> \
BACKUP_ENCRYPTION_STATUS=<verified-policy> BACKUP_RETENTION_DAYS=<days> \
make production.backup.install.preflight

ENV=prod PROD_DANGER=1 PRODUCTION_COMPOSE_PROJECT=sc_production \
TARGET_DB=sc_production BACKUP_TOOL_SOURCE_SHA=<approved-main-sha> \
EXPECTED_LIVE_MAIN_SHA=<same-sha> \
BACKUP_ENCRYPTION_STATUS=<verified-policy> BACKUP_RETENTION_DAYS=<days> \
CONFIRM_BACKUP_TOOL_INSTALL=YES_INSTALL_GOVERNED_BACKUP_TOOL \
make production.backup.install

ENV=prod PROD_DANGER=1 \
CONFIRM_PRODUCTION_BACKUP=YES_CREATE_SC_PRODUCTION_TRIPLE_BACKUP \
make production.backup.run
```

The installer preserves old files, hashes, permissions, and timer state. It
rolls back when offline unit verification fails and keeps the timer stopped
after a successful installation until a manual backup and restore rehearsal
both pass. Every immutable set atomically binds the `sc_production` database,
its filestore, and sanitized deployment metadata. A non-blocking identity lock
rejects concurrent runs; incomplete sets are never valid recovery points.

## Isolated restore drill

The restore entry creates its own internal network, database volume, filestore
volume, and container namespace. It never joins production networks, mounts
production volumes, or connects to production PostgreSQL. Odoo starts with no
egress and zero cron, using `--stop-after-init` as the health gate:

```bash
ENV=prod PROD_DANGER=1 \
BACKUP_DIR=/data/backups/sc_production/<backup-set-id> \
RESTORE_ID=sc_restore_<utc>_<random> \
RESTORE_REPORT=/data/backups/sc_production/restore-rehearsals/<restore-id>.json \
RESTORE_ODOO_IMAGE=<immutable-odoo-digest-ref> \
RESTORE_POSTGRES_IMAGE=<immutable-postgres-digest-ref> \
CONFIRM_RESTORE_REHEARSAL=YES_RUN_ISOLATED_RESTORE_REHEARSAL \
make production.restore.rehearsal
```

The rehearsal compares key table counts, attachment samples, and filestore
digests, and records RTO plus `external_write_side_effects=0`. A failed report
is retained without automatic retry. Cleanup is a separate, explicitly
confirmed operation scoped to resources recorded in the report. Only after
installation, triple backup, and rehearsal all pass may
`production.backup.timer.restore` restore a previously enabled equivalent
schedule. A previously disabled timer requires a separate scheduling decision.

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
