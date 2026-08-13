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
- `make release.production.acceptance.harness` (requires
  `PROD_READONLY_VERIFY=1`, the locked immutable package digest, and one
  credential supplied at execution time; performs only real-HTTP login,
  authenticated reads, and negative authorization checks, without Odoo shell
  or `auth.logout`)
- `make release.production.user_activation.readiness` (requires
  `PROD_READONLY_VERIFY=1`, exact `sc_production` identity, and a new root-only
  evidence path; enables PostgreSQL transaction read-only before querying and
  records only aggregate activation readiness counts and irreversible tenant
  fingerprint evidence, with no login, person, contact, password, token, or
  challenge values)
- `make release.production.user_activation.predeploy.plan` (requires
  `PROD_READONLY_VERIFY=1`, the frozen RC12 deployment identity, immutable
  deployment-tool identity, exact tenant identity, and a new root-only `0600`
  evidence path; establishes PostgreSQL transaction read-only before checking
  installed activation capabilities, public-registration isolation, the
  immutable approved 62-user mapping, the 76-user technical population, the
  14-user approval delta, the two current parameter values, and the singleton
  administrator relation; writes nothing)
- `make release.production.user_activation.predeploy.verify` (requires the
  reviewed root-only plan and exact plan digest; establishes PostgreSQL
  transaction read-only before confirming the two runtime bindings, singleton
  activation administrator, zero credentials, and unchanged ordinary-user
  fingerprint)
- `make release.production.public_signup.close.plan` and
  `make release.production.public_signup.close.verify` (require read-only mode,
  the frozen RC12 and immutable tool identities, and root-only evidence; they
  verify the singleton native signup parameter and create no database writes)
- `make release.production.single_user_activation.plan` and
  `make release.production.single_user_activation.verify` (require read-only
  mode, the frozen RC12 and immutable tool identities, exact `wutao` and
  root-owned runtime tenant bindings, and root-only evidence; they expose no person contact,
  password, activation token, or challenge value)
- `make release.production.promotion.config.preflight` (requires
  `PROD_READONLY_VERIFY=1`, separate governed configuration and secret files,
  and a new `0600` evidence path; validates every promotion field, the fixed
  local image, immutable acceptance package, and current-production HTTP
  acceptance before any application-container replacement)
- `make production.backup.install.preflight` (read-only tool/main/runtime identity check)
- `make verify.baseline` (requires PROD_DANGER=1)
- `make verify.p0` (requires PROD_DANGER=1)
- `make verify.p0.flow` (requires PROD_DANGER=1)

## Allowed with PROD_DANGER=1 (danger)

- `make ops.user.password-reset DB=sc_production LOGIN=<exact-login>` (requires
  a real interactive TTY and execution from an immutable synchronized
  deployment-tool directory; reads the new password twice with `getpass`
  directly from `/dev/tty`, accepts no password through argv, environment,
  stdin, or files, and uses Odoo ORM to change only the unique active internal
  target user's password; the same in-memory password is used once for real
  HTTP login, `system.init`, and one authorized-menu contract verification;
  the launcher reconstructs the one-off Compose context only from allowlisted
  identity fields and mounts of the four running `sc_production` services;
  required infrastructure secrets are inherited in memory from that running
  container rather than stale disk configuration and are never printed;
  the unique selected `res.users` target is bound to a non-secret
  database/model/record digest without depending on an activation external
  identity model or activation runtime parameters;
  role, job, company, menu scope, all other users, login, and business data are
  fingerprinted or statically constrained to remain unchanged)

- `make ops.user.password-verify DB=sc_production LOGIN=<exact-login>` (requires
  a real interactive TTY and the immutable synchronized deployment-tool
  directory; reads the already assigned password once with `getpass`, performs
  only real HTTP login, `system.init`, and one authorized-menu contract read,
  and writes no password, user, role, company, or business record)

- `make release.production.public_signup.close.apply` (requires the reviewed
  root-only plan and exact confirmation; compare-and-set changes only the
  singleton `auth_signup.invitation_scope` row from `b2c` to `b2b`, verifies
  invitation-only policy and unchanged user/activation populations, and may
  not change users, credentials, groups, companies, business data, code,
  images, modules, or services)

