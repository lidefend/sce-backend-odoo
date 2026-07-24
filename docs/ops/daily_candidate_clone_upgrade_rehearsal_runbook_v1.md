# Daily Candidate Clone Upgrade Rehearsal Runbook v1

## Purpose and boundary

This runbook governs a real upgrade of an isolated clone restored from the
approved `sc_demo` database/filestore pair. It never upgrades the daily source
database, mounts its filestore into the clone, changes the running daily
repository or containers, or accesses production.

The rehearsal is a P4 delivery proof. It can authorize scheduling a later daily
candidate promotion, but it cannot perform that promotion.

## Candidate freeze is the first gate

No restore, clone container, volume or network may be created until a release
owner supplies one approved candidate declaration. The declaration must bind:

- `candidate_name=RC6`;
- one full 40-character source commit;
- `approval_status=FROZEN`;
- a successful full-CI run URL;
- `ghcr.io/lidefend/sce-product@sha256:<manifest-digest>`;
- the image OCI revision label to the same source commit;
- local image availability and `image_pull_policy=never`;
- ancestry containing the PR #41 and PR #42 merge commits.

An advancing `main`, a branch name, a mutable tag, a local Docker image ID, or
an unapproved commit is not an RC6 candidate.

Run the gate from a clean checkout of the declared candidate:

```bash
ENV=dev \
DAILY_CLONE_RC6_CANDIDATE_MANIFEST=/controlled/rc6-candidate.json \
DAILY_CLONE_RC6_CANDIDATE_REPOSITORY="$PWD" \
make daily.candidate.clone_rehearsal.freeze
```

If the declaration is missing, the result is
`RC6_CANDIDATE_NOT_FROZEN`. This is deliberately before restore or upgrade.

## Fixed source evidence

The versioned contract binds the rehearsal to:

- database `sc_demo`;
- database UUID `c838b4b6-4cd6-11f1-9590-82245e4e7b62`;
- continuity set `sc_demo-20260724T032145Z-6eb277d1`;
- sentinel set `sc_demo-sentinel-20260724T040527Z-1fa42479`;
- sentinel SHA-256
  `1083bae745568fbaef1404c060c76078bec33c4bb7c18a4a9033689c3762257f`;
- fixed repository base `8962c8e0b831c4ac93e15a6d503740113dcd2c57`.

Before an approved rehearsal, revalidate all backup members and checksums,
sentinel evidence, database identity, healthy source containers and the daily
running repository prefix `6095e201`. Record source container identities,
start times and restart counts. All source access is read-only.

## Isolation contract

Every clone resource uses a unique `sc-rc6-rehearsal-*` identity. The clone has:

- independent PostgreSQL and Odoo containers and volumes;
- a copied filestore, session, temporary and log state;
- an internal-only database network and no public egress;
- disabled cron, email, SMS, webhook, payment and object-storage writes;
- no production secret mount;
- no connection to the source database;
- no mount of source database or filestore storage.

The clone is restored only from the fixed backup. Capture and compare the
restored clone against the fixed sentinel before upgrading.

## Migration plan

Generate the deterministic versioned plan from old and target module
inventories before running Odoo. Record module versions, versioned migration
files, model mappings, schema/permission/config/frontend changes, estimated
locks and rollback mode.

The gate rejects:

- `-i` or `--init` module reinstallation;
- demo, fixture or reset paths;
- ad-hoc SQL, database recreation or module uninstall;
- undeclared destructive or irreversible operations;
- deletion of `UNKNOWN_ORIGIN` records;
- deletion of unreferenced filestore objects.

Use `APPLICATION_IMAGE_ROLLBACK` only when all persistent changes are backward
compatible. Otherwise use `PAIRED_DATABASE_FILESTORE_RESTORE`.

## Upgrade, acceptance and recovery sequence

After every preflight passes:

1. restore the fixed pair into the isolated clone;
2. capture and compare the pre-upgrade sentinel;
3. start the immutable RC6 image with pull disabled;
4. execute only the versioned module upgrade entry;
5. capture and strictly compare the post-upgrade sentinel;
6. run real HTTP login, `system.init`, navigation, core-read, role and
   cross-company read-boundary acceptance without business writes;
7. repeat the exact upgrade entry and prove idempotency;
8. capture and compare again;
9. restore the original pair into a second independent clone and prove recovery
   against the pre-upgrade sentinel;
10. atomically publish redacted mode-`0600` evidence;
11. remove only exactly labeled rehearsal resources;
12. prove source daily container/runtime identities and source write counts did
    not change.

Never use an upgraded clone volume as the paired-restore recovery proof.

## Current admission status

RC6 is frozen by `config/releases/rc6_candidate.json` at product source
`fb1f2b5a6e93fb4d7865023e6cda2961848c3cb8` and immutable image manifest
`sha256:02edec2628b276834abd10ec3cc9ef96517fb499c6b0e8a60b19d59e3694fdeb`.
Later delivery-only commits do not change that product candidate.

## Governed remote execution

The daily host has no GHCR credential and the clone network must have no public
egress. Import the already-built candidate without rebuilding or adding tags:

```bash
ENV=dev DAILY_CANDIDATE_SSH_HOST=sc-root \
CONFIRM_RC6_OFFLINE_IMAGE_IMPORT=IMPORT_FROZEN_RC6_IMAGE_OFFLINE \
make daily.candidate.clone_rehearsal.remote_image_import
```

The import archive must contain exactly one image, no `RepoTags`, config digest
`sha256:f468dedc5daf5252f9d7631ee6b31a55a164b97d52f5f0e8b71e46035389e244`,
and the frozen OCI revision. This is the manifest-to-config chain recorded in
the candidate declaration; a classic Docker daemon's local `.Id` is not
compared to the source daemon's `.Id` semantics.

Install the immutable delivery tool and run the read-only preflight:

```bash
ENV=dev DAILY_CANDIDATE_SSH_HOST=sc-root \
make daily.candidate.clone_rehearsal.remote_preflight
```

Only after preflight passes, execute the isolated rehearsal:

```bash
ENV=dev DAILY_CANDIDATE_SSH_HOST=sc-root \
CONFIRM_RC6_DAILY_CLONE_REHEARSAL=RUN_FROZEN_RC6_ISOLATED_CLONE_REHEARSAL \
make daily.candidate.clone_rehearsal.remote_execute
```

The executor restores the fixed pair into isolated volumes, copies the
installed P2 `smart_construction_custom` code from the fixed DAILY Git commit
into a separate read-only customer-addons volume, and never mounts the running
repository. It runs the fixed RC6 product modules plus that unchanged customer
module through the same versioned upgrade entry twice. Internal-only networks
block email, payment, webhook and other external writes. Real-HTTP acceptance
uses the approved DAILY clone identity without persisting or reporting its
secret.

Rollback proof restores the original database and filestore into a second
independent state, copies the old fixed application tree into another isolated
volume, starts the prescribed old application image, and compares the restored
sentinels. All labeled clone resources are removed in `finally`; evidence and
protected logs remain mode `0600`.
