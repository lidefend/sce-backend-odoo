# Daily Candidate Data Sentinel Runbook v1

## Purpose and boundary

The daily candidate is a stateful candidate business environment, not a
disposable demo stack and not the production authority. This sentinel records
read-only, repeatable assertions that must survive clone rehearsal and later
candidate upgrades.

It does not update modules, write the database, alter the filestore, change the
running repository, start Odoo from a new image, access production, or classify
unknown records as safe to delete.

## Contract

The versioned contract is
`scripts/ops/daily_candidate_data_sentinel_contract_v1.json`. It fixes:

- environment, database UUID, filestore and continuity-backup identity;
- `MODEL_PRESENT`, `MODEL_ABSENT` and `MODEL_REPLACED_BY` mappings;
- aggregate, required-field, relationship and attachment assertions;
- deterministic sample selection;
- data-origin classification and sensitive-output denylist;
- strict failure, allowed drift and warning semantics.

`UNKNOWN_ORIGIN` is protected. Names containing words such as demo or test are
not sufficient deletion evidence.

## Consistent read

Every capture uses one PostgreSQL `REPEATABLE READ READ ONLY` transaction with a
30-second statement timeout and one-second lock timeout. It creates no table,
index, function or persistent temporary object. Normal global database activity
is recorded separately and is not attributed to this task.

Samples use stable numeric IDs and deterministic company/state partitions.
Evidence may contain technical IDs, relationship IDs/counts, state, active
flags, and amount sign profiles. It must not contain names, logins, contact
details, business text, numeric business amounts, attachment paths, tokens,
cookies or sessions.

## Capture and compare

From an immutable approved tool checkout:

```bash
python3 scripts/ops/daily_candidate_data_sentinel.py capture \
  --output /tmp/daily-candidate-sentinel.json

python3 scripts/ops/daily_candidate_data_sentinel.py compare \
  --baseline /path/to/baseline.json \
  --candidate /path/to/post-upgrade.json
```

Strict comparison fails on lost fixed samples, changed fixed relationships,
increased orphans, newly missing/unreadable attachments, model mapping drift,
company/user identity loss, and unexplained record-count reduction. New records
and ordinary write-date movement are warnings or allowed drift.

## Baseline verification

The governed task entry is:

```bash
ENV=dev \
DAILY_CANDIDATE_SSH_HOST=<daily-host> \
DAILY_CONTINUITY_BACKUP_DIR=/data/backups/daily_candidate/sc_demo-20260724T032145Z-6eb277d1 \
CONFIRM_DAILY_SENTINEL_VERIFY=READ_ONLY_CAPTURE_AND_ISOLATED_RESTORE \
make daily.candidate.sentinel.remote_verify
```

It performs two primary read-only captures, checks deterministic samples,
restores the fixed paired backup into unique temporary volumes and an
internal-only network, captures the restored database and filestore, compares
them in restore-equivalence mode, removes only labeled temporary resources,
and verifies daily container identities/start times/restart counts are
unchanged.

The final evidence is atomically published with mode `0600` below:

```text
/data/backups/daily_candidate/sentinels/<sentinel-set-id>.json
```

The evidence references the paired backup set and has a separately reported
SHA-256. It does not modify the prior continuity manifest or evidence.

Any explicitly named `/tmp/daily-candidate-data-sentinel-<UTC>.json` preflight
capture can be removed through `daily.candidate.sentinel.remote_cleanup_temp`;
the target rejects globs, directories and paths outside that exact namespace.

## RC6 clone upgrade use

For a future RC6 clone rehearsal:

1. restore the same paired backup into an isolated clone;
2. capture the pre-upgrade clone;
3. run only the declared versioned migration on that clone;
4. capture the post-upgrade clone;
5. run strict comparison;
6. treat warnings as reviewable drift and any failure as a promotion blocker;
7. remove the exact clone resources.

Do not upgrade the daily main database until the clone comparison passes.
