# Daily Customer Addons Runtime Topology Guard — Batch-DCA-1

## Boundary

- Formal Product Layer: P4 operations delivery tool.
- Layer Target: daily-development service topology and release preflight.
- Module: `scripts/verify` and `make/guards.mk`; no Odoo product module changes.
- Why Here: the database can retain an installed customer module while a
  base-compose-only service recreation silently drops its external addon mount.
- Why Not Elsewhere: changing product models, frontend behavior, customer data,
  or the customer package cannot prove the long-running service mount topology.
- Blast Radius: `verify.daily_dev.runtime_repo.clean` and the daily Odoo service
  only. Production, tenant rehearsal, and isolated test projects are unchanged.

## Root cause and correction

- The one-off module upgrade used the customer overlay, but the long-running
  Odoo service had been recreated with only `docker-compose.yml`.
- The database therefore showed customer module metadata while the service
  returned `get_module_path('smart_construction_custom') = False`.
- The service was rebuilt through `make restart` with the repository customer
  overlay. Make now selects that overlay by default whenever the configured
  customer root is present. The new preflight rejects a missing, incorrect, or
  writable mount; non-installed module state; package/database version drift;
  unresolved Odoo module path; or path/version shadowing.

## Validation and rollback

- Unit tests include missing/writable/wrong-source mounts, ambiguous container
  identity, pending state, database/package version drift, unresolved registry
  path, and registry/package version drift negative fixtures. Executable Make
  tests cover base-only default, configured overlay default, and explicit
  `COMPOSE_FILES` override precedence.
- Daily proof must report the read-only customer mount, exact external source
  path, and aligned module versions before release publication.
- Rollback is the source commit only. Do not remove the live customer overlay;
  doing so recreates the defect and is intentionally blocked by the preflight.
