# Backend Contract SLO Telemetry — Core, Boundary, Delivery Call Site and Runtime Emission (L5 gap 1)

Run: `.agent/runs/BACKEND-CONTRACT-SLO-TELEMETRY/run.json`
Branch: `fix/contract-slo-telemetry`
Baseline: `c2410190feb7f7db2407083cca65f5ca624bb8c8`
Date: 2026-10-02

## Purpose

`docs/architecture/backend_contract_lifecycle_authority_v1.md` records the
backend unified page contract lifecycle at L4 and lists three L5 gaps. The first
is the missing contract-version SLO telemetry: success rate, degradation rate and
integrity-failure rate aggregated per contract version.

These batches deliver the **decision-independent core**, the **sink-agnostic
emission boundary**, the **runtime delivery call site**, and a governed
**runtime emission check** on the isolated contract-lifecycle profile:

- the identity a delivery is aggregated under;
- the outcome classification (`success` / `degraded` / `integrity_failure`);
- the aggregation, with exact-sum counts and rates that are never fabricated for
  an empty window;
- a fail-open hand-off of a validated observation (or its canonical log line) to a
  caller-supplied sink;
- one emission at the single runtime delivery chokepoint, defaulting to a
  structured log line;
- a runtime probe that drives real `ui.contract.v2` deliveries through the
  production handler on the authorized isolated profile and reads the
  `contractSlo` line the production sink actually emits.

## Boundary

- Formal Product Layer: **P0** platform kernel product (`smart_core`), with P4
  verification tooling.
- No contract protocol change, no new Odoo model. The runtime check reuses the
  isolated `sc-contract-lifecycle-v1` profile already registered by
  `docs/architecture/backend_contract_lifecycle_authority_v1.md` (database
  `sc_contract_lifecycle`, dbfilter `^sc_contract_lifecycle$`) through governed
  Make bring-up targets and a worktree-local env file; the fixed `scdevpass`
  credential is confined to that isolated synthetic database.
- The module is pure standard library, so the semantics are offline-verifiable
  and reusable by any sink (structured log, metrics pipeline, future read model).

## Exclusions

- Long-term persistence, trend reporting and any read intent. The runtime sink is
  the structured log line; a persisted read model would change
  schema/manifest/examples and is a separate protocol decision.
- Aggregating by the published `ui.business.config.contract` version number: the
  runtime lifecycle evidence does not carry it, so this batch keys on the
  identity that is actually present and leaves the additive field to a separate
  decision. `delivery_identity` already carries an optional `publishedVersionRef`
  so that decision stays additive.

## Results

### Delivered

- `addons/smart_core/core/contract_slo_telemetry.py` — pure standard-library core:
  - `delivery_identity()` reads the aggregation identity from the lifecycle
    evidence already emitted by `contract_lifecycle.build_lifecycle_evidence`
    (schemaId / schemaVersion / contractVersion / sourceType / sourceSha256 /
    stage), fails closed when that identity is incomplete, and carries an
    optional `publishedVersionRef` so published-version keying stays additive.
  - `classify_delivery()` returns `success` / `degraded` / `integrity_failure`,
    with integrity failure outranking degradation.
  - `aggregate_observations()` reports exact per-identity counts and
    `successRate` / `degradationRate` / `integrityFailureRate` over accepted
    observations only; an empty input yields no version rows rather than
    fabricated zero rates, and malformed observations are counted and sampled
    (capped) instead of being silently dropped.
  - Rows are keyed by the **whole** identity including `publishedVersionRef`, so
    two published versions never merge into one SLO row and an unattributed
    delivery never borrows another delivery's version. The row identity is
    rebuilt from its own grouping key, not from whichever observation arrived
    first. A first cut keyed on the six `IDENTITY_FIELDS` only, which collapsed
    three distinct published versions (two of them different) into one row and
    reported the first one's version for all of them.
  - `emit_observation()` validates an observation and hands it to a
    caller-supplied sink; it is fail-open (an unusable observation, a missing
    sink and a raising sink all return `False` instead of propagating into the
    delivery path), honours an explicit `False` rejection, and never reports the
    delivery outcome.
  - `observation_log_line()` / `parse_observation_line()` render and recover the
    canonical single-line form (observation key + compact, key-sorted JSON), so a
    line sink and a reader round-trip the same payload; an untrusted observation
    has no line at all.
  - `emit_observation_line()` is the same fail-open hand-off for line sinks.
