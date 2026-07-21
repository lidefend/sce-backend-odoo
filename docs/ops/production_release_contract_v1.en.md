# Production release contract v1

This document defines build and database lifecycle controls. It is not deployment authorization.

## Immutable image inputs

Production Dockerfiles retain a readable version tag and pin every base image with an immutable `sha256` digest. Production Compose also pins PostgreSQL and Redis by digest. Builds must use the repository commit named by `EXPECTED_RELEASE_SHA`; the resulting OCI revision label must match it.

To update a base image, inspect the official registry manifest, select the digest for the target platform (`linux/amd64` for the current contract), verify `repository:tag@sha256:digest` directly with the registry, then update the reference and run `make verify.production.release_contract` plus the isolated image acceptance. Never derive a production digest only from a mutable tag or local cache. Odoo and PostgreSQL major-version changes require a separate compatibility task.

## Database identities and storage

The formal names are fixed:

- `sc_migration_rehearsal`: disposable migration rehearsal, never production.
- `sc_production`: new formal production database.
- `sc_prod`: archived practice database; it is never a valid initialization or upgrade target.

Each target has dedicated PostgreSQL, Redis, filestore, session, temporary, and log volumes named `sce-<database>-<purpose>`. Rehearsal and production must never share a filestore. A database backup without its matching filestore snapshot is not a complete recovery point.

## Runtime and management separation

Normal container startup is read-only until it proves that an explicitly named database exists and has an installed `base` module. Missing, unreachable, or uninitialized databases stop startup. Normal startup never creates a database, installs modules, upgrades modules, restores data, or loads demo/fixture data.

Database lifecycle commands are deliberately separate:

```sh
TARGET_DB=sc_migration_rehearsal SC_ENVIRONMENT=migration_rehearsal \
EXPECTED_RELEASE_SHA=<40-char-commit> make release.production.db.preflight

TARGET_DB=sc_migration_rehearsal SC_ENVIRONMENT=migration_rehearsal \
EXPECTED_RELEASE_SHA=<40-char-commit> make release.production.db.init

TARGET_DB=sc_migration_rehearsal SC_ENVIRONMENT=migration_rehearsal \
EXPECTED_RELEASE_SHA=<40-char-commit> TARGET_MODULE=smart_construction_core \
make release.production.module.upgrade
```

`init` owns failure compensation only for a database successfully created by that invocation. If the subsequent Odoo `base` initialization fails, the command revalidates the full contract, terminates residual connections to that database, removes only that newly created database, and returns the original initialization status so the same guarded command can be retried. A database that existed before invocation is always rejected and never removed; a pre-creation failure never triggers cleanup. If cleanup itself fails, the command stops with a distinct error and explicitly reports that an orphan database may remain. No general-purpose drop entry is provided.

The corresponding exact volume variables and candidate image must also be supplied. For `sc_production`, initialization or upgrade additionally requires the one-time operator acknowledgement `SC_PRODUCTION_CHANGE_APPROVED=I_ACKNOWLEDGE_SC_PRODUCTION_CHANGE` and an image revision equal to `EXPECTED_RELEASE_SHA`. This acknowledgement is not stored in Compose or source control.

Production sets `list_db = False`, uses an exact `dbfilter`, and fixes `SC_ALLOW_DEMO_DATA=0`. `sc_production` rejects demo/fixture modules even if a caller tries to enable demo data. Database initialization is always `--without-demo=all`.

## Release and rollback boundary

Before any formal initialization or module upgrade, freeze writes and create a verified, paired database-and-filestore backup. Validate its manifest and checksums and complete the separately authorized restore rehearsal. After a module upgrade has written schema or metadata, switching back to the prior image is not a complete rollback: restore the paired database and filestore recovery point according to the approved rollback plan.

This contract does not authorize deployment, server changes, database creation, data migration, attachment archival, or Nginx/TLS changes.
