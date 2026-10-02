# Backend Contract Lifecycle L4 — Runtime Evidence Governance

Run: `.agent/runs/BACKEND-CONTRACT-L4-CLOSURE/run.json`
Branch: `fix/backend-contract-l4`
Baseline: `002b2c64aec7b8981b3df21ebc25f80be2eb728c` (origin/main after PR #526/#527/#528)
Date: 2026-10-02

## Purpose

`docs/architecture/backend_contract_lifecycle_authority_v1.md` already declares the
backend unified page contract lifecycle at **L4** on two halves:

- machine coverage 100/100 across eight lifecycle dimensions (P0 = 0);
- fourteen real assertions against an isolated contract-lifecycle database.

The first half is a governed, offline, failing gate
(`make verify.backend.contract_lifecycle.authority`). The second half is produced by
`make verify.backend.contract_lifecycle.runtime`, but its artifact
(`artifacts/backend/backend_contract_lifecycle_runtime_probe.json`) had **no guard,
no identity binding and no offline validation** — only the probe's own exit code
protected it, and nothing re-checked the emitted evidence.

This batch closes that gap so the runtime half is verifiable offline, exactly like
the machine half.

## Batch scope

- `scripts/verify/backend_contract_lifecycle_runtime_probe.py` — bind identity and
  emit the declared assertion set.
- `scripts/verify/backend_contract_lifecycle_runtime_schema_guard.py` (new) — offline
  validation of the runtime artifact.
- `scripts/verify/test_backend_contract_lifecycle_runtime_schema_guard.py` (new) —
  negative-first unit proof.
- `make/dev_test.mk` — wire the guard into the runtime lane and add its unit target.
- `docs/architecture/backend_contract_lifecycle_authority_v1.md` / `.en.md` — bind
  the L4 statement to the guard.

## Exclusions

- No new compose project, database, port, volume or credential.
- No industry (P1), customer (P2) or low-code (P3) semantics.
- No deployment or version release.

## Results

### L1 — static/iteration (offline)

- `make ci.local.iteration` → PASS, `change_state=dirty`, `coverage=L1_only`
  (recommendation-only; the real L2 targets were run below).

### L2 — offline gates (recorded as run receipts)

- `verify.backend.contract_lifecycle.authority` → PASS. Guard report
  `score=100/100`, `maturityLevel=L4_governed_production_ready`, `p0Count=0`,
  8/8 dimensions; 31 unit tests across the bundled suites, now including the new
  runtime schema-guard suite. Receipt
  `.runtime/agent-runs/BACKEND-CONTRACT-L4-CLOSURE/authority.json`
  (log `logs/authority.log`).
- `verify.backend.contract_lifecycle.runtime.schema.guard.unit` → PASS, 12 tests.
  Receipt `runtime_artifact_guard.json` (log `logs/runtime_artifact_guard.log`).
- Negative-first proof that the guard is load-bearing: removing both `_check_*`
  invocations from the guard makes 11/12 tests fail; the file was then restored
  byte-identical (`diff` empty) and the suite returned 12/12 OK. Log
  `logs/guard_negative_first.log`.

Both receipts resolve as `reusable` under `make agent.run.resume`
(`declared inputs and original log unchanged`).

### L4 runtime lane — `not_run` (blocked, not fabricated)

`make verify.backend.contract_lifecycle.runtime` cannot execute in this worktree:

- bare target: `[FATAL] COMPOSE_PROJECT_NAME is required. Set it or create .env`;
- with the registered project name (`make ... COMPOSE_PROJECT_NAME=sc-contract-lifecycle-v1`):
  `missing required env vars: DB_USER DB_PASSWORD DB_NAME ADMIN_PASSWD JWT_SECRET ODOO_DBFILTER`.

The registered isolated environment profile is absent here: the
`sc-contract-lifecycle-v1` compose project retains only a leftover `redis`
container (`odoo`/`db` are gone), `sc_contract_lifecycle` is not present in the
reachable databases, and there is no env file or Make bring-up target for the
profile. Hand-assembling compose/credentials is forbidden and creating a new
environment is outside this batch's scope, so the fourteen-assertion artifact is
not produced here. This is recorded truthfully as `not_run`; the guard unit proof
and the authority gate are unaffected, and the runtime lane re-run stays a
separate environment prerequisite.

## Status

- Batch (offline governance closure): **验收完成** for the offline half — the
  runtime artifact is now bound to an offline, negative-proven guard, and the
  authority gate stays 100/100 L4 with `p0Count=0`.
- L4 runtime re-execution: **blocked** on the registered isolated environment
  (see above); no new environment was created.
- Mainline integration, version release and product delivery: not started, not
  authorized by this batch. Publication is held by the owner; the remaining gate
  is the runtime lane re-run once its registered isolated environment is restored.
- Run state: `verification_pending` (implementation complete, `runtime_probe`
  still `not_run`). Rollback: revert the two layer-owned commits
  (`57aeee43e`, `df0ea7957`); the guard, probe declaration and Make wiring are
  additive and change no product behaviour.
