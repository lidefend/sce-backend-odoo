# Backend Contract SLO Telemetry — Core, Boundary, Delivery Call Site, Runtime Emission and Durable Store (L5 gap 1)

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
  `contractSlo` line the production sink actually emits;
- a durable observation store, a retention horizon **with its scheduled sweep**
  (an active daily cron, not just a declared horizon), and a per-version trend
  read model exposed through a read intent.

## Boundary

- Formal Product Layer: **P0** platform kernel product (`smart_core`), with P4
  verification tooling.
- No contract protocol change. The durable store adds one P0 platform model
  (`sc.contract.slo.observation`) and one read intent; the runtime check reuses the
  isolated `sc-contract-lifecycle-v1` profile already registered by
  `docs/architecture/backend_contract_lifecycle_authority_v1.md` (database
  `sc_contract_lifecycle`, dbfilter `^sc_contract_lifecycle$`) through governed
  Make bring-up targets and a worktree-local env file; the fixed `scdevpass`
  credential is confined to that isolated synthetic database.
- The module is pure standard library, so the semantics are offline-verifiable
  and reusable by any sink (structured log, metrics pipeline, future read model).

## Exclusions

- Aggregating by the published `ui.business.config.contract` version number: the
  runtime lifecycle evidence does not carry it, so this batch keys on the
  identity that is actually present and leaves the additive field to a separate
  decision. `delivery_identity` already carries an optional `publishedVersionRef`
  so that decision stays additive.

The durable store, the retention horizon and the trend read model are no longer
excluded: they are delivered below. They changed the manifest version and added a
model, ACL rows and a read intent, which is the P0 protocol surface this batch
owns.

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
- `addons/smart_core/models/contract_slo_observation.py` — the durable store
  (`sc.contract.slo.observation`): one row per aggregate-ready observation, the
  lifecycle identity as columns, `outcome`, `observed_at`, `latency_ms`,
  `client_type`, `request_id`, `company_id`, plus version/time composite indexes.
  Registered in `models/__init__.py` with read-for-user / write-for-admin ACLs.
  It also exposes `cron_prune()`, the scheduled half of the retention horizon:
  the horizon was declared but nothing invoked it, so the store grew without
  bound once persistence was on. The sweep is `@api.model`, delegates to the
  pure `prune_observations()`, stays fail-open, and deliberately does **not**
  gate on `persist_enabled` (rows written while it was on must still age out
  after it is switched off).
- `addons/smart_core/data/contract_slo_retention_cron.xml` — the carrier: one
  active daily `ir.cron` (`SC Contract SLO Observation Prune`) targeting this
  model, loaded by the manifest after the ACLs it depends on. It ships active
  like the existing GC cron (`cron_signup_throttle_gc`), because it is a cheap
  indexed delete that is a no-op on an empty store and must not silently drift
  off on upgrade.
- `addons/smart_core/core/contract_slo_persistence.py` — the second half of the
  gap. Pure, offline-verifiable parts: `row_values()`/`observation_from_row()`
  (exact identity round trip, and an unusable row reads back as unreadable rather
  than as a guessed identity), `bucket_windows()` and `build_trend()` (each
  observation lands in exactly one half-open bucket; an unplaceable observation is
  counted, never dropped or leaked into a neighbour). Thin fail-open `env`
  wrappers: `persist_observation()`/`persist_line()`, `read_observations()`,
  `aggregate_window()`, `window_trend()`, `prune_observations()`. On/off and
  retention are existing platform configuration
  (`smart_core.contract_slo.persist_enabled`, default off;
  `smart_core.contract_slo.retention_days`, default 30).
- `addons/smart_core/handlers/contract_slo_snapshot.py` — read intent
  `smart_core.contract_slo.snapshot` (`MACHINE_ACCESS = "read"`), returning the
  store summary, the window aggregate and the per-version trend. It re-implements
  no rate formula: both come from the pure core.
- `addons/smart_core/handlers/ui_contract_v2_authority.py` — the default delivery
  sink now logs the canonical line and then persists *that same line* when the
  store is enabled, so the store consumes exactly the emission format a reader
  would. Persistence stays fail-open and the explicit-sink path is unchanged.
