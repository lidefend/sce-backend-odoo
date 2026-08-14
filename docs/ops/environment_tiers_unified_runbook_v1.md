# Environment Tiers Unified Runbook v1

## Scope

This runbook unifies four frontend acceptance profiles while preserving the
three deployment tiers:

- Local development (`local`)
- Isolated test / CI (`test`)
- Daily development server (`daily`)
- Production safe smoke (`production`)

It is the single command policy for environment setup, script usage, and Makefile entrypoints.

Frontend acceptance distinguishes the runner from the target. A developer or
CI runner may connect to an external daily target without acquiring authority
to start or stop that target. `managed` targets must be loopback; `external`
targets must never be managed by an audit script.

The versioned policy is
`config/frontend/acceptance_environments_v1.json`; tool applicability is
`config/frontend/acceptance_tool_matrix_v1.json`. The canonical resolver uses
this precedence:

```text
CLI > SC_ACCEPTANCE_* > compatibility environment aliases > profile > safe default
```

Conflicting aliases fail. Daily and production targets require an explicit URL,
a full expected source SHA, and matching served runtime identity. Production
only permits `production-safe-smoke`; form and configuration writes only permit
the isolated local/test fixture database.

Each run receives an independent artifact directory keyed by profile, SHA,
tool, and run id. Cross-worktree leases live below `XDG_RUNTIME_DIR` (or the
system temporary directory), not in a worktree. Read-only tools share a target
lease; write-capable and managed-service tools take an exclusive lease. A
managed service uses a dynamic port and may terminate only a process whose
recorded PID, start time, and command identity still match.

## Layer Target / Module / Reason

- Layer Target: `Governance Layer (Ops/Execution Policy)`
- Module: `Makefile + env governance + runbook`
- Reason: prevent mis-execution caused by mixed DB knobs and non-standard command paths before formal deployment.

## Single Source of Truth

1. Environment variables must come from `.env.<tier>` or explicit CLI override.
2. Canonical database knob is `DB_NAME`.
3. Compatibility aliases:
- `DB` is accepted.
- `BD` is legacy only.
4. Priority is fixed:
- `DB_NAME` > `DB` > `BD` > default value.

## Tier Profiles

| Tier | ENV | ENV_FILE | DB baseline | Usage |
| --- | --- | --- | --- | --- |
| Daily dev | `dev` | `.env.dev` | `sc_demo` | Day-to-day feature work, replay rehearsal |
| Test dedicated | `test` | `.env.test` | `sc_test` | CI-like gates, strict verification |
| Production | `prod` | `.env.prod` | `sc_prod` | Formal deployment only, guarded operations |

## Runtime Topology

| Tier | Host alias | Runtime path | ENV | ENV_FILE | DB_NAME |
| --- | --- | --- | --- | --- | --- |
| Daily dev | `sc-root` | `/opt/projects/repos/sce-product-odoo` | `dev` | `.env.dev` | `sc_demo` |
| Production | `sc-prod` | `/opt/sce/production/sce-product-odoo` | `prod` | `.env.prod` | `sc_prod` |