- `make release.production.user_activation.predeploy.apply` (requires
  `CONFIRM_USER_ACTIVATION_PREDEPLOY=YES_APPLY_PRODUCTION_USER_ACTIVATION_PREDEPLOY_BASELINE`,
  the reviewed root-only plan and exact plan digest, the frozen RC12 deployment
  and immutable deployment-tool identities; atomically changes at most
  `sc.runtime.tenant_key`, `sc.runtime.environment_type`, and one
  `smart_core.group_smart_core_user_activation_admin` relation for the unique
  active internal `admin`; it issues no credential and cannot write ordinary
  user login, password, roles, company scope, or business data)

- `make release.production.single_user_activation.apply` (requires
  `CONFIRM_SINGLE_USER_ACTIVATION=YES_ACTIVATE_ONLY_WUTAO_IN_PRODUCTION`, a
  reviewed root-only plan and exact digest, the frozen RC12 and immutable tool
  identities; it may set only the two activation runtime bindings, append the
  activation group to the sole internal `admin`, activate only the sole
  internal `wutao` when necessary, create one activation batch and one
  digest-only 24-hour credential, and deliver the plaintext once through the
  registered TLS email channel without recording it in stdout or evidence)

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
- `make production.backup.install` (requires the exact
  `CONFIRM_BACKUP_TOOL_INSTALL=YES_INSTALL_GOVERNED_BACKUP_TOOL` contract;
  atomically installs only the versioned backup/rehearsal tools and units,
  preserves a rollback manifest, validates units before daemon-reload, and
  leaves the timer disabled until backup and restore evidence pass)
- `make release.production.customer_runtime.activate` (requires
  `CONFIRM_PRODUCTION_CUSTOMER_RUNTIME=YES_ACTIVATE_SIGNED_CUSTOMER_RUNTIME`,
  the locked production release set, the exact prepared customer addon set,
  and the frozen `/data/odoo/legacy_attachments/raw_files` plus
  `/data/odoo/legacy_attachments/online_mirror` sources; recreates only the
  production Odoo/nginx runtime with the customer addons and both historical
  binary roots mounted read-only, without copying binaries into the product
  image or product filestore)
- `make release.production.customer_module.upgrade` (requires
  `CONFIRM_PRODUCTION_CUSTOMER_MODULE_UPGRADE=YES_UPGRADE_SIGNED_CUSTOMER_MODULE`,
  the locked production release set, and a target module declared by that
  release set; upgrades only the selected prepared P2 customer module through
  the immutable production database-management entrypoint)
- `make production.backup.run` (requires
  `CONFIRM_PRODUCTION_BACKUP=YES_CREATE_SC_PRODUCTION_TRIPLE_BACKUP`; creates
  one immutable database/filestore/sanitized-metadata backup set)
- `make production.restore.tool.sync` (requires
  `CONFIRM_PRODUCTION_RESTORE_TOOL_SYNC=YES_SYNC_GOVERNED_RESTORE_TOOL`; from
  a clean dual-remote-approved `main`, synchronizes only
  `/opt/ops/production_backup_restore.py` to `sc-prod` under a nonblocking
  lock, preserves a root-only rollback copy, atomically replaces the file,
  and verifies the installed SHA-256 without changing application services,
  systemd, containers, volumes, or databases)
- `make production.candidate.image.sync` (requires
  `CONFIRM_PRODUCTION_IMAGE_SYNC=YES_SYNC_VERIFIED_CANDIDATE_IMAGE`; from a
  clean dual-remote-approved `main`, verifies the governed candidate archive
  SHA-256, local OCI manifest ID, and every archive blob digest; it incrementally
  synchronizes only changed OCI blobs to the fixed `sc-prod` digest cache using
  checksum comparison and a previous-layout link base, resolves the published registry digest, and verifies
  that both the archive tag and immutable digest reference map to the exact
  backend-portable remote config ID;
  it creates no remote staging file and does not change services, containers,
  volumes, systemd, or databases)