- `make/dev.mk` — `local.contract-lifecycle.upgrade` (governed module upgrade for
  the isolated profile).
- `make/dev_test.mk` —
  `verify.backend.contract_slo_telemetry[.unit|.emission|.persistence|.runtime]`.

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
- Receipts `slo_core` (33 tests), `slo_emission` (11 tests) and `slo_store`
  (31 tests) all resolve as `reusable` under `make agent.run.resume`.
- `make verify.backend.contract_slo_telemetry.persistence` → PASS, 31 tests
  (22 persistence + 9 retention-cron wiring).
  Receipt `.runtime/agent-runs/BACKEND-CONTRACT-SLO-TELEMETRY/slo_store.json`
  (log `logs/slo_store.log`). The suite covers the identity round trip, an
  unusable row reading back as unreadable rather than as a guessed identity,
  half-open bucket windows, single-bucket placement with an `unplacedObservations`
  counter, the retention cutoff, and asserts the persistence module imports no
  `odoo` module.
- Retention-carrier lock, `scripts/verify/test_contract_slo_retention_cron.py`
  (9 tests): the cron record must target the model derived from the model file's
  own `_name` (so a rename cannot orphan the cron), call a method the model
  actually defines, be active with a bounded interval, be loaded by the manifest
  after the ACLs, delegate to the pure `prune_observations()`, stay fail-open and
  ignore the persist switch. These pin declaration *consumption*, not the
  presence of a file name.
- Negative-first proof, retention carrier
  (`logs/slo_retention_negative_first.log`): after confirming the un-injected
  baseline at 9/9 OK, four separate injections each produced exactly one failure
  — cron shipped inactive, cron data file dropped from the manifest, cron
  pointing at another model, and the sweep no longer delegating to the pure
  helper. The three sources were restored byte-identical
  (`c686ed77…`, `b255b220…`, `0dd7ca53…`) and the suite returned 9/9 OK.
- Runtime emission, on the isolated profile (`local.contract-lifecycle` stack:
  `sc-contract-lifecycle-v1-{odoo,db,redis,nginx}-1`, database
  `sc_contract_lifecycle`, `smart_core` installed, my worktree's `addons`
  mounted into the container so the probe exercises *this* code):
  `make verify.backend.contract_slo_telemetry.runtime` → PASS, probe 24/24
  checks, host guard 8 tests (extended from the earlier 15 checks / 5 guard
  tests when the store checks were added). The production handler delivered a `res.partner`
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
- Runtime persistence, same run: the module was upgraded to
  `17.0.1.1.14` (`make local.contract-lifecycle.upgrade MODULE=smart_core`), which
  created the store table (`0` rows at upgrade time) and registered both ACL
  rows. With the store enabled the production sink wrote exactly one row per
  delivery (`3` rows for `3` deliveries, `0` rejected); the row identity
  round-trips through the model, the store aggregate matches the emission
  aggregate, the trend places all three observations in one bucket, the two
  delivery surfaces stay in separate version rows, the read intent
  `smart_core.contract_slo.snapshot` sees the store (`store=3`, `accepted=3`),
  prune keeps the fresh rows, and the probe restored the original
  `smart_core.contract_slo.persist_enabled` value (`None`, i.e. default off) on
  exit.
- Runtime retention carrier, same probe (now **32/32 checks**, guard **9 tests**):
  the shipped cron exists, is active, targets `sc.contract.slo.observation` and
  calls `model.cron_prune()`. Three rows were planted — one 90 days old, one 29
  days old and one fresh — and the sweep removed exactly the one past the 30-day
  horizon while keeping the other two, so "deletes the old rows" cannot be
  satisfied by "deletes every row". A second sweep returned 0, and the planted
  rows were cleaned up. Readback confirmed the store has zero rows older than the
  horizon afterwards.
- Negative-first proof, runtime retention
  (`logs/slo_retention_runtime_negative_first.log`): after the un-injected
  32/32 baseline, making `cron_prune()` a no-op failed exactly
  `retention_sweep_removes_only_rows_past_the_horizon` (1 probe check) plus the
  guard's retention test; the model file was restored byte-identical
  (`0dd7ca53…`) and the very next run returned 32/32 with no manual cleanup.
  That last part is a fix, not a coincidence: the first attempt at this proof
  left the planted stale row behind and poisoned the *next* run's "prune keeps
  the fresh rows" check, so the probe's planted-row cleanup is now unconditional
  (`finally`), and the injection was re-run to confirm the residue cannot
  survive a failing sweep.
