# Daily Dev Runtime Repository Policy v1

## Purpose

The daily development runtime repository is the deployable working tree for
`ENV=dev`, `.env.dev`, and `DB_NAME=sc_demo`. It must stay aligned with
`origin/main` so upgrades can be fast-forwarded and verified without preserving
ad hoc local state.

## Runtime Repository

- Host alias: `sc-root`
- Path: `/opt/projects/repos/sce-product-odoo`
- Required branch: `main`
- Required state: clean working tree, aligned with upstream
- Allowed operations: deploy, module upgrade, restart, read-only inspection
- Forbidden operations: exploratory edits, replay output generation, migration
  asset generation, long-running validation that writes into the repository

Before every upgrade or publish step, run:

```bash
ENV=dev ENV_FILE=.env.dev DB_NAME=sc_demo make verify.daily_dev.runtime_repo.clean
```

If the daily server cannot read GitHub smart HTTP, the approved fallback is an
exact incremental Git bundle sent over the configured SSH host. It is allowed
only after the candidate is merged to authoritative `origin/main`:

```bash
CONFIRM_DAILY_RUNTIME_BUNDLE_SYNC=SYNC_EXACT_DAILY_MAIN_SHA_WITH_BUNDLE \
make daily.runtime.main.bundle_sync \
  DAILY_RUNTIME_EXPECTED_SHA=<merged-main-full-sha> \
  DAILY_RUNTIME_EXPECTED_OLD_SHA=<current-daily-main-full-sha> \
  DAILY_RUNTIME_SSH_HOST=sc-root
```

The fallback requires a clean governed local branch at the exact authoritative
`origin/main` SHA, a clean remote `main`, exact old and new SHAs, an incremental
bundle digest match, and a fast-forward ancestry check. The local checkout does
not need to be `main`, which may be reserved by another governed worktree. The
bundle is created only from `refs/remotes/origin/main`. It updates the remote
checked-out `main` and its local `origin/main`
remote-tracking identity to the same bundle-proven SHA; it does not modify Git
remote configuration and cannot perform a non-fast-forward update.

## Scratch Work

Temporary development, migration replay, attachment probes, and acceptance runs
must use a separate worktree or scratch directory, for example:

```bash
mkdir -p /opt/projects/scratch/worktrees
cd /opt/projects/repos/sce-product-odoo
git worktree add /opt/projects/scratch/worktrees/<topic> main
cd /opt/projects/scratch/worktrees/<topic>
```

Generated outputs must stay outside the runtime repository, preferably under:

- `/opt/projects/artifacts`
- `/opt/projects/backups`
- `/opt/projects/scratch`

If a scratch result becomes product code, move it through the normal local
branch, review, validation, merge, and deploy flow. Do not apply scratch
changes directly to the runtime repository.

## Closeout Rule

If local state appears in the runtime repository, stop deployment and classify
it before proceeding:

- tracked code changes: archive to a named branch or move to a topic branch
- untracked artifacts: move to `/opt/projects/backups/<timestamp>/untracked`
- generated reports: keep outside runtime repo unless intentionally committed
- stale temporary refs: delete after archive/report is confirmed

The runtime repository can be upgraded only after the guard passes again.
