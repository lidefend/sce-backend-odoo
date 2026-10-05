# Daily Acceptance Entry: Command-Line DB_NAME Constraint (2026-10-06)

## Trigger

While running the daily composite acceptance matrix on the daily development
server (`sc-root`) at mainline `626836ad`, the first invocation failed
`env.matrix.check` with:

```
❌ [env.matrix.check] DB alias broken: expected sc_matrix_alias got 'sc_demo'
```

The failure was reproduced and isolated to the invocation, not to the product,
the target's gates, or the acceptance assertions.

## Fact / Evidence (A/B/C)

Same repository, same `HEAD`, same `.env.dev`, only the `DB_NAME` input changed:

| Case | Invocation | Result |
| --- | --- | --- |
| A | `make env.matrix.check ENV=dev ENV_FILE=.env.dev` | EXIT=0, `✅ [env.matrix.check] PASS` |
| B | `make env.matrix.check ENV=dev ENV_FILE=.env.dev DB_NAME=sc_demo` | EXIT=2, `DB alias broken: expected sc_matrix_alias got 'sc_demo'` |
| C | `export DB_NAME=sc_demo; make env.matrix.check ENV=dev ENV_FILE=.env.dev` | EXIT=0, `✅ [env.matrix.check] PASS` |

So the breaking input is specifically **`DB_NAME` as a make command-line
variable**; the `.env.dev` value and an exported environment variable are both
accepted.

## Why

`env.matrix.check` (`make/guards.mk`) probes DB-name precedence by invoking a
sub-make:

```
$(MAKE) --no-print-directory -s DB=sc_matrix_alias env.print.db
```

`Makefile` resolves `DB_NAME` with priority `DB_NAME > DB > BD > default`. A
command-line `DB_NAME` is propagated to sub-makes through `MAKEFLAGS`, where it
re-enters with *command-line* origin and therefore outranks the `DB` alias, so
the probe reads back `sc_demo` instead of `sc_matrix_alias`. An
environment-origin `DB_NAME` does not take that path, which is why case C passes.

## Constraint

For `make release.daily_dev.acceptance.publish` — and therefore for
`env.matrix.check` — do **not** pass `DB_NAME` as a make command-line variable.
Let it resolve from `.env.dev` (which already sets `DB_NAME=sc_demo`). The
`daily_dev_acceptance_env_guard` still receives `DB_NAME=sc_demo`, because the
recipe forwards `$(DB_NAME)`, which now comes from `.env.dev`.

Correct daily entry:

```bash
ENV=dev ENV_FILE=.env.dev \
ACCEPTANCE_LOGIN=wutao ACCEPTANCE_PASSWORD='<password>' \
make -k release.daily_dev.acceptance.publish
```

## Daily Matrix Result At 626836ad (read-only observation)

With the corrected invocation the full governed matrix passed on `sc-root`:

- `daily_dev_acceptance_env_guard` PASS (`sha=626836ad`)
- `env.matrix.check` PASS (DB precedence/alias probes + `environment_topology_guard`)
- `daily_dev_runtime_repo_guard` PASS (`head=626836ad`)
- `daily_dev_customer_addons_runtime_guard` PASS
- product menu release gate PASS (standard/preview, 90/90)
- `frontend.static.build` PASS (`dist-dev`)
- `verify.user_confirmed.formal_surface.locked` OK
- `DEV_ACCEPTANCE_RELEASE_PROBE` PASS (`identity_deployed_sha expected=served=626836ad`,
  unique fixture target, `login=wutao` navigation PASS)
- `dev_acceptance_release_probe_schema_guard` PASS
- `[release.dev.acceptance.publish]` and `[release.daily_dev.acceptance.publish]` PASS

## Boundaries

- Scope is documentation only: `make/dev.mk`, `make/guards.mk`, the gates,
  thresholds, fixtures and assertions are unchanged.
- Historical iteration records that still show `DB_NAME=sc_demo` on the daily
  composite entry are intentionally not rewritten.
- The daily-server matrix above is a read-only observation recorded for context;
  it is not a deployment, version release, or product-delivery claim.
