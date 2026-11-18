# PR 933 CI execution repair (2026-11-18)

## Boundary and identity

- Formal Product Layer: P4; standard engineering tooling.
- Layer Target / Module: Make environment propagation and backend CI execution.
- Worktree: `sce-backend-odoo-release-rehearsal`.
- Starting HEAD: `b8ccee4da2aee2fd063f2c68001eb242178cfca0`.
- PR base: `64f2e68ea1b80464fd080bb93b1a83312decc8c4`.
- Product models, contracts, permissions, frontend and persistent environments are
  excluded from this repair. Their existing PR validation obligations remain.
- Existing uncommitted CI changes were preserved in
  `.runtime/pr933-ci-diagnosis/preexisting.patch` before editing.

## Observed failure and correction

Run `44304328637` timed out both backend shards before any test-container output.
Its downstream coverage collector then correctly rejected missing module receipts.
The previous claims that pip, Python session handling, GNU timeout process groups,
or Compose stdin caused that startup stall were hypotheses, not demonstrated causes.

The reproduced defect is the bare `export` after Make includes `ENV_FILE`.
It exports all later lazy Make variables, including unrelated acceptance/release
shell probes. GNU Make 4.4 also exports variables into `$(shell ...)` subprocesses
(see the upstream 4.4 NEWS `shell-export` change), causing recursive expansion.

A real GNU Make 4.4.1 build reproduced the defect using only
`make guard.prod.forbid ENV_FILE=/dev/null`: it exceeded a 10-second diagnostic
limit without starting any Docker process. Without the environment include it
finished in 0.17 seconds. With the correction, the same environment-file probe
finished in 0.16 seconds on both Make 4.3 and 4.4.1.

Make now exports only assignment names declared in the environment file. Existing
file values, explicit exports, default/append assignments and command-line database
precedence are tested against the real Make graph. An unrelated lazy side-effect
probe must never execute during environment construction.

The correction keeps the existing per-module `timeout --foreground`, heartbeat,
retry and diagnostic receipts, with the 240-minute job ceiling. The inherited
proposal to cap an entire full shard at 25 minutes was rejected: multiple modules
and retries must retain their own budgets. Compose stdin is explicitly disabled.
Dependency installation is restored and fails closed before Odoo execution.

Independent review also identified that changed tests had replaced complete
impacted modules without certified baseline/family reuse. Focused requests now
return the full impacted plan, preserving unchanged families and dependency
modules. Changed-test selectors remain additional coverage. The consumer regression
continues to execute the actual Make-call fragment with external execution stubbed.

## Evidence reuse repair

The CI repair worktree initially lacked the ignored `.runtime` evidence held by
`sce-backend-odoo-acceptance-scope-20261109-be-close-01-20261118`. Missing original
receipts, logs and readbacks were copied unchanged into the selected worktree,
without overwriting existing files. The run evaluator verifies ancestor identity,
declared input hashes, log hashes and readback dependencies; 17 targets are reusable.
The initial repeat ORM invocation was interrupted and is not recorded as a pass.

The aggregate resume path additionally required identical changed-path and target
sets. Adding a CI check therefore discarded unrelated passed business targets.
It now selects requested targets that the source actually declared and executed,
then excludes targets affected by intervening committed/dirty changes. Declared
stale dependencies cannot be overridden by either exact or partial aggregate reuse.
Original logs and source receipts remain immutable and hash-verified.

The revised plan reuses the lane audit from a verified aggregate as well as those
17 run checks. Runtime/unknown-kind targets without a currently reusable single-check
receipt cannot borrow aggregate success. The intent-smoke ORM therefore remains
required: its prior aggregate log lacks the required environment-bound single-check
receipt. Other remaining targets are CI/tool tests, a profile check and validation
of an existing sample artifact. Regression coverage includes a new unrelated target, a remaining
target subset, tampered evidence, changed-target invalidation and explicit stale
inputs. `verify.frontend.dev.incremental.unit`: PASS, 182 tests.

## Gate responsibility

| Gate | State | Owner / reason |
| --- | --- | --- |
| exact base/head and dirty scope | required | PR and local Git identity |
| existing CI tool families and focused regression | required | `verify.ci.workflow.contract` |
| workflow security / test coverage consumer | required | `verify.github_actions.security`, `verify.test.coverage.registry` |
| local iteration | required | `ci.local.iteration` |
| product module baseline / contract / frontend / browser | excluded from new repair | no P0-P3 source change; existing PR obligations remain |
| remote required gates | not_run for new candidate | requires published exact SHA |

## Validation

- Make environment regression: PASS on GNU Make 4.3 and 4.4.1, including empty
  and populated environment files; no database/container execution.
- `verify.ci.workflow.contract`: PASS; dispatch family includes 23 tests.
- `verify.github_actions.security`: PASS, 18 tests and policy scan.
- `verify.test.coverage.registry`: PASS, 19 tests and registry audit.
- Initial `ci.local.iteration`: failed on undeclared `Makefile` scope; the current
  run scope has been corrected.
- Independent review: three findings addressed (baseline scope, per-module timeout,
  dependency-install failure); recheck found no blocking issues.
- Exact-tree plan diagnostic: full scope, 14 impacted modules, four shards;
  76 changed cases across backend and separately managed owners remain declared.
- `ci.delivery.freeze.prepare`: PASS, including generated evidence preflight.
- Final `ci.local.iteration`: PASS. Seventeen registered checks and one offline
  aggregate target reused; ten remaining targets passed, including ten intent-smoke
  ORM cases. Runtime evidence: `.runtime/test-baseline/1795006732083719988/receipt.json`.
- Final independent reuse review: no remaining blockers; runtime, unknown-kind and
  unregistered targets cannot substitute aggregate success for environment evidence.
- Raw logs: `.runtime/pr933-ci-diagnosis/`.

## Rollback and completion boundary

Revert this repair commit to restore the previous execution behavior. No persistent
runtime/data changes are part of this repair. Local passes do not establish remote
CI success, merge readiness, deployment or product delivery.