- `addons/smart_core/handlers/ui_contract_v2_authority.py` — the runtime delivery
  call site:
  - `emit_delivery_observation()` re-verifies the seal
    (`verify_unified_page_contract_integrity`) so `integrityFailureRate` reports a
    real re-verification result rather than an assumed success, builds the
    observation from the sealed contract's own `meta.lifecycle`, and emits it
    through an injectable sink that defaults to the module logger. It is
    fail-open and returns `False` on every failure path, including a delivery
    with no lifecycle evidence (which is never aggregated under a guess).
  - `seal_runtime_contract()` emits once for every runtime delivery. It is the
    single chokepoint: all three handler seal sites route through it, and the
    handler calls `seal_unified_page_contract` nowhere else.
- `scripts/verify/test_contract_slo_telemetry.py` — 33 offline tests.
- `scripts/verify/test_ui_contract_v2_slo_emission.py` — 11 offline tests that
  load the real `ui_contract_v2_authority` module behind a package shim and
  *execute* `seal_runtime_contract` with an injected sink, so the emission is
  proven by behaviour rather than by finding a string in the source.
- `scripts/dev/local_contract_lifecycle_{env_prepare,rebuild,discard}.sh` and
  `make/dev.mk` — governed bring-up for the registered isolated profile
  (`local.contract-lifecycle.{prepare,rebuild,up,down,ps,odoo-shell,discard}`):
  env derived from `.env.dev` with the exact project / database / dbfilter
  identity, fixed `scdevpass`, ports 18090/8079, an exact-identity DENY guard
  when volumes exist without an env file, and confirmation-guarded destroy.
  `local.contract-lifecycle.odoo-shell` routes through the shared
  `scripts/ops/odoo_shell_exec.sh` with the env loaded by Make, so the shell
  entrypoint sees the right `COMPOSE_PROJECT_NAME` instead of the default
  project.
- `scripts/verify/contract_slo_telemetry_runtime_probe.py` — the in-container
  runtime probe. It attaches a capture handler to the production logger, drives
  three real deliveries (a form, the same form again, and a list) through
  `UiContractV2Handler.handle`, and asserts exactly one `contractSlo` line per
  delivery, identity completeness, `stage == runtime_delivery`, the declaration
  consumer accepting every observation unchanged, identical-identity grouping
  into one row, a distinct surface emitting its own identity, and no
  integrity-failure outcome. It writes a machine-readable report to
  `/tmp/contract_slo_telemetry_runtime_probe.json`.
- `scripts/verify/contract_slo_telemetry_runtime_probe_schema_guard.py` — host-side
  guard (5 tests) that re-checks the report with a non-zero test count, so a
  probe run cannot be a pass just because a string appeared.
- `make/dev_test.mk` —
  `verify.backend.contract_slo_telemetry[.unit|.emission|.runtime]`.

### Evidence

- `make ci.local.iteration` → PASS, `change_state=dirty`.
- `make verify.backend.contract_slo_telemetry.unit` → PASS, 33 tests.
  Receipt `.runtime/agent-runs/BACKEND-CONTRACT-SLO-TELEMETRY/slo_core.json`
  (log `logs/slo_core.log`).
- Negative-first proof, batch 1 (`logs/negative_first.log`): removing the integrity-first
  branch and the malformed-row outcome check makes 2 tests fail; the core was
  restored byte-identical (`diff` empty) and the suite returned 18/18 OK.
- Negative-first proof, batch 2 (`logs/batch2_neuter_injected.log`): after
  confirming the un-injected baseline at 30/30 OK, removing the
  `_reject_reason` guard in `emit_observation` produced 5 failures and making the
  fail-open `except` re-raise produced 1 error on the raising-sink test. The core
  was restored and verified byte-identical
  (`logs/batch2_baseline_sha256.txt`, `logs/batch2_restored.log`) before being
  recorded.
- Negative-first proof, batch 3 (`logs/batch3_neuter_injected.log`): after
  confirming the un-injected baseline at 33/33 OK, restoring the pre-fix
  grouping key (six `IDENTITY_FIELDS`, first-observation identity copy) produced
  exactly the 3 version-grouping failures and nothing else. The core and suite
  were restored and verified byte-identical
  (`logs/batch3_baseline_sha256.txt`, `logs/batch3_restored.log`).
