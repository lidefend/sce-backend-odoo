# Daily Candidate Data Continuity Runbook v1

## Environment classification

`sc-backend-odoo-dev` is a `DAILY_CANDIDATE_ENVIRONMENT`. Its `sc_demo`
database and matching filestore contain persistent candidate user data. They
must survive application replacement and must not be treated as disposable
development fixtures.

The authoritative source boundary remains separate:

- approved legacy system: `LEGACY_SOURCE`
- daily `sc_demo` database and filestore: `CANDIDATE`
- isolated acceptance fixtures: `TEST_FIXTURE`
- personal developer databases: `DISPOSABLE`

Application releases and data evolution are governed independently. Images may
be replaced or rolled back. Candidate data may only move forward through a
declared, versioned migration after a clone rehearsal and paired backup.

## Fixed state pair

The versioned contract is
`scripts/ops/daily_candidate_data_continuity_contract_v1.json`. It binds:

- compose project `sc-backend-odoo-dev`
- database `sc_demo` in `sc_dev_db_data`
- filestore `/var/lib/odoo/filestore/sc_demo` in `sc_dev_odoo_data`
- backup root `/data/backups/daily_candidate`

The tool refuses renamed databases, containers, projects, volumes and backup
roots. It never drops the candidate database, uninstalls modules, installs demo
data, resets fixtures, or removes candidate volumes.

The shared destructive targets (`db.reset`, `db.reset.manual`, `demo.reset` and
`db.demo.reset`) also fail before executing when both the compose project is
`sc-backend-odoo-dev` and the target database is `sc_demo`. Destructive local
experiments must use a separately named project and database.

## Read-only baseline

```bash
ENV=dev make daily.candidate.continuity.baseline
```

The baseline records only technical identities, aggregate counts, a small set
of stable numeric record IDs, database UUID and irreversible relation/path/
content digests. It does not emit business field values, credentials or
attachment names.

`ir_attachment` rows can legitimately share one `store_fname`; compare distinct
non-empty `store_fname` values to physical files, not the raw attachment row
count.

## Paired backup

Run from an immutable checkout of the approved tool revision:

```bash
ENV=dev \
CONFIRM_DAILY_CANDIDATE_BACKUP=BACKUP_DAILY_CANDIDATE_PAIRED_STATE \
make daily.candidate.continuity.backup
```

From an approved local branch, install and invoke that immutable tool without
changing the live candidate repository:

```bash
ENV=dev DAILY_CANDIDATE_SSH_HOST=<daily-host> \
make daily.candidate.continuity.remote_baseline

ENV=dev DAILY_CANDIDATE_SSH_HOST=<daily-host> \
CONFIRM_DAILY_CANDIDATE_BACKUP=BACKUP_DAILY_CANDIDATE_PAIRED_STATE \
make daily.candidate.continuity.remote_backup
```

The recovery point contains a PostgreSQL custom dump, matching filestore
archive, manifest and `SHA256SUMS`. It is published atomically with directory
mode `0700` and artifact mode `0600`. The tool captures attachment and filestore
watermarks before and after the operation and refuses publication if that pair
changes during capture. Ordinary non-attachment business activity is not
treated as a failure.

## Validation and isolated restore

```bash
ENV=dev \
DAILY_CONTINUITY_BACKUP_DIR=/data/backups/daily_candidate/<backup-set-id> \
make daily.candidate.continuity.validate

ENV=dev \
DAILY_CONTINUITY_BACKUP_DIR=/data/backups/daily_candidate/<backup-set-id> \
CONFIRM_DAILY_CANDIDATE_RESTORE_DRILL=RESTORE_ISOLATED_COPY \
make daily.candidate.continuity.restore_drill
```

The drill creates uniquely named temporary volumes, an internal-only network
and a PostgreSQL container from the already local image. It restores the dump
and filestore, compares database UUID, aggregate sentinels and filestore
digests, then removes only those uniquely named drill resources. It never joins
the daily candidate network and never touches the source volumes.

