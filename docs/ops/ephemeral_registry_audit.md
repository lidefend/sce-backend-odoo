# Ephemeral Registry Audit Environment

The repository provides a governed, disposable environment for exporting Odoo
registry metadata without connecting to an existing database or Compose
project.

## Isolation contract

- A random `sc-admin-vis-p3-registry-audit-<suffix>` Compose project owns every
  resource.
- PostgreSQL and Odoo use a single internal-only network and publish no ports.
- Database, filestore, session state, and temporary files are held in dedicated
  run-scoped volumes or tmpfs mounts.
- The Odoo container runs with HTTP, cron, workers, demo data, and fixtures
  disabled.
- Source addons are mounted read-only. Audit JSON is written only below
  `/tmp/sc-admin-vis-p3-registry-audit` by default.
- Before Docker can create anything, an atomic two-phase creation manifest
  records every expected resource name. Resource IDs are backfilled after
  creation. Cleanup validates the exact name, recorded ID, task label, and run
  label, and refuses resources outside that manifest.
- Every volume path declared by the selected PostgreSQL and Odoo images must
  have an explicit named, labeled, manifest-tracked Compose mount. Validation
  fails before initialization if an image path would create an anonymous
  volume.

## Governed commands

Run the full lifecycle:

```bash
make admin-vis-p3.registry-audit
```

Use an explicit run identifier for separate steps:

```bash
make admin-vis-p3.registry-audit.validate \
  REGISTRY_AUDIT_RUN_ID=sc-admin-vis-p3-registry-audit-0123456789ab
make admin-vis-p3.registry-audit.export \
  REGISTRY_AUDIT_RUN_ID=sc-admin-vis-p3-registry-audit-0123456789ab
make admin-vis-p3.registry-audit.cleanup \
  REGISTRY_AUDIT_RUN_ID=sc-admin-vis-p3-registry-audit-0123456789ab
```

Run infrastructure checks:

```bash
make verify.admin-vis-p3.registry-audit
```

The runtime audit task must use these Make targets. It must not reproduce their
Docker, Compose, PostgreSQL, or Odoo commands directly.

## Effective generic API policy metadata

The export includes deterministic `generic_api_policies` schema version 2.
It records each effective generic registry key, canonical handler and alias,
model selector, operations, field and method policies, domain/context inputs,
project-context inputs, and the static policy source.

Every runtime model containing a project-context field receives an individual
generic API reachability decision, and every such field receives an individual
read/create/write capability decision. Runtime ACLs, record rules,
company-scoped manual `x_` fields, onchange execution, and button method
callability are not executed. They remain explicit per-policy unresolved
records with their provider, required inputs, affected models, and operations.

The `route_policies` schema version 4 projection first classifies every final
rule as a custom frontend page route, custom frontend backend API, Odoo native
web route, Odoo native RPC, or internal route. Candidate duplicates are then
reconciled against one fingerprinted final routing map using the complete
available Rule match dimensions, dispatch identity, and auth/CSRF/CORS
security metadata.

Controller inheritance or decorator declarations that collapse to one final
Rule are marked `FALSE_CONFLICT` and never enter winner analysis. Only rules
that remain in the same final map with overlapping match dimensions are marked
`TRUE_RUNTIME_CONFLICT`. For those rules only, the exporter may inspect the
actual container-installed Odoo/Werkzeug source and non-request ordering keys.
If that evidence does not prove the exact selection structure, the winner
remains `UNRESOLVED_DYNAMIC`. The exporter never calls `match()`, sends an HTTP
request, invokes a controller endpoint, or executes a business model method.