- Negative-first proof, batch 4, run one injection at a time so each property is
  independently load-bearing (`logs/batch4_neuter_failopen_only.log`,
  `logs/batch4_neuter_callsite_only.log`): making the emitter's `except` re-raise
  produced 6 errors, all on the bad-input paths; removing the chokepoint's emit
  call produced 2 failures and 1 error, exactly the call-site tests. The
  authority module and suite were restored and verified byte-identical
  (`logs/batch4_baseline_sha256.txt`, `logs/batch4_restored.log`). A raising sink
  is caught one layer deeper in `emit_observation_line`, whose own fail-open was
  already proven load-bearing in batch 2.
- Receipts `slo_core` (33 tests) and `slo_emission` (11 tests) both resolve as
  `reusable` under `make agent.run.resume`.
- Runtime emission, on the isolated profile (`local.contract-lifecycle` stack:
  `sc-contract-lifecycle-v1-{odoo,db,redis,nginx}-1`, database
  `sc_contract_lifecycle`, `smart_core` installed, my worktree's `addons`
  mounted into the container so the probe exercises *this* code):
  `make verify.backend.contract_slo_telemetry.runtime` → PASS, probe 15/15
  checks, host guard 5 tests. The production handler delivered a `res.partner`
  form (`ok=True`, intent `ui.contract.v2`), captured exactly one `contractSlo`
  line, and the declaration consumer accepted every observation unchanged:
  aggregate 3 observations, 0 rejected, 2 identities, `successRate=1.0`,
  `integrityFailureRate=0.0`. The repeat form delivery grouped into the same row
  (`observations=2`) while the list delivery emitted its own identity
  (`sourceType=ui.contract` vs `native_form_projection`), proving version/identity
  keying at runtime. Receipt
  `.runtime/agent-runs/BACKEND-CONTRACT-SLO-TELEMETRY/slo_runtime.json`
  (log `logs/slo_runtime.log`); the receipt is head-bound but not auto-reusable
  (the reuse evaluator refuses runtime evidence without authoritative
  environment readback, so `make agent.run.resume` reports `slo_runtime` stale by
  design).
- Negative-first proof, runtime half: after confirming the un-injected baseline
  emitted a valid `success` line, injecting `return False` at the top of
  `emit_delivery_observation` produced zero `contractSlo` lines while the
  delivery still succeeded (`ok=True`, fail-open) and failed 10 probe checks /
  3 host guard tests (`make verify.backend.contract_slo_telemetry.runtime`
  errored). The authority module was restored and verified byte-identical
  (`sha256 e8131205b79181c3fa01501053aa962c2ce21867ca47bf3abcfdde29341897d3`),
  after which the check returned 15/15 and 5/5 again.
- The identity test seals a real contract through `contract_lifecycle` and reads
  the identity back from `meta.lifecycle`, so the SLO identity is bound to the
  emitted evidence rather than to a synthetic dictionary. The suite also asserts
  the core imports no `odoo` module.

### Not delivered (deferred, deliberate)

- Long-term persistence or a trend read model.
- Contract-version keying by the published `ui.business.config.contract` version
  number (needs an additive lifecycle field; separate decision).

### Runtime half (closed on the authorized isolated profile)

The owner authorized standing up the registered isolated profile and driving the
runtime delivery path, so the previous environment block is resolved:

- the bring-up exists as governed Make targets
  (`local.contract-lifecycle.*`) with a worktree-local env file
  (`.env.local.contract-lifecycle`), derived from `.env.dev` and bound to the
  exact identity (project `sc-contract-lifecycle-v1`, database
  `sc_contract_lifecycle`, dbfilter `^sc_contract_lifecycle$`, ports 18090/8079,
  fixed `scdevpass`);
- the container mounts *this* worktree's `addons` directory, so a probe there
  exercises the changed code rather than the primary worktree's;
- the shared profiles `local.dev` / `local.sample` / `local.clean` were not
  touched; their fixed project names and volumes still serve the primary
  worktree.

The runtime follow-up ran as one command
(`make verify.backend.contract_slo_telemetry.runtime`) and emitted a real
`contractSlo` line, so the runtime delivery path is exercised, not just wired.

### Remaining gap

The L5 gap stays open because emission is proven but retention is not:
long-term persistence (a sink surviving process exit) and a per-version trend
read model are still not implemented. The L4/L5 statement in
`docs/architecture/backend_contract_lifecycle_authority_v1.md` is therefore
intentionally unchanged. Publication is on hold by owner instruction.