- Negative-first proof, runtime half: after confirming the un-injected baseline
  emitted a valid `success` line, injecting `return False` at the top of
  `emit_delivery_observation` produced zero `contractSlo` lines while the
  delivery still succeeded (`ok=True`, fail-open) and failed 10 probe checks /
  3 host guard tests (`make verify.backend.contract_slo_telemetry.runtime`
  errored). The authority module was restored and verified byte-identical
  (`sha256 e8131205b79181c3fa01501053aa962c2ce21867ca47bf3abcfdde29341897d3`),
  after which the check returned 24/24 and 8/8 again.
- The identity test seals a real contract through `contract_lifecycle` and reads
  the identity back from `meta.lifecycle`, so the SLO identity is bound to the
  emitted evidence rather than to a synthetic dictionary. The suite also asserts
  the core imports no `odoo` module.

### Not delivered (deferred, deliberate)

- Contract-version keying by the published `ui.business.config.contract` version
  number (needs an additive lifecycle field; separate decision).

Durable persistence and the per-version trend read model are now delivered (see
above); they were the only items on this list besides published-version keying.

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

Both halves of this gap are now proven: emission is verified at runtime and
retention is delivered as a durable store, a retention horizon and a
per-version trend read model, all verified on the isolated profile. The horizon
is now *enforced* by a shipped active cron rather than merely declared: before
this increment it had no carrier at all, which is why the store had grown
unbounded. The
**overall** L5 maturity claim is nevertheless intentionally unchanged, because
`docs/architecture/backend_contract_lifecycle_authority_v1.md` still lists
signature-level supply-chain provenance and N-1/N+1 automated compatibility
drills as missing. Only the contract SLO telemetry/trend item is closed in that
document; the L4→L5 statement does not move on this workstream alone.
Publication is on hold by owner instruction.

### Known non-blocking gaps (recorded, not silently dropped)

- **`verify.contract.catalog` is red on this branch and on its baseline.** The
  target regenerates the tracked catalog from the handler AST scan and then
  requires every declared intent to have an authored `intent.invoke` case; any
  intent without one is exported with `inferred_example` and rejected. The
  regenerated catalog flagged **15 pre-existing offenders**
  (`chatter.*`, `payment.request.*`, `project.boq.*`, `search.favorite.delete`)
  whose handler files are **not** in this branch's diff
  (`git diff --name-only c2410190f..HEAD`), so the gate was already red before
  this workstream. The new read intent `smart_core.contract_slo.snapshot` adds a
  16th offender because it has no authored case yet.
  - Decision: the regenerated catalog was **not** committed and the tracked
    `docs/contract/exports/intent_catalog.json` was restored byte-identical
    (`git checkout --`), so the checked-in catalog still passes its own guards.
    Committing inferred examples is exactly what the guard forbids.
  - Closure needs its own topic: author `intent.invoke` cases plus snapshots for
    the declared-but-uncased intents, and decide field determinism for the
    read intent, whose response carries live store counts and trend buckets and
    would not snapshot deterministically as-is. This is repo-wide
    contract-completeness debt, not a defect introduced by the SLO telemetry
    code.

## Catalog completeness closure (owner-authorized topic "a") — CLOSED

The gap recorded immediately above is closed by authoring the missing contract
examples. The verification assertion was **not** relaxed.

### Root cause

`verify.contract.catalog` regenerates the tracked
`docs/contract/exports/intent_catalog.json` from the handler AST scan and then
requires every declared intent to carry an authored `intent.invoke` case. An
intent without one is exported with `inferred_example`, which
`intent_catalog_inferred_guard.py` rejects. This is contract-projection
completeness, not a product defect: the handlers exist and work, they simply had
no authored contract example. The export is atomic, so all offenders had to be
authored in one batch.

### What was authored

