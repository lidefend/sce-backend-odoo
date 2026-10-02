# Backend Contract SLO Telemetry — Core, Boundary and Delivery Call Site (L5 gap 1)

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
emission boundary** and the **runtime delivery call site**:

- the identity a delivery is aggregated under;
- the outcome classification (`success` / `degraded` / `integrity_failure`);
- the aggregation, with exact-sum counts and rates that are never fabricated for
  an empty window;
- a fail-open hand-off of a validated observation (or its canonical log line) to a
  caller-supplied sink;
- one emission at the single runtime delivery chokepoint, defaulting to a
  structured log line.

## Boundary

- Formal Product Layer: **P0** platform kernel product (`smart_core`), with P4
  verification tooling.
- No contract protocol change, no new Odoo model, no module upgrade, no new
  compose project / database / port / volume / credential.
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
- `make/dev_test.mk` —
  `verify.backend.contract_slo_telemetry[.unit|.emission]`.

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
- The identity test seals a real contract through `contract_lifecycle` and reads
  the identity back from `meta.lifecycle`, so the SLO identity is bound to the
  emitted evidence rather than to a synthetic dictionary. The suite also asserts
  the core imports no `odoo` module.

### Not delivered (deferred, deliberate)

- Long-term persistence or a trend read model.
- Contract-version keying by the published `ui.business.config.contract` version
  number (needs an additive lifecycle field; separate decision).

### Blocked on authorization

The call site and sink are now implemented, so only the environment remains. No
governed profile in this repository runs this worktree's code:

- every running Odoo container mounts
  `/home/lidefend/workspace/sce-backend-odoo/addons` (the primary worktree), so a
  probe against any of them would exercise unchanged code;
- `local.dev`, `local.sample` and `local.clean` use fixed compose project names
  and fixed volumes and currently serve the primary worktree, so re-running any
  of them from here would recreate a stack another executor is using — the
  shared-runtime case the hard lock forbids;
- the registered isolated profile (`sc-contract-lifecycle-v1` /
  `sc_contract_lifecycle` / dbfilter `^sc_contract_lifecycle$`, per
  `docs/architecture/backend_contract_lifecycle_authority_v1.md`) has no Make
  bring-up target and no env file, and all `LOCAL_*_ENV_FILE` values point into
  the primary worktree.

Consequently the emission stays offline-verified only: the runtime delivery path
is wired but not exercised, and the SLO gap is still a definition rather than
telemetry. Standing the isolated profile up means a new compose project, database
and volumes plus a new env file, which the hard lock reserves for separately
authorized P4 work; hand-assembling compose/database/port/volume/credential
commands is explicitly forbidden.

The runtime follow-up is one command once such an environment exists: drive a
page delivery through the handler and read the `contractSlo` line the module
logger emits.

Consequently the L5 gap remains open: the L4/L5 statement in
`docs/architecture/backend_contract_lifecycle_authority_v1.md` is intentionally
unchanged.
