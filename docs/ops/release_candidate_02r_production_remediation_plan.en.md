# RELEASE-CANDIDATE-02R production remediation plan

Chinese version: [release_candidate_02r_production_remediation_plan.md](release_candidate_02r_production_remediation_plan.md)

## Boundary

This plan fixes the order and gates for a later production operation. It does not
authorize or perform a production connection, Git mutation, container change,
database write, backup write, or deployment. The old `rc.1` and its archive,
manifest, scan, and checksums remain read-only evidence and must not be
overwritten, deleted, retagged, or promoted.

The only formal target is:

```text
PRODUCTION_COMPOSE_PROJECT=sc_production
PRODUCTION_DATABASE=sc_production
LEGACY_TARGET=sc_prod (forbidden)
```

## Exact execution package required before approval

The operator must first provide these read-only results. A release owner must
explicitly approve them before a release-window backup may be created:

1. Resolution of the `sc_production` PostgreSQL instance, database, and its one
   corresponding filestore.
2. Current Odoo/Nginx containers, health, immutable image digests, and release
   manifest. A missing manifest requires an independently verifiable replacement
   identity record; a tag cannot be used to infer a digest.
3. The last known-working Odoo/Nginx digest set, manifest, and exact rollback
   Compose inputs.
4. Actual database size, actual filestore size, and backup-target free space. The
   minimum budget is `estimated logical dump + estimated filestore archive + 25%
   verification/temporary margin`, without deleting existing backups.
5. A new restore-point name in the form
   `sc_production-release-<UTC YYYYMMDDTHHMMSSZ>-<first 12 source SHA chars>`.
   Existing directories must not be reused.
6. The complete proposed commands (credential references only), write paths,
   expected duration, and stop conditions.

Neither `.incomplete-*` directories nor the 2026-07-22 historical backup count as
the backup for this release window.

## Execution order after separate production approval

1. Reconfirm `sc_production` as the only target and prove every `sc_prod` input is
   rejected.
2. Diagnose the Odoo/Nginx unhealthy cause without changing versions. Record the
   log window, container digests, configuration references, and read-only health
   probes.
3. Freeze one restore-point window and create a paired set without switching the
   running version: `database.dump`, `filestore.tar.gz`, configuration-reference
   snapshot, current image digests, and the current release manifest (or an
   approved, verifiable replacement identity record).
4. Record SHA-256 checksums, start/end times, database identity, filestore
   ownership, and sizes. Any window or ownership mismatch is BLOCKED.
5. Run a restore drill in an isolated namespace. The restore commands must use a
   new non-production database and isolated filestore and must never overwrite
   `sc_production`.
6. Verify the restored database opens, required tables exist, filestore
   references are readable, and checksums match. Preserve the restore commands
   and the governed isolation cleanup steps.
7. A candidate deployment may be requested only after health diagnosis converges,
   the paired backup is valid, the restore drill passes, and the prior-version
   rollback digest/manifest remains available.

## Subsequent release order

After this PR is merged, lock the new `main` SHA, build `v1.0.0-rc.2`, and run the
complete scan, manifest v2 generation, and artifact identity gate. Production
remediation and backup must be bound to that `rc.2` release window. Until all
gates pass, do not create a Git release tag, switch production Compose, or set
`SC_PRODUCTION_CHANGE_APPROVED`.
