# Daily Deployment Tooling

## Identity

- Baseline: `94d6bdb20c0e7f26a97d5df8dba69846f5b01e73`
- Branch: `fix/daily-deploy-tooling-20261125`
- Run: `.agent/runs/DAILY-DEPLOY-TOOLING-20261125/run.json`

## Findings

The authorized deployment exposed two P4 defects:

1. The local platform-control env file retained a stale source worktree after
   that worktree was removed. Existing platform volumes stayed healthy, but the
   running container mounted the deleted source tree and no in-place smart_core
   upgrade action existed.
2. The daily host is a shared 7.4 GiB runtime. The remote Vite build succeeded
   with a bounded 1536 MiB Node heap but was OOM-killed without the bound. The
   release wrapper also discarded the structured remote build tail on failure.
3. The daily release orchestration omitted the declared-module upgrade even
   though the deployment runbook requires it; the deployment had to run it
   manually after duty refresh.

## Result

- Existing local platform credentials and database identity are preserved.
- Source root, source revision, deployment environment and frontend directory
  are rebound to the current worktree before platform lifecycle actions.
- `local.platform upgrade` runs Odoo `-u smart_core` against existing volumes.
- Daily remote frontend builds use `--max-old-space-size=1536`.
- Failed builds retain stderr plus remote `build_tail`, `fingerprint_tail` and
  `restart_tail` evidence.
- Daily release now runs `daily.runtime.database.duty.upgrade` after refresh and
  before source-revision/publication convergence.

## Deployment Readback

- Local runtime: `94d6bdb20c0e7f26a97d5df8dba69846f5b01e73`.
- Local frontend fingerprint: `d6dccc33f5b79dc85c24f8238fc3b4037b708efb4396f995df2df2cf0d7f8284`.
- Local active release: `local-dev-94d6bdb20c0e`, 46 scenarios, 132 pages.
- Daily demo and platform control: `94d6bdb20c0e7f26a97d5df8dba69846f5b01e73`.
- Daily frontend fingerprint: `0ccf154507873f70a4bb79d24966ff5fa47fb37aef133fd11985d4155e1fbcb3`.
- Daily duty refresh and module upgrade: PASS.
- Daily published face: `construction.standard`, `construction.preview`: PASS.
- Daily entry verify and build identity verify: PASS.

## Cleanup

Stopped without deleting volumes:

- R10 performance A/B stacks.
- Four-month-old release and user-data rehearsal containers.
- A 140-day-old remote Vite development server on port 5174.

Historical `sc-backend-odoo-dev`, the active named tenant development stack, a
separate UAT stack, MySQL and the public site service were preserved.

## Integration and closeout

- PR #1000 merged at `2026-11-25T01:04:55Z`.
- Source HEAD: `4559a881f05442f1e3cde7604171b58430f130f1`.
- Main merge commit: `da10143779c9f96afb165c30e7f74c51a1192657`.
- The active-run binding is removed after the merged tooling result becomes
  mainline history; the run remains as a completed historical record.
- The source workspace returns to `main`. Pre-existing dirty worktrees, open PRs
  and unmerged branches are excluded from this closeout.

## Exclusions

No demo rebuild or seed, no database volume deletion, no production deployment.