- `make production.candidate.manifest.sync` (requires
  `CONFIRM_PRODUCTION_CANDIDATE_MANIFEST_SYNC=YES_SYNC_VERIFIED_CANDIDATE_MANIFESTS`;
  from a clean dual-remote-approved `main`, validates the secure manifest set's
  source SHA, version, GHCR digest refs, and checksum, then atomically creates
  one new immutable `/opt/sce/candidates/v<version>` directory on `sc-prod`;
  an existing differing target fails closed and no runtime resource changes)
- `make production.deployment.tool.sync` (requires
  `CONFIRM_PRODUCTION_DEPLOYMENT_TOOL_SYNC=YES_SYNC_IMMUTABLE_DEPLOYMENT_TOOLING`;
  streams the exact clean dual-remote-approved main Git archive into one new
  atomic `/opt/sce/deployment-tools/<sha>` directory without runtime changes)
- `make production.attachment_preview.csp.apply` (requires
  `CONFIRM_PRODUCTION_ATTACHMENT_PREVIEW_CSP=YES_ADMIT_SAME_ORIGIN_BLOB_ATTACHMENT_PREVIEWS`,
  an immutable deployment-tool SHA, a new root-only evidence directory, and
  the production HTTPS base URL; changes only the exact frozen edge CSP by
  adding `frame-src 'self' blob:`, validates and reloads nginx, verifies the
  public response header, and restores the captured config on any failure)
- `make production.tenant.delivery.artifacts.sync` (requires
  `CONFIRM_PRODUCTION_TENANT_ARTIFACT_SYNC=YES_SYNC_SIGNED_TENANT_DELIVERY_ARTIFACTS`;
  from a clean dual-remote-approved `main`, validates and incrementally
  synchronizes one signed customer package, signed tenant payload, and public
  key into a new root-owned production custody directory, then generates the
  bound release-set lock with the immutable deployment tool; it changes no
  database, service, container, product image, product filestore, or historical
  attachment binary)
- `make production.customer.runtime.config.promote` (requires
  `CONFIRM_PRODUCTION_CUSTOMER_RUNTIME_CONFIG_PROMOTE=PROMOTE_VERIFIED_PRODUCTION_CUSTOMER_RUNTIME_CONFIG`;
  after signed P2 preparation, module upgrade, and runtime activation, verifies
  the immutable release set and the live `/mnt/customer-addons` mount, then
  atomically advances only `SC_CUSTOMER_ADDONS_ROOT` with a root-only rollback
  copy and evidence; it changes no database, product identity, image, service,
  filestore, payload, or historical attachment binary)
- `make production.release.config.promote` (requires
  `CONFIRM_PRODUCTION_RELEASE_CONFIG_PROMOTE=YES_PROMOTE_VERIFIED_PRODUCTION_RELEASE_CONFIG`;
  verifies the current running image, current runtime identity, next cached
  image ID, and next manifests, then atomically advances only the allowlisted
  runtime/promotion identity keys with paired rollback copies; it does not
  replace containers, start services, or connect to a database)
- `make production.restore.rehearsal` (requires
  `CONFIRM_RESTORE_REHEARSAL=YES_RUN_ISOLATED_RESTORE_REHEARSAL`; restores only
  into an internal-network rehearsal namespace)
- `make production.restore.cancel` (requires
  `CONFIRM_PRODUCTION_RESTORE_CANCEL=YES_CANCEL_SCOPED_RESTORE_REHEARSAL`;
  from a clean dual-remote-approved `main`, terminates only the single active
  restore process and descendants whose exact restore ID and retained PLANNED
  report match, using SIGTERM only; it does not remove resources or touch
  production services or databases)
- `make production.restore.cleanup` (requires
  `CONFIRM_RESTORE_CLEANUP=YES_CLEANUP_SCOPED_RESTORE_RESOURCES`; removes only
  resources recorded in one retained rehearsal report)
- `make production.backup.timer.restore` (requires
  `CONFIRM_BACKUP_TIMER_RESTORE=YES_RESTORE_VERIFIED_BACKUP_TIMER`; restores
  the previously enabled schedule only after paired backup and restore PASS)
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
