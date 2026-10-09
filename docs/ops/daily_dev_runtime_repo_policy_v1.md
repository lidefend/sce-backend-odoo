# Daily Dev Runtime Repository Policy v1

## Purpose

The daily development runtime repository is the deployable acceptance working
tree for `ENV=dev`, `.env.dev`, and `DB_NAME=sc_demo`. It accepts either the
authoritative `origin/main` identity or one explicitly approved governed branch
candidate at an immutable full SHA. A candidate is deployed before merge so the
owner can accept the real daily runtime; production authority remains `main`.

## Runtime Repository

- Host alias: `sc-root`
- Path: `/opt/projects/repos/sce-product-odoo`
- Main mode: branch `main`, clean and aligned with `origin/main`
- Candidate mode: detached exact SHA with a matching
  `refs/daily-candidates/<source-branch>` evidence ref
- Candidate source branch: `feature/*`, `fix/*`, `refactor/*`, `audit/*`,
  `release/*`, or `codex/*`
- Required state: clean working tree and an explicitly declared deployment mode
- Allowed operations: deploy, module upgrade, restart, read-only inspection
- Forbidden operations: exploratory edits, replay output generation, migration
  asset generation, long-running validation that writes into the repository

Before every main-mode upgrade or publish step, run:

```bash
ENV=dev ENV_FILE=.env.dev DB_NAME=sc_demo make verify.daily_dev.runtime_repo.clean
```

Before every candidate-mode upgrade or publish step, bind the exact source:

```bash
ENV=dev ENV_FILE=.env.dev DB_NAME=sc_demo \
DAILY_DEV_DEPLOYMENT_MODE=candidate \
DAILY_DEV_CANDIDATE_SOURCE_BRANCH=feature/example \
DAILY_DEV_CANDIDATE_EXPECTED_SHA=<full-40-character-sha> \
make verify.daily_dev.runtime_repo.clean
```

This preflight also fails closed unless `smart_construction_custom` is
`installed`, its database version equals the external package manifest, the
running Odoo container has the configured customer directory mounted read-only
at `/mnt/customer-addons`, and Odoo resolves the module from that exact path.

Start or recreate the daily Odoo service through the repository entrypoint.
When `SC_CUSTOMER_ADDONS_ROOT` is configured, Make automatically includes the
customer overlay; a base-compose-only restart is not a valid daily runtime. The
explicit equivalent is:

```bash
ENV=dev ENV_FILE=.env.dev DB_NAME=sc_demo \
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.customer-addons.yml" \
make restart
```

If the daily server cannot read GitHub smart HTTP, a locally committed and
validated governed branch can be sent as an exact verified Git bundle before
merge:

```bash
CONFIRM_DAILY_CANDIDATE_BUNDLE_SYNC=SYNC_EXACT_DAILY_CANDIDATE_SHA_WITH_BUNDLE \
make daily.runtime.candidate.bundle_sync \
  DAILY_CANDIDATE_SOURCE_REPOSITORY=/absolute/path/to/topic-worktree \
  DAILY_CANDIDATE_SOURCE_BRANCH=feature/example \
  DAILY_CANDIDATE_EXPECTED_SHA=<candidate-full-sha> \
  DAILY_CANDIDATE_EXPECTED_OLD_SHA=<current-daily-full-sha> \
  DAILY_RUNTIME_SSH_HOST=sc-root
```

The server records the source under `refs/daily-candidates/`, checks out the
candidate as detached HEAD, and does not update `main` or `origin/main`.
The tool may run from the governance/main worktree while reading a separate
clean topic worktree through `DAILY_CANDIDATE_SOURCE_REPOSITORY`; that source
must have the authoritative GitHub `origin`, exact branch, and exact SHA.

A daily candidate deployment has two faces that were previously released by
separate lanes: the code/rendering face (bundle sync, module upgrade, served
revision, built frontend) and the published product face (the active
edition-release snapshot the navigation release gate actually reads). Only the
published face decides whether an entry may be opened, so deploying a contract
change without re-freezing it silently dropped declared, user-visible entries
from the gated navigation. Deploy a candidate through the single coupled entry:

```bash
CONFIRM_DAILY_CANDIDATE_BUNDLE_SYNC=SYNC_EXACT_DAILY_CANDIDATE_SHA_WITH_BUNDLE \
CONFIRM_DAILY_RUNTIME_PUBLISHED_FACE=REFRESH_DAILY_RUNTIME_PUBLISHED_FACE_FROM_LOCKED_CONTRACT \
make daily.runtime.candidate.release \
  DAILY_CANDIDATE_SOURCE_REPOSITORY=/absolute/path/to/topic-worktree \
  DAILY_CANDIDATE_SOURCE_BRANCH=feature/example \
  DAILY_CANDIDATE_EXPECTED_SHA=<candidate-full-sha> \
  DAILY_CANDIDATE_EXPECTED_OLD_SHA=<current-daily-full-sha> \
  DAILY_RUNTIME_SSH_HOST=sc-root \
  DAILY_RUNTIME_PUBLISHED_FACE_LOGIN=<daily-full-product-login>
```

It binds the exact candidate revision, re-freezes every published product
snapshot from the locked contract through
`release.daily_product_navigation.converge`, reloads the served runtime and
re-proves the released face with
`verify.daily_dev.product_menu_release_gate.guard`. The run fails closed when the
contract, the product policy, the active snapshot, the gate and the gated
navigation disagree, so a stale published face cannot be deployed silently. The
refresh step alone is also available as
`make daily.runtime.published_face.converge`. Releasing the two faces through
separate manual lanes is not an accepted daily procedure.

After owner acceptance, open or update the PR and merge through protected
`main`. A later main-mode deployment replaces the candidate runtime. Candidate
rejection returns to the previously recorded accepted SHA; it never rewrites
the source branch or production state.

When the runtime is still at the accepted detached candidate, the main-mode
deployment may return it to `main` by declaring the exact candidate SHA. The
entry then requires a clean detached HEAD equal to that SHA, `refs/heads/main`
and `refs/remotes/origin/main` equal to the expected old SHA, and the candidate
SHA present under `refs/daily-candidates/`; only then does it check out `main`
and run the unchanged exact bundle sync. If the candidate SHA is omitted, the
entry still requires the runtime to be attached `main` at the expected old SHA.

For an already merged main commit, the existing incremental main bundle remains
available:

```bash
CONFIRM_DAILY_RUNTIME_BUNDLE_SYNC=SYNC_EXACT_DAILY_MAIN_SHA_WITH_BUNDLE \
make daily.runtime.main.bundle_sync \
  DAILY_RUNTIME_EXPECTED_SHA=<merged-main-full-sha> \
  DAILY_RUNTIME_EXPECTED_OLD_SHA=<current-daily-main-full-sha> \
  DAILY_RUNTIME_EXPECTED_CANDIDATE_SHA=<recorded-detached-candidate-full-sha> \
  DAILY_RUNTIME_SSH_HOST=sc-root
```

`DAILY_RUNTIME_EXPECTED_CANDIDATE_SHA` is optional and only needed when the
runtime is on the recorded detached candidate rather than attached `main`.

The main fallback requires a clean governed local branch at the exact authoritative
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

If a scratch result becomes product code, move it to a governed branch and
commit it before candidate deployment. Do not apply scratch changes directly
to the runtime repository. The fixed flow is:

```text
governed branch local gates
→ exact branch SHA on daily development
→ owner acceptance
→ PR review and merge to main
→ production release process
```

## Closeout Rule

If local state appears in the runtime repository, stop deployment and classify
it before proceeding:

- tracked code changes: archive to a named branch or move to a topic branch
- untracked artifacts: move to `/opt/projects/backups/<timestamp>/untracked`
- generated reports: keep outside runtime repo unless intentionally committed
- stale temporary refs: delete after archive/report is confirmed

The runtime repository can be upgraded only after the guard passes again.