After a successful drill, `daily.candidate.continuity.remote_closeout` writes one
redacted, mode-`0600` evidence document below
`/data/backups/daily_candidate/evidence/`. It also proves the source container
IDs/start time are unchanged and no labeled drill resources remain.

## Upgrade gate

Before every candidate application upgrade, record:

```text
DATABASE_MIGRATION_REQUIRED=
MIGRATION_PLAN_VERSIONED=
BACKWARD_COMPATIBILITY=
ROLLBACK_MODE=
FIXTURE_WRITE_ALLOWED=false
DEMO_DATA_WRITE_ALLOWED=false
DATABASE_RECREATE_REQUIRED=false
FILESTORE_RECREATE_REQUIRED=false
PAIRED_BACKUP_SET_ID=
CLONE_REHEARSAL_PASS=
```

If the migration is not backward compatible, image-only rollback is forbidden.
Choose either paired data restoration or a reviewed forward fix before changing
the candidate database.

After upgrade, run both product acceptance and historical-data acceptance:
database UUID, aggregate count floors, selected technical sample IDs and
relations, attachment readability, existing active-user state, company/role
boundaries, and orphan statistics. Do not demand a globally static database
while users and background jobs remain active.

## Duty-scoped recovery points (`daily.runtime.duty.recovery.*`)

A duty is one database with exactly one owner: the platform control plane, the
demo, or one customer development tenant. Each duty needs its own paired
recovery point before its first business-data write.

Identity for these entries has exactly one owner:
`config/ops/daily_runtime_database_duties.v1.json`. The tool derives the
compose project, containers, volumes, application role, filestore scope,
backup namespace and exact database filter from that declaration, and a duty
contract may only carry assertion configuration (sentinel tables, sample
tables, relationship sample, backup-id prefix, task id). A contract that
restates a conflicting identity is refused, so there is no second source of
truth for "which database is this".

The tenant contract is
`scripts/ops/daily_runtime_tenant_recovery_contract_v1.json`, bound to duty
`customer_tenant_dev`. The concrete database, application role, compose project,
routing and backup namespace of that duty come from the duty declaration
(`config/ops/daily_runtime_database_duties.v1.json` plus the managed instance
document under its `ops_root`) and are never restated here: this runbook ships
with the product, and a duty binding belongs to the environment that is being
served. This entry is remote-only: the duty storage namespaces exist on the
daily server, not in the local iteration profile.

```bash
make daily.runtime.duty.recovery.remote_baseline \
  DAILY_CANDIDATE_SSH_HOST=sc-root

make daily.runtime.duty.recovery.remote_backup \
  DAILY_CANDIDATE_SSH_HOST=sc-root \
  CONFIRM_DAILY_CANDIDATE_BACKUP=BACKUP_DAILY_CANDIDATE_PAIRED_STATE

make daily.runtime.duty.recovery.remote_validate \
  DAILY_CANDIDATE_SSH_HOST=sc-root \
  DAILY_DUTY_RECOVERY_BACKUP_DIR=<the duty backup namespace>/<backup set id, as read back from the baseline step>

make daily.runtime.duty.recovery.remote_restore_drill \
  DAILY_CANDIDATE_SSH_HOST=sc-root \
  DAILY_DUTY_RECOVERY_BACKUP_DIR=<the duty backup namespace>/<backup set id, as read back from the baseline step> \
  CONFIRM_DAILY_CANDIDATE_RESTORE_DRILL=RESTORE_ISOLATED_COPY
```

The remote tool tree is installed from one immutable commit, so these targets
refuse a dirty worktree; commit the reviewed tool revision first. The
confirmation tokens are read from the environment, never from stdin. The drill
runs in `sc-daily-continuity-drill-*` temporary resources labeled
`sc.daily-continuity=true`, uses the drill instance's own role, and never
writes to the live duty cluster. This runbook authorizes no write to the live
duty database: capture, validate and drill stay separate steps with their own
exact inputs.