The daily development runtime repository is the only deployable `dev` working tree.
It may run `main` or one explicitly approved governed branch candidate at an
immutable detached SHA. Daily candidate acceptance happens before merge to
`main`; production authority is unchanged.
Before publishing or upgrading it, run `make verify.daily_dev.runtime_repo.clean`
inside `/opt/projects/repos/sce-product-odoo`.
Daily acceptance publication must use `make release.daily_dev.acceptance.publish`
from that same runtime repository.
That target only accepts `ENV=dev`, `ENV_FILE=.env.dev`, and `DB_NAME=sc_demo`;
it also requires `ACCEPTANCE_BASE_URL=http://127.0.0.1:18081` and
`ACCEPTANCE_LOGIN=wutao`, a non-empty `ACCEPTANCE_PASSWORD`, and
`ACCEPTANCE_NAV_MIN_ACTIONS=100`, `ACCEPTANCE_NAV_MAX_ACTIONS=115`, and
`ACCEPTANCE_NAV_FORBIDDEN_LABELS=用户核对菜单,用户数据验收,用户验收,直营项目系统菜单`.
`ACCEPTANCE_NAV_REQUIRED_PATHS` must include the locked daily product path
sample covering customer, supplier, project ledger, general contract,
construction diary, inbound, payment request, project capital overview, payroll,
company archive, and input invoice entries.
`ACCEPTANCE_NAV_REQUIRED_ACTIONS` must pin that same sample to locked runtime
action ids.
`ACCEPTANCE_PROBE_OUTPUT=artifacts/backend/dev_acceptance_release_probe.json`.
The frontend build output must stay `FRONTEND_DIST_DIR=./frontend/apps/web/dist-dev`,
and `VITE_ODOO_DB`, `VITE_APP_ENV`, `VITE_BUILD_MODE`, and
`VITE_BUILD_OUT_DIR` must not be overridden. `VITE_PLATFORM_ADMIN_DB` must stay
`sc_platform_core`, and `VITE_API_BASE_URL`, `VITE_API_PROXY_TARGET`,
`VITE_ODOO_DB_LOCKED`, `VITE_DELIVERY_MODE`, `VITE_FEATURE_FLAGS`,
`VITE_LITE_CONTRACT_PILOT`, `VITE_LITE_CONTRACT_ROLLOUT`, and `VITE_TENANT`
must stay unset. Wrong DB, tier, served URL, evidence
path, or frontend build/runtime override parameters must fail before frontend
build or acceptance probes run.

Production code authority is `main` or a frozen release package applied under `/opt/sce/production/sce-product-odoo`.
If production is a Git working tree, run `make verify.production_git.authority.guard` before upgrade.
Do not deploy from scratch worktrees or archived runtime directories.

## Mandatory Preflight

Always run before operations:

```bash
make environment.capability.inventory
make env.matrix.check
```

The inventory is a fail-closed reuse decision, not an environment setup step.
P0-P3 product topics consume the listed governed entries and must not invent a
Compose project, port, database, volume, filestore, fixture identity, or
temporary environment file. Only an explicitly scoped P4 environment topic may
change topology, and only after this inventory proves the required capability
is absent. A missing local `.env` in a topic worktree is not such proof; the
managed acceptance resolver deliberately consumes the primary worktree's
credential authority.

The frontend release workflow is an existing governed exception to the local
fixed topology: GitHub Actions creates a per-run `sc-fe-release-${GITHUB_RUN_ID}`
Compose project and a mode-`0600` `RUNNER_TEMP` environment file. The same
`make db.frontend.acceptance.ensure` entry validates repository, workspace,
checkout SHA, run ID, database/filter and three per-run volume identities before
using that workflow-owned environment. It must not be redirected to `.env.dev`
or to the local fixed acceptance project.

This command checks:

- `.env.dev/.env.test/.env.prod` presence and required keys
- three-tier env validation via `check-compose-env`
- DB knob precedence (`DB_NAME`, `DB`, `BD`) to avoid wrong-database execution
- runtime topology policy for daily development and production

## Standard Command Entry

Use Makefile only for runtime-changing actions:

- container lifecycle: `make up/down/restart/logs/ps`
- DB reset / seed / demo: `make db.reset`, `make seed.run`, `make demo.*`
- module install/upgrade: `make mod.install`, `make mod.upgrade`
- verifications/gates: `make verify.*`, `make gate.*`

## Managed Frontend Acceptance Runtime

The local managed frontend acceptance runtime is a complete versioned identity,
not merely a database name. Its authority is
`config/frontend/acceptance_environments_v1.json` under
`profiles.local.managed_runtime`. The contract locks all of the following as
one lifecycle unit:

- database `sc_frontend_acceptance` and exact filter
  `^sc_frontend_acceptance$`;
- Compose project, PostgreSQL volume, Redis volume, and Odoo filestore volume;
- the existing Odoo container that owns the database credentials and filestore;
- backend port `18082`, frontend port `5175`, and frontend process identity;
- the candidate worktree source mount and served source SHA.

The primary worktree `.env.dev` remains the secret source. Non-secret runtime
topology always comes from the versioned acceptance profile and has higher
precedence than `.env.dev`. `scripts/common/env.sh` preserves these explicit
topology overrides when lower-level scripts load the base environment again.

Use only these entries for the managed acceptance lifecycle:

```bash
make acceptance.runtime.preflight
make acceptance.runtime.infrastructure.restore
make backend.acceptance.up
make frontend.acceptance.up
make acceptance.frontend.fixture
make acceptance.baseline.upgrade \
  CODEX_NEED_UPGRADE=1 \
  CODEX_MODULES=smart_core,smart_construction_core
make acceptance.module.upgrade \
  MODULE=smart_construction_core \
  CODEX_NEED_UPGRADE=1 \
  CODEX_MODULES=smart_construction_core
```

`acceptance.runtime.preflight` is mandatory before every managed write. It
fails closed if the database/filter, any named volume, the mounted database or
Redis volume, the credential authority, or the Odoo filestore differs from the
profile. `acceptance.runtime.infrastructure.restore` only reconnects the
already-declared managed volumes; it does not create a database or fixture.
For a recovered or version-lagged acceptance database,
`acceptance.baseline.upgrade` fixes the dependency order to `smart_core` first
and `smart_construction_core` second. The single-module target is reserved for
incremental upgrades whose dependency baseline is already current.

Database architecture declaration for this profile:

```text
TARGET_DATABASE_ROLE=isolated_acceptance_fixture_database
TARGET_TENANT_ID=platform_internal_acceptance
TARGET_ENVIRONMENT_ID=frontend_acceptance_local
IS_PLATFORM_CONTROL_DATABASE=false
IS_INDUSTRY_CATALOG_DATABASE=false
IS_CUSTOMER_TENANT_DATABASE=false
IS_ISOLATED_REHEARSAL_DATABASE=true
CUSTOMER_BUSINESS_DATA_ALLOWED=false
FIXTURE_ALLOWED=true
EXACT_DATABASE_FILTER_CONFIRMED=true
FILESTORE_IDENTITY_CONFIRMED=true
```

## Forbidden Usage

Do not use ad-hoc direct commands for state mutation:

- direct `docker compose exec ...` for core flows that already have Make targets
- direct SQL mutation outside governed scripts
- mixed DB knobs in one command (for example setting both `DB_NAME` and `DB` with conflicting values)

## Canonical Usage Examples

Daily:

```bash
ENV=dev ENV_FILE=.env.dev DB_NAME=sc_demo make seed.run
```

Test:

```bash
ENV=test ENV_FILE=.env.test DB_NAME=sc_test make verify.restricted
```

Production (guarded):

```bash
ENV=prod ENV_FILE=.env.prod DB_NAME=sc_prod make verify.prod.guard
```

## Daily Acceptance and Merge-to-main Gate

Daily development candidate order is fixed:

1. Complete local gates on a clean governed branch and commit the candidate.
2. Deploy that exact branch SHA with `make daily.runtime.candidate.bundle_sync`
   (or an equivalent governed fetch path).
3. Run `make release.daily_dev.acceptance.publish` in candidate mode and obtain
   owner acceptance.
4. Only then open/update the PR and merge to protected `main`.

Daily acceptance is evidence for merge readiness, not production authorization.

Before integrating to `main`, required minimum:

1. `make env.matrix.check`
2. required verification bundle for this batch (at least restricted gate)
3. run controlled merge path only (`make codex.merge`) after explicit approval

If any check fails, stop integration and fix environment policy drift first.
