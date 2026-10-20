# Tooling Maintenance Fast Lane (2026-10-20)

## Purpose

Small P4 tooling fixes should not pay the product, ORM, browser and full
backend matrix. They still need a bounded safety floor.

This lane is only for changes under:

- `docs/ops/`
- `scripts/verify/`
- `scripts/ops/`
- `make/guards.mk` with the explicit `--allow-make-guards` flag

Product code, demo data, runtime configuration, frontend, `.agent` ledgers,
migrations and deployment files are rejected.

## Local commands

```bash
python3 scripts/ops/tooling_maintenance.py classify
python3 scripts/ops/tooling_maintenance.py check \
  --allow-make-guards

git add <exact tooling files>
git commit -m "<bounded tooling fix>"

python3 scripts/ops/tooling_maintenance.py publish \
  --expected-head "$(git rev-parse HEAD)" \
  --allow-make-guards
```

`check` runs only:

- Python syntax for changed files
- changed tooling unit tests
- documentation guards when docs changed
- environment topology guard when a verify guard or `make/guards.mk` changed
- `git diff --check`

`publish` requires:

- branch `main`
- clean worktree
- exactly one commit ahead of `origin/main`
- the same expected full SHA
- a successful fast check

It then performs a normal non-force `git push origin HEAD:main`.

## Protected-main fallback

The active main ruleset grants the repository owner `lidefend` a `User` /
`always` bypass actor. `publish` still uses a normal non-force push and verifies
the remote head; if the platform rejects it, the tool prints
`direct_main_push_rejected` and instructs the operator to use a governed
`fix/*` PR. It never force-pushes or disables branch protection.

## Boundary

The full product/backend/browser suites remain mandatory when any product,
runtime, data, permission, migration, deployment or frontend input changes.
