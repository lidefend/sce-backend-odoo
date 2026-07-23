---
capability_stage: P0
status: frozen
since: v0.3.0-stable
---
# Production Command Policy

This policy enforces safe command usage in production. It is enforced by
Makefile guards and script-level guards.

## Allowed (safe)

- `make up/down/logs/ps`
- `make diag.project`
- `make verify.business_system.usability_readiness.prod` (requires `PROD_READONLY_VERIFY=1`)
- `make history.attachment.custody.probe.prod` (requires `PROD_READONLY_VERIFY=1`)
- `make verify.legacy_attachment.mirror.completeness.audit.prod` (requires `PROD_READONLY_VERIFY=1`)
- `make verify.legacy_online_attachment.custody.evidence.prod` (requires `PROD_READONLY_VERIFY=1`)
- `make verify.legacy_online_attachment.mirror.job.audit.prod` (requires `PROD_READONLY_VERIFY=1`)
- `make verify.production_menu.release_gate.guard.prod` (requires `PROD_READONLY_VERIFY=1`)
- `make verify.production_git.authority.guard` (read-only Git/worktree/auth check)
- `make verify.baseline` (requires PROD_DANGER=1)
- `make verify.p0` (requires PROD_DANGER=1)
- `make verify.p0.flow` (requires PROD_DANGER=1)

## Allowed with PROD_DANGER=1 (danger)

- `make mod.install`
- `make mod.upgrade`
- `make restart` (requires PROD_DANGER=1)
- `make prod.restart.safe` (requires PROD_DANGER=1)
- `make prod.restart.full` (requires PROD_DANGER=1)
- `make prod.frontend.build` (requires PROD_DANGER=1)
- `make policy.apply.business_full`
- `make policy.apply.role_matrix`
- `make audit.project.actions`
- `make prod.upgrade.core`
- `make history.production.fresh_init`
- `make release.production.formal_modules.install_missing` (requires the exact
  `CONFIRM_FORMAL_MODULE_INSTALL=YES_INSTALL_MISSING_FORMAL_MODULES` contract;
  loads the root-owned `0600` backup identity only from
  `/etc/scems/production-backup.env`)
- `make release.production.admin_identity.baseline` (defaults to dry-run;
  dry-run establishes and verifies `transaction_read_only=on` before formal
  module, user, role, menu, or product-configuration queries; its atomic,
  redacted evidence separates current state, shared-policy planned state, and
  observed-after state, and records the exact relation plan, zero write audit,
  and stable before/after fingerprints;
  every execution also requires a safe UTC `ADMIN_IDENTITY_RUN_ID`, the exact
  40-character `ADMIN_IDENTITY_TOOL_SOURCE_SHA`, and its matching
  `ADMIN_IDENTITY_DEPLOYED_PATH`; the tool validates the immutable deployment
  marker plus `deployment-tool-metadata.json`, script digest, and
  `make/release.mk` digest before any database query; v3 evidence binds those
  identities, execution timestamps, target fingerprint, and a reproducible
  canonical-payload SHA-256 while the external report separately records the
  complete evidence-file SHA-256;
  apply requires the exact
  `CONFIRM_ADMIN_IDENTITY_BASELINE=YES_APPLY_FRESH_PRODUCTION_ADMIN_IDENTITY_BASELINE`
  contract and may only append the canonical
  `smart_core.group_smart_core_admin` role to the sole active internal
  `admin` in `sc_production`)
- `make legacy_attachment.custody_marker.backfill.prod`
- `make policy.restore.formal_product_menu`
- `make smoke.business_full`
- `make smoke.role_matrix`

## Forbidden in prod (hard stop)

- `make db.reset` / `db.reset.manual`
- `make demo.reset` / `demo.load*` / `demo.rebuild` / `demo.ci` / `demo.full` / `demo.repro` / `demo.verify`
- `make gate.*` / `make gate.audit`
- `make test` / `make test.safe`
- `make ci.*`
- `make verify.ops`
- `make seed.run PROFILE!=base`
- `make seed.run` without `SEED_DB_NAME_EXPLICIT=1`
- `make seed.run` with `SC_BOOTSTRAP_USERS=1` unless `SEED_ALLOW_USERS_BOOTSTRAP=1`
- `make history.continuity.rehearse`
- `make history.continuity.replay`

## Examples

Enable a guarded operation:

```bash
ENV=prod PROD_DANGER=1 make mod.upgrade MODULE=smart_construction_seed DB_NAME=sc_prod
```

Fresh production history initialization:

```bash
ENV=prod ENV_FILE=.env.prod DB_NAME=sc_prod PROD_DANGER=1 \
  RUN_ID=prod_history_init_YYYYMMDDTHHMMSS \
  make history.production.fresh_init
```

Production frontend static rebuild after frontend changes:

```bash
ENV=prod ENV_FILE=.env.prod DB_NAME=sc_prod PROD_DANGER=1 \
  make prod.frontend.build
```

Restore the formal product menu release policy from the locked baseline:

```bash
ENV=prod ENV_FILE=.env.prod DB_NAME=sc_prod PROD_DANGER=1 \
  make policy.restore.formal_product_menu
```

Read-only production business readiness verification:

```bash
ENV=prod ENV_FILE=.env.prod DB_NAME=sc_prod PROD_READONLY_VERIFY=1 \
  make verify.business_system.usability_readiness.prod
```

Read-only production menu release-gate verification:

```bash
ENV=prod ENV_FILE=.env.prod DB_NAME=sc_prod PROD_READONLY_VERIFY=1 \
  make verify.production_menu.release_gate.guard.prod
```

Read-only production attachment custody verification:

```bash
ENV=prod ENV_FILE=.env.prod DB_NAME=sc_prod PROD_READONLY_VERIFY=1 \
  make history.attachment.custody.probe.prod
```

Production attachment custody marker backfill:

```bash
ENV=prod ENV_FILE=.env.prod DB_NAME=sc_prod PROD_DANGER=1 \
  make legacy_attachment.custody_marker.backfill.prod
```

Resume a production history initialization from a replay step:

```bash
ENV=prod ENV_FILE=.env.prod DB_NAME=sc_prod PROD_DANGER=1 \
  RUN_ID=<same_run_id> HISTORY_CONTINUITY_START_AT=<failed_step> \
  make history.production.fresh_init
```

Allow bootstrap users in prod:

```bash
ENV=prod SEED_ALLOW_USERS_BOOTSTRAP=1 SC_BOOTSTRAP_USERS=1 PROFILE=base make seed.run DB_NAME=sc_prod
```

Seed.run in prod must be explicit:

```bash
ENV=prod SEED_DB_NAME_EXPLICIT=1 PROFILE=base DB_NAME=sc_prod make seed.run
```

## Seed users bootstrap prerequisites

- `SC_BOOTSTRAP_USERS=1` requires `SC_BOOTSTRAP_ADMIN_PASSWORD` (or the run will abort).
- Always pass `DB_NAME` explicitly in prod (`SEED_DB_NAME_EXPLICIT=1`).

Blocked demo in prod:

```bash
ENV=prod make demo.reset DB_NAME=sc_demo
```

## Notes

- `ENV=prod` or `ENV_FILE=.env.prod` triggers production guard.
- Guards also apply when scripts are called directly (bypassing Makefile).
- Release checklist: `docs/ops/release_checklist_v0.3.0-stable.md`