15 pre-existing intents plus `smart_core.contract_slo.snapshot`, which this
branch added as a read intent and which was the 16th offender:

`chatter.attachment.delete`, `chatter.followers.list`,
`chatter.followers.update`, `chatter.message.delete`,
`search.favorite.delete`, `smart_core.contract_slo.snapshot`,
`payment.request.settlement.search`, `payment.request.settlement.preview`,
`payment.request.add.settlement.lines`, `project.boq.export.request`,
`project.boq.import.dangerous.preview`, `project.boq.import.dangerous.execute`,
`project.boq.import.preview.fetch`, `project.boq.line.patch`,
`project.overview.rich_text.patch`, `project.dashboard.chart.fetch`.

Named handler files and consumed parameters were read from the handlers
themselves, not from the earlier handoff note: the real names use the
`project.boq.*` / `project.dashboard.*` prefixes, and
`chatter.followers.update` takes `action ∈ {follow, unfollow}` (the note said
add/remove).

### Determinism policy (locked by declaration-consumption, not by string match)

Every case is deterministic and side-effect free against the seeded snapshot
profile:

- reads that return real data bind `sc_test_admin`, the fixture user that holds
  the construction capability groups. `admin` is a platform admin and only
  bypasses `REQUIRED_GROUPS`; it has no construction model ACL, so it produced
  raw `AccessError` 500s for `sc.settlement.order`, `project.boq.version`,
  `project.boq.import.batch` and `project.boq.line`.
- `compare_mode=shape` is used where the payload carries wall-clock buckets
  (`smart_core.contract_slo.snapshot`), `meta.elapsed_ms`
  (`payment.request.settlement.preview`,
  `payment.request.add.settlement.lines`) or freshly minted attachment ids
  (`project.boq.export.request`). Those fields are real contract output and
  cannot be frozen as literals.
- write and gated intents either use a non-existent id or carry
  `allow_error_response`, so the recorded contract is the structured refusal
  (`*_NOT_FOUND`, `MISSING_PARAMS`, `CAPABILITY_DISABLED`) rather than a
  mutation. The `project.boq.import.dangerous.*` pair and
  `project.overview.rich_text.patch` record their feature-flag-off gate, which
  is the deterministic current state of the seeded profile; the flag is not
  flipped, so no runtime configuration authority is introduced.

### Evidence

- `make verify.contract.catalog` → **PASS** on the clean commit `ccd45a4ac`
  (integrity, catalog, case-coverage, inferred, example-shape and
  snapshot-reference guards, plus 13 contract snapshot-principal /
  execute-authority / path tests).
- The 16 new baselines were bootstrapped once
  (`LOCAL_CONTRACT_SNAPSHOT_GATE_ARGS=--bootstrap`) and then re-verified
  **strictly** in a repeated run: **16/16 PASS**, which is what proves the
  determinism policy above rather than a single lucky capture.
- Case authoring was accepted only after the same 16 were confirmed
  reproducible: an initial run showed 4 non-deterministic cases
  (`elapsed_ms`, trend bucket timestamps, attachment id/digest drift), which
  drove the `shape` decisions above.

### Pre-existing drift, bound to identity (not introduced here)

- The tracked `docs/contract/exports/intent_catalog.json` and the tracked
  `docs/contract/snapshots/*` references were last regenerated at `666838f92`
  (2026-08-24, merge PR #283) and are still **identical at the merge base**
  `002b2c64a` (`git diff --stat 002b2c64a HEAD -- <path>` is empty). The
  references are therefore baseline content and their drift predates this
  branch.
- Regenerating the catalog also re-derives per-intent `test_refs` counters; that
  delta (22 changed lines) is the same pre-existing regeneration effect, not a
  new semantic change. Committing the freshly generated artifact is what makes
  the guard reproducible for other executors.

### Scope boundary

`verify.contract.catalog` does not consume the snapshot comparison matrix
(`gate.contract` / `local.contract-snapshot.gate_contract`); it only requires the
referenced `snapshot_file` to exist. Authoring the 16 examples therefore closes
the previously-red catalog gate on its own. The full 151-case snapshot matrix
diff inventory against the stale `666838f92` references is a separate,
pre-existing item and is not part of this closure.
