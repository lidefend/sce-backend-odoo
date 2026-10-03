# Gitee formal package refresh and sc-local-dev fixed credential (2026-10-03)

## Objective

- Repoint the governed Gitee formal static package to the current mainline SHA so Gitee
  PR checks stop failing closed on `policy_source_mismatch`.
- Settle the `sc-local-dev` / `sc_dev_demo` demo credential as one fixed, intentionally
  simple value so a developer can log in during repeated verification without reading a
  per-install secret.

## Boundary

- `Formal Product Layer`: P4 (ops delivery tool).
- `Layer Target`: Gitee CI formal package lane (`make gitee.ci.server.update`) and local
  dev lifecycle tooling (`scripts/dev`, `make/dev.mk`).
- `Standard vs User-Specific`: operations delivery standard for the isolated
  `sc-local-dev` profile only.
- `Why Here`: `.env.dev` and `scripts/dev/local_dev_demo_credentials_prepare.sh` already
  own the `sc-local-dev` identity, volume and env-file checks.
- `Why Not Elsewhere`: no product/runtime semantics, so nothing belongs in
  `smart_core` / `smart_construction_*`, the frontend renderer, low-code runtime
  configuration or a migration script.
- `Blast Radius`: only the `smart_construction_demo`-registered demo users inside
  `sc-local-dev` / `sc_dev_demo`. The acceptance fixture, `sc-local-sample`,
  `sc-local-clean`, the contract lifecycle/snapshot environments, production tenants
  and the generic login default are unchanged.

## Gitee formal package refresh

- Mainline identity: `main = origin/main = 17c1a9740b617ee1367d3dbe7634df0dac3d0f0d`,
  tree `0b1de9faa645e9a21549f1e16305811523bf2cfa`, clean.
- Root cause: the worker `GITEE_FORMAL_ROOT` was pinned at the stale package
  `1c89d604...`, so the incremental lane failed closed with `policy_source_mismatch` and
  Gitee PR #34 published zero checks.
- Dry run: `make gitee.ci.server.update EXPECTED_HEAD=17c1a974... GITEE_FORMAL=1
  GITEE_NODE_ARCHIVE=<node-v22.17.0-linux-x64.tar.xz>` produced
  `plan_sha256=e97107e4ad369f125464a35808c1f483d635cd51e60b8b602d698c8baa01d394` with
  `source_sha=17c1a974...`.
- Apply: `APPLY=1 GITEE_UPDATE_PLAN_SHA256=e97107e4... GITEE_UPDATE_CONFIRM=APPLY_REVIEWED_CI_INCREMENTAL_UPDATE`
  returned `status=installed`, `credentials_unchanged=true`, backup
  `/var/lib/gitee-ci/update-backups/incremental-8wr_jba3`.
- Readback: `gitee-webhook-ci.service` and `gitee-ci-worker.service` active;
  `GITEE_CI_MODE=formal-static`; `GITEE_FORMAL_ROOT=/opt/gitee-ci/formal/17c1a9740b617ee1367d3dbe7634df0dac3d0f0d`
  with 16 files; the mirror timer is `inactive`/`disabled`.

## sc-local-dev fixed credential

- `scripts/dev/local_dev_demo_credentials_prepare.sh` declares
  `FIXED_DEV_DEMO_PASSWORD="scdevpass"` and `MODE="${SC_DEV_DEMO_PASSWORD_MODE:-fixed}"`;
  `SC_DEV_DEMO_PASSWORD_MODE=random` restores the per-install `openssl rand -hex 32`
  path and any other value is denied. The existing identity, `0600`, ownership and
  `DB_PASSWORD}`/`JWT_SECRET}` guards are preserved.
- `make/dev.mk` adds `local.dev.demo_users.sync`, which re-applies only `STEPS=demo_users`
  through the governed `scripts/demo/run_seed.sh` so the demo accounts match the
  canonical credential without re-running the whole demo load.
- `docs/ops/local_development_environment_v1.md` records the fixed default, the
  `random` opt-in and the exact scope limits.
- `scripts/verify/test_local_development_lifecycle.py` locks the declaration, the
  default mode, the `sc-local-dev`-only scope and the new sync target behaviour.

## Verification

- `make verify.local.development_lifecycle.unit` -> 16 tests, OK (recorded in the run
  receipt).
- `make local.dev.demo_credentials.prepare` -> `switched canonical demo credential to
  the fixed dev value`; `.env.dev` holds `SC_DEMO_USER_PASSWORD=scdevpass`, mode `0600`.
- `make local.dev.demo_users.sync` -> `[demo.seed] executed=demo_users`.
- Login readback against `http://127.0.0.1:18081` (`sc_dev_demo`, password `scdevpass`):
  `demo_pm` -> 46 `Demo-项目经理`, `demo_finance` -> 47, `demo_cost` -> 48,
  `demo_audit` -> 49, `demo_readonly` -> 50, all PASS. `wutao` and `admin` are not
  `smart_construction_demo` users; they keep their own credentials and this change does
  not alter them.

## Open items

- Gitee main catch-up lane: inspect `make gitee.integration.inspect` and the
  `make main.gitee.catchup` plan anchor before any apply.
- Gitee PR #34 disposition after the package refresh.
