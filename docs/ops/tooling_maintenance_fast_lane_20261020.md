# Tooling Maintenance Fast Lane (2026-10-20)

## Purpose

Small P4 tooling fixes should not pay the product, ORM, browser and full
backend matrix. They still need a bounded safety floor.

This lane is only for changes under:

- `docs/`
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
  --allow-make-guards \
  --owner-bypass-window
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

With `--owner-bypass-window`, it temporarily adds the repository owner as the
single `User` / `always` bypass actor, performs one normal non-force
`git push origin HEAD:main`, and removes that actor in a `finally` block. The
bypass is never left installed. Non-tooling paths fail classification before
the temporary actor is added.

## Protected-main fallback

If the temporary actor cannot be removed after the push, the tool reports
`failed_bypass_cleanup`; the operator must restore `bypass_actors=[]`
immediately. If the platform rejects the direct push, the tool stops and prints
`direct_main_push_rejected`; create a governed `fix/*` PR instead. It never
force-pushes or disables the ruleset.

## Boundary

The full product/backend/browser suites remain mandatory when any product,
runtime, data, permission, migration, deployment or frontend input changes.
