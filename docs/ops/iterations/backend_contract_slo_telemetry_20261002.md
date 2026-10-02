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

#### Matrix completion probe (bounded, out of scope, recorded for the owner)

One bounded full-matrix run was attempted on the seeded snapshot profile and it
**aborts at case 21**. This is diagnostic only and does not affect the closure
above, but the exact cause matters for whoever owns fixture hygiene:

- 20 cases export, then `my_work_complete_batch_pm` fails with
  `{'code': 409, 'reason_code': 'IDEMPOTENCY_CONFLICT'}`. The case is unmodified
  by this branch (`git diff 002b2c64a HEAD -- docs/contract/cases.yml` contains
  no reference to it) and has no `allow_error_response`, so the 409 is fatal.
- Root cause is **seed residue, not this change**: `sc.idempotency.record`
  holds exactly one row, `idempotency_key = snapshot_my_work_batch_1`,
  `create_date = 2026-09-08 10:54:18` — weeks before this session, and carried
  in by the read-only seed from the registered `sc-local-dev` / `sc_dev_demo`
  source. That record is also proof that the idempotency store commits
  independently of the exporting transaction, so a replayed fixed
  `request_id` can never export twice from a DB seeded off a prior run.
- A separate stale-fixture class exists as well: cases such as
  `execute_button_not_allowed` (`demo_role_pm`, `--op model`) fail against the
  current fixture expectations. (An interleaved log from a previously killed
  attempt made this look like an earlier abort; the ordered export list confirms
  the run reached case 21 before stopping.)
- Consequence: the full matrix can only become a usable gate after seed/fixture
  hygiene work (unique per-run `request_id`s, or a seed without committed
  idempotency state). Recording it is in scope; repairing it is not, and it is
  not needed to close the catalog gate, which is evaluated offline.

## Owner topic (d): contract-snapshot seed/fixture hygiene (2026-10-02)

Owner authorized item (d). Result, evidence and the decision that is still open
are recorded here; no gate or assertion was relaxed.

### Fix (P4 tooling, `c8d87495c`)

- `scripts/dev/local_contract_snapshot_seed.sh` now purges the transient
  run-state tables right after `pg_restore` and proves each one is empty
  (`cleared transient table=sc_idempotency_record rows=0`). A baseline dataset
  has to be operation-free; the dump's committed idempotency state is exactly
  what turned the case's first-call baseline into a 409.
- The same script now fails closed when the target `odoo` is running. The
  restore replaces the whole database, and a live Odoo made the `--clean` DROP
  fail, leaving a half-restored target (`duplicate key ... res_company_pkey`,
  `multiple primary keys ... res_users`). Observed first hand; the guard now
  refuses with a pointer to `local.contract-snapshot.rebuild`, which takes the
  profile down first.
- `local.contract-snapshot.matrix_audit` (+ `scripts/dev/local_contract_snapshot_matrix_audit.sh`)
  is a bounded diagnostic that reuses the same per-case export with `CASE_ONLY`
  and keeps going, so one run lists every failing case. The gate itself stays
  fail-fast and is unchanged; this entry is not evidence of a pass.

### Verification (identity-bound)

- Profile identity: `sc-contract-snapshot-v1` / `sc_contract_snapshot` /
  `^sc_contract_snapshot$` / nginx `18091` / odoo `8080`; rebuilt seed
  `seed_dump_sha256=529bdcd670883b4db127589d27bc84bfe3dd57897c1cce4d3d13dfb6d270824c`;
  `smart_core 17.0.1.1.14`, `smart_construction_core 17.0.0.169`.
- Before the fix, the bounded audit on the previously seeded profile:
  **150 PASS / 1 FAIL** — the only export failure in the whole matrix was
  `my_work_complete_batch_pm`.
- After the fix (`make local.contract-snapshot.seed` inside
  `local.contract-snapshot.rebuild`), `sc_idempotency_record` is empty and
  `make local.contract-snapshot.gate_contract` runs the export **to
  completion**: all **151** cases produced a snapshot, `0 MISSING_BASELINE`,
  and the comparison reports **32 PASS / 119 FAIL**. The previous abort at case
  21 is gone.

### Correction to the probe note above

The earlier "separate stale-fixture class (`execute_button_not_allowed`,
`demo_role_pm`, `--op model`)" claim was wrong. The audit shows it exports
fine; it appears only as a comparison diff against its reference. The
151-case matrix has exactly one export-stage defect, and it is now fixed.

### Classification of the 119 remaining diffs (not a fixture defect)

- **44** differ **only** by `-contract_version` / `+snapshot_schema_version`:
  identical behaviour, renamed envelope key.
- **75** carry content drift. Examples: `permission_check_intent_admin` embeds
  the capturing database (`debug.db` = `sc_dev_demo` in the reference,
  `sc_contract_snapshot` now); `my_work_complete_batch_pm`'s
  `idempotency_fingerprint` differs; `app_catalog_intent_admin` lists 4 apps in
  the reference and 28 now.
- The tracked references are heterogeneous: **46** already carry
  `snapshot_schema_version` (introduced in `c0a6e9e2c`, PR #277) while **114**
  still carry `contract_version`, so roughly 114 references predate PR #277.
  This is the pre-existing reference staleness the catalog topic already
  recorded, now quantified per case.

### Single-shot property (recorded, by design)

The gate run re-created the idempotency row (`id=48`, `2026-10-02`), so a second
full run on the same profile fails case 21 again: matrix cases perform writes
and the case declares a fixed `request_id`. A full matrix run is therefore
**single-shot per freshly seeded profile**. `make/dev.mk` now records that
precondition on the gate entry and points at `local.contract-snapshot.rebuild`.

### Still open (owner decision)

Re-baselining the 119 (`LOCAL_CONTRACT_SNAPSHOT_GATE_ARGS=--bootstrap`) would
declare today's behaviour as the new reference. That is a contract-authority
decision, not hygiene, so it was **not** taken here.


## Owner topic (b): SLO keying by the published ui.business.config.contract version (2026-10-02)

Owner decision restated: **fix the contract-projection defect and do not relax the
acceptance assertion.** Keep the SLO grouped by the *applied published* contract
version, derive it where it is already declared, and do not add a payment-model
special case or let a `critical` flag override ACL, field-permission or a legitimate
hidden rule.

### Root cause / gap (verified before editing)

`addons/smart_core/core/contract_slo_telemetry.py` already declares the optional
`publishedVersionRef` inside `GROUPING_FIELDS`, so version-scoped aggregation was
implemented and tested — but **no producer ever emitted it**, so every real delivery
was aggregated with the field absent and the "by version" claim had no carrier.

The applied published contract version co-varies with the delivery and is *already
declared* in `governance.view_orchestration` / `source_trace.view_orchestration`
(flat `business_config_contracts` plus the per-view summary
`views.<view_type>.business_config_contracts`), written by
`addons/smart_core/core/view_orchestrator.py` and
`app_config_engine/services/assemblers/page_assembler.py:_inject_view_orchestration_summary`.
The reference is therefore derivable at the single seal chokepoint with **zero
call-site churn** — no new protocol, no new field on the delivery, no producer
rewrite.

### What changed

- `addons/smart_core/core/view_orchestration_contract.py` — declared-carrier reader
  only: `view_type_candidates` (list↔tree alias), `applied_business_config_contracts`,
  `business_config_contract_ref`, `resolve_published_version_ref`, plus the
  `BUSINESS_CONFIG_CONTRACT_MODEL` / `BUSINESS_CONFIG_CONTRACT_PUBLISHED_SOURCE_KIND`
  constants. It reads *only* declared carriers (`governance`, `source_trace`,
  `runtimeContract.governance`), prefers the matching `views.<view_type>` entry and
  falls back to the flat list.
- `addons/smart_core/core/contract_lifecycle.py` — `build_lifecycle_evidence(...,
  published_version_ref="")` and `seal_unified_page_contract(...,
  published_version_ref="")` add `definition["publishedVersionRef"]` **only when it is
  non-empty**, so an unattributed delivery stays byte-identical and keeps the same
  `contractSha256`. `UNIFIED_PAGE_SCHEMA_SHA256` regenerated through
  `scripts/verify/contract_schema_declaration_sync.py` to
  `204b8f6c4e3ea78800073811f4fd74846a3c33caa55655b62fdc9b171f613b94`.
- `addons/smart_core/handlers/ui_contract_v2_authority.py` — private
  `_delivered_view_type` / `_published_version_ref` helpers, resolved at the single
  `seal_runtime_contract` chokepoint (source payload first, then the assembled
  contract). File sha256 `68e182a26c26402e9f1822d9d48ba55c5301a6405c91f24615b93529872996de`.
- `docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json` —
  optional `contractLifecycleDefinition.properties.publishedVersionRef`
  (`type: string`, `minLength: 1`), deliberately **not** in `required`; the
  `lifecycleVersion` / `schemaVersion` / `contractVersion` consts are unchanged.
- `scripts/verify/contract_v2_render_authority_matrix.py` +
  `docs/frontend_productization/rendering-detail/contract-v2-render-authority-matrix-v1.json`
  — the new key is classified (regenerated: 327 fields, 0 unclassified).
- `frontend/apps/web/src/app/contracts/v2/types.ts` + `schema.ts` — optional
  `publishedVersionRef` on `ContractV2Lifecycle.definition` and a new
  `decodeLifecycleDefinition()` using `optionalStringField`; the unknown-key
  rejection still fails closed. File sha256
  `74271214a1f53dbebace4dbb78bdb3978881ff8b87f0ac533e98d8e63649cfcc`.
- `addons/smart_core/tests/test_contract_lifecycle.py` — 3 tests: absent ref is
  omitted, blank ref is omitted, a ref is additive and preserves `contractSha256`
  with a valid integrity block (8 tests total).
- `scripts/verify/test_ui_contract_v2_slo_emission.py` — new
  `PublishedVersionAttributionTest` (10 tests, 23 total) driven through the real
  `seal_runtime_contract` chokepoint with an injected sink.
- `frontend/apps/web/scripts/contract_v2_runtime_policy_test.ts` — 3 declared policy
  cases (attribute present; unattributed must not gain the ref; an undeclared
  `definition` key still fails closed).

### Reference string and the exclusion rule

Natural, authority-carrying reference: `<model>:<id>@<version_no>`, e.g.
`ui.business.config.contract:22@2`. Several applied published rows are sorted and
joined with `,` so the identity is order-independent. Rows whose `source_kind` is not
`published` (for example an id `0` `change_set_preview`) are **excluded**, so an
unattributed delivery can never borrow a preview/edit-state contract identifier.

### Evidence (all zero-non-zero, all recorded as receipts in the run)

| layer | command | result |
| --- | --- | --- |
| L2 offline | `make verify.backend.contract_slo_telemetry.emission` | 23 tests OK (`slo_emission`) |
| L2 offline | `make verify.backend.contract_lifecycle.authority` | 8 + 10 + 4 + 13 tests OK, guard `score 100`, `maturityLevel L4_governed_production_ready` (`contract_lifecycle_authority`) |
| L2 frontend | `make verify.frontend.contract_v2_render_authority.unit` | PASS, 327 fields / 0 unclassified (`v2_render_authority`) |
| L2 frontend | `make verify.frontend.contract_v2_runtime_policy.unit` | PASS, 12 declared cases (`fe_v2_runtime_policy`) |
| L2 runtime | `make verify.backend.contract_slo_telemetry.runtime` | probe 43/43 checks (baseline + persistence + retention + published-version attribution), host guard 11 tests OK (`slo_runtime`) |
| L1 static | `make verify.frontend.typecheck.strict` | PASS, exit 0 (25.2s). No unittest count is printed by `vue-tsc`, so it is recorded here and in the log rather than as a receipt. |
| L2 offline | `make verify.contract.catalog` | PASS, 16 tests (`contract_catalog`, see bookkeeping) |

### Negative-first proofs (each restored byte-identical afterwards)

- Neutering the `published_version_ref=_published_version_ref(...)` wiring at the seal
  chokepoint fails 5 tests and errors 2 in `test_ui_contract_v2_slo_emission`, so the
  attribution tests detect the removed behaviour rather than passing unconditionally.
- Reverting the decoder's allowed key makes the runtime-policy test fail with
  `meta.lifecycle.definition.publishedVersionRef is not allowed`, so the frontend half
  fails closed on the new key being undeclared.

### Snapshot-matrix impact measured as zero

The seal change is bounded by reference inspection alone: only 1 of the 151 stored
contract references (`ui_contract_v2_intent_admin.json`) contains a sealed
`meta.lifecycle`, and it is already inside the 119 reference diffs recorded under
topic (d). Adding `publishedVersionRef` only to the definition of a delivery that
actually carries applied published rows cannot turn a matching reference into a
differing one, so the 119-diff inventory is untouched and was not re-run for it.
The other four refs that carry a bare `lifecycle` key are business state machines
(`allowed_transitions` / `steps`), not sealed envelopes.

The later carrier fix (see below) needed a real measurement rather than reference
inspection, because it can add rows to an already-emitted dict. Bounds, both
recorded in `.runtime/agent-runs/BACKEND-CONTRACT-SLO-TELEMETRY/probe/
view_orchestration_matrix_impact.py`:

- Only 4 of 151 references contain any `view_orchestration`, and all 4
  (`load_contract_intent_admin`, `load_view_intent_pm`, `system_init_intent_admin`,
  `ui_contract_v2_intent_admin`) are already inside the 119 diffs. The 147 refs
  without the key cover every PASS case, and a PASS case matches its reference
  exactly, so it cannot start differing unless `compose` starts emitting the key —
  which this change does not do; it only changes the content of an already-emitted
  dict.
- For the two references that actually carry `business_config_contracts` rows, the
  same case was exported twice against the registered `sc-contract-snapshot-v1`
  profile, once with the fix and once with `view_orchestrator.compose` reverted to
  the pre-fix guard: **0 differences inside `view_orchestration`** (155 and 255
  carrier paths compared). A same-code rerun reproduces the only difference at the
  same magnitude, so it is not caused by this change.

Separate, pre-existing matrix-stability observation (not introduced or fixed here):
the exported `task_ids` stage-domain ordering is not deterministic. Two runs of
*identical* code produce 28 differing leaf paths
(`ui_contract_raw/.../task_ids/domain[0][2][n]`), which is why the reference
comparison is inherently flaky for the affected cases. It touches no file changed by
this branch.

### Runtime half: what it proves and what it does not

On the isolated profile `sc-contract-lifecycle-v1` / `sc_contract_lifecycle` the
production handler emitted real `contractSlo` lines that the declaration consumer
accepted unchanged: 3 observations, 0 rejected, `versionCount 2`, `successRate 1.0`,
`integrityFailureRate 0.0`, and `publishedVersionRef` occurrences **0**. That equality
with the pre-change aggregate is the point: an unattributed delivery still groups
exactly as before, so the new key is purely additive.

### Runtime attribution closed: the producer was the defect, not the resolver

The isolated fixture held **zero** `ui.business.config.contract` rows (read-only
evidence, `.runtime/agent-runs/BACKEND-CONTRACT-SLO-TELEMETRY/probe/q_published.py` ->
`COUNT=0 ALL=0`), so the first attempt at runtime attribution published one row
(bounded P4 probe extension, now authorized) and delivered against it. The probe came
back red and the reason is the actual root cause of this topic:

`addons/smart_core/core/view_orchestrator.py:compose()` only appended a row to
`applied_contracts` when
`out != before or declares_form_layout_overlay or declares_semantic_entry_surface or
declares_native_semantic_surface`. A published row that declares only
`views.form.fields` (which `_apply_business_config_contract` normalises so that
`out == before` whenever the declared fields already match the native form) qualified
for **none** of those, so it was selected by `_effective_view_orchestration_contracts`,
applied to the delivery, and still left the declared carrier as
`{"applied": false, "business_config_contracts": []}`. The reader side was correct: it
read the declared carrier and returned the empty string, because the carrier was
empty. A read-only spy (`.runtime/.../probe/spy_attribution.py`) proved the row was
effective and its fields applied, and that the SLO resolver returned `''`.

Fix (generic, no model/view special case): record **every** row returned by
`_effective_view_orchestration_contracts` in the declared carrier, exactly once
(de-duplicated by id, as before), outside the change guard. That list *is* the
declared "which published rows governed this delivery" carrier by construction, so a
field-policy-only contract is now attributed like a structural one. The
`applied` flag follows the same list
(`applied = bool(applied_contracts or legacy_policy_applied or tenant_extension_fields)`),
so a surface with a selected published row no longer contradicts its own field set by
reporting `applied: false`. The form-structure projection is unaffected in which
branch it takes: `resolve_form_structure_governance` already computed `applied` from
`config_summaries`, which is populated from the same selected rows.

Two accessors are deliberately different and were both exercised: the emitted
observation nests the reference under `identity.publishedVersionRef`, while an
aggregate version row exposes it flat (`row["publishedVersionRef"]`), which is what
the existing `slo_core` unit test already asserts.

Files: `addons/smart_core/core/view_orchestrator.py` (carrier producer, one hunk
plus a now-dead `before = deepcopy(out)` removed) and the two probe files
`scripts/verify/contract_slo_telemetry_runtime_probe.py` /
`scripts/verify/contract_slo_telemetry_runtime_probe_schema_guard.py`. The probe
extension adds `_capture_delivery`, `_run_published_version_attribution` and the
`attribution` section; the guard adds an `importlib` loader for the real telemetry
core plus 11 required check names and two tests
(`test_published_version_attribution_is_really_keyed`,
`test_the_attribution_fixture_was_restored`).

Layer commit: `85526530e` on `fix/contract-slo-telemetry`, parent `aec885fac`. It
changes no protocol version, no Odoo model/field and no XML, so no module upgrade is
implied; the runtime half again ran through a fresh governed `odoo shell` process
reading this worktree's addons mount. Because the commit adds host guard tests, the
tracked generated reports were refreshed through `make ci.delivery.freeze.prepare` and
are committed with the record; that refresh also caught up pre-existing staleness from
earlier commits on this branch (`test_inventory`, `complexity_budget_report`,
`module_dependency_map`, `split_plan_queue`, `component-driver-takeover-inventory-v1`),
which is bookkeeping, not a behaviour change.

Evidence (receipt `slo_runtime`, probe 43/43 checks and 11 host guard tests):

| check | observed |
| --- | --- |
| `published_contract_row_is_published` / `published_contract_contributes_form_only` | row published; contributes `form`, not `list` |
| `delivery_on_published_form_names_the_version` | `formRef == ui.business.config.contract:<id>@1` |
| `another_surface_does_not_borrow_the_version` | `listRef == ''` |
| `aggregate_splits_the_published_version_from_unattributed` | `versionCount 2`, 1 attributed + 1 unattributed row, 1 observation each |
| `probe_contract_removed` / `mutation_audit_left_clean` | no contract row and no `ui.business.config.mutation.audit` row left behind |
| `delivery_after_removal_is_unattributed_again` | `afterRemovalRef == ''` |

Negative-first, in the required order: the un-injected baseline passes first, then
reverting only the carrier fix (back to the change guard) makes the probe fail exactly
two checks — `delivery_on_published_form_names_the_version` and
`aggregate_splits_the_published_version_from_unattributed` — and the file was restored
byte-identical (sha256 `e69f8a26827586d5fb79d4009f6225441dada938bfac28bb4a9d3baf2c147808`).
So the added checks fail on the removed behaviour rather than passing unconditionally.
The probe's own fixture discipline is part of the assertion: the row is created and
unlinked inside the mutation-audit skip context, and removal plus audit cleanliness are
asserted rather than assumed, so a repeated probe leaves no residue.

### Bookkeeping

The added test reference moved the tracked `ui.contract` `test_refs` counter
**128 -> 129** in `docs/contract/exports/intent_catalog.json`. The catalog was
regenerated by `contract.catalog.export` inside `verify.contract.catalog` and the
guards validated the regenerated artifact in the same run, so the tracked export stays
consistent with the tests that exist. `scene_catalog.json` is unchanged.

### Layer commit

`7665827b55014eb0a365db8061528cdbaa90ca8b` on `fix/contract-slo-telemetry`, parent
`3f17e031d`. It changes no protocol version, no Odoo model/field and no XML, so no
module upgrade is implied. The runtime half ran through a fresh `odoo shell` process
(the governed `odoo_shell_exec.sh` entry) that imports this worktree's
`/mnt/source-addons` mount, which is why the changed code was live without a service
restart; the profile still reports `smart_core 17.0.1.1.14`.

## Topic (c) — L5 供应链证明与 N-1/N+1 兼容演练

边界：Formal Product Layer = P0（`smart_core` 契约机制）+ P4（验证工具）；按权威文档 §6
作为独立专题推进，不并入客户交付。这是该 run 剩余的两项 L5 缺口（-2 供应链统一证明、
-3 N-1/N+1 兼容与回滚演练）。

### Part A：统一供应链证明（签名 + 制品证明 + 部署运行 SHA）

新增 P0 纯标准库核心 `addons/smart_core/core/contract_supply_chain_attestation.py`：

- 主体绑定三枚 64-hex 内容摘要（`schemaSha256` / `contractSha256` / `artifactSha256`）与
  40-hex `deploymentRuntimeSha`，用有序 `chain` 做摘要链接（`required_subject_hash_fields()`
  是消费方读取的声明，不是重复的字符串清单）；
- 统一不变量（“统一”之所在）：`artifactSourceRevision == sourceRevision`，否则
  `artifact_revision_mismatch`；`deploymentRuntimeSha == sourceRevision`，否则
  `deployment_runtime_sha_mismatch`；
- 签名信封被 `attestationDigest` 覆盖；方案 `hmac-sha256`（密钥、不可公开）与注册的
  `ed25519`（公钥）；`require_public_key=true` 时拒绝密钥方案。

离线锁 `scripts/verify/test_contract_supply_chain_attestation.py`（19）：基线先通过，再逐个
注入单一篡改并断言对应 reason code（含 `_reseal()` 隔离签名路径、非对称方案注册、AST
无 Odoo 依赖）。

运行半 `scripts/verify/contract_supply_chain_runtime_probe.py`（14 checks）在隔离 profile 上
对真实运行部署构建证明：schema 摘要取自生命周期权威、契约摘要取自真实 `ui.contract.v2`
交付、制品摘要从容器**已加载**的模块文件重算、部署 SHA 取自受管 `SC_SOURCE_REVISION`，
用进程内临时 Ed25519 自签。宿主侧
`scripts/verify/contract_supply_chain_runtime_probe_schema_guard.py`（12 测试）用真实 Ed25519
独立复核并重导链绑定，探针自己的 PASS 标记不作为证明。

受管入口 `make verify.backend.contract_supply_chain.runtime`（另含 `.unit`、
`.compatibility.unit`、`.runtime.schema.guard`）。

环境前置：`.env.local.contract-lifecycle` 原无 `SC_SOURCE_REVISION`，容器报 `unknown`。
`scripts/dev/local_contract_lifecycle_env_prepare.sh` 现解析并刷新 40-hex 部署版本
（`CONTRACT_LIFECYCLE_SOURCE_REVISION`，默认本工作区 HEAD，`make/dev.mk` 传入），随后一次
**定向** `make local.contract-lifecycle.up` 重建 odoo 服务使 env 生效——这是对既有隔离
profile 的受管重建，非新环境/新凭据授权。

证据：探针 14/14、宿主 guard 12/12；`sourceRevision = 593de9de6ccc9f0e6ec47fd45c90d3a540cdeb71`，
`schemaSha256 = 204b8f6c…`。信任边界：自签证明可证制品—版本—运行一致性与抗篡改，但未引入
外部身份/信任锚，**不能**证明“谁构建了制品”——该残余在权威文档 §5 记为保留的 -1。

### Part B：N-1/N+1 兼容与只追加回滚演练（声明级离线）

新增 P0 纯标准库核心 `addons/smart_core/core/contract_version_compatibility.py`：
`compare_declarations`（删键、新增必填、类型变更、收窄必填、闭枚举移除/新增判 breaking；
开放枚举新增成员为 additive）、`check_consumer`（未知键容忍、缺必填/类型不符/越界枚举拒绝）、
`drill_adjacent`（N-1/N/N+1 双向矩阵，输出具名检查）、`append_only_rollback`、
`declaration_from_payload`（把真实 payload 的键面投影为消费者声明，默认全部可选）。

决策：**保持声明级离线，不做运行半**。理由：(1) 运行侧发布/回滚语义已由既有
`contract_lifecycle_authority`（35）与 `slo_runtime` 的发布版本归因证据覆盖，重复运行需要
受管可恢复夹具且会重证已证行为；(2) 本专题的判定是纯数据，正确性完全由离线判定；
(3) 演练输入取真实 `ui.contract.v2` 信封键面投影并把只追加规则绑定到发布权威
`max(cur, latest)+1`（`ui_business_config_contract._append_published_version`）的语义，避免仅
玩具夹具的循环论证。

离线锁 `scripts/verify/test_contract_version_compatibility.py`（31）：基线（加法演进演练通过、
`check_names()` 声明消费被锁定、真实信封键面投影）先通过；负例（注入 breaking 变更、移除键、
复用/回退版本序列）再被检出。

修复记录：投影原先把空嵌套对象当作独立可选键声明，使“移除叶路径”的 breaking 结论被
`optional_key_added` 噪声排到 findings[0]。按通用规则修复——空映射不声明任何叶面（不特判
模型/视图）——`a.b` 的移除重新成为唯一且正确的 breaking finding。

### 与既有工具的关系（非重复）

既有 `scripts/verify/contract_version_evolution_drill.py` 是对**运行中服务**的活体非回归检查：
它断言 envelope/meta 必需键存在且 `api_version` / `contract_version` 不倒退。它不做相邻版本
声明差分，也不做只追加回滚演练。本专题的 `contract_version_compatibility` 是**决策层**核心
（声明级 N-1/N/N+1 差分与回滚规则），二者互补而非重复：活体演练证明“当前运行不倒退”，
决策核心证明“相邻版本的兼容分类与回滚序列正确”。因此不合并、不互相替代。

### Layer commit

`d8827e63739cfa34361a4ed9d1c018298d9c3ab4` on `fix/contract-slo-telemetry`. It adds two
pure-standard-library P0 cores, four verification assets, the four governed Make entries, the
deploy-revision injection in the governed env-prep, and the record/authority-doc updates plus the
refreshed tracked generated reports. It changes no protocol version, no Odoo model/field and no XML,
so no module upgrade is implied; the runtime half ran through a fresh governed `odoo shell` process
reading this worktree's addons mount, which is why the attestation's recomputed artifact digest
reflects the live code. The signature is self-signed, so this commit closes the -2 item's unified
binding and leaves the external trust root open; L5 is not declared.

## Integration status after PR #533 and the topic (c) carry (2026-10-02)

Topics (a) intent-catalog completeness, (b) published `ui.business.config.contract`
version keying and (d) contract-snapshot seed/fixture hygiene, together with the
contained `BACKEND-CONTRACT-L4-CLOSURE` batch, were integrated into `main` by PR #533
(squash merge `9abaa79d9876721c0f1b1236ee542cb898e4c66a`, carried by
`CONTRACT-BATCHES-MAINLINE-INTEGRATION`). That batch also re-ran the L4 runtime lane on
the restored isolated profile at the integration head — 14/14 assertions, schema guard
PASS, rotted identity pins realigned — recorded in
`docs/ops/iterations/contract_batches_mainline_integration_20261002.md`. Because the
merge is a squash, this branch's own commit history is not an ancestor of `main`:
integration is by content, and `main`'s newer versions of the shared files stay
authoritative over this branch's pre-merge snapshot.

Topic (c) — signature-level supply-chain provenance and the N-1/N+1
consumer-compatibility drill, delivered by this record's last layer commit `d8827e637` —
was **not** part of that merge. It is carried onto the current `main` baseline
`e93b5e83f` as one candidate on branch `fix/contract-supply-chain-attestation`, under
goal `BACKEND-CONTRACT-SUPPLY-CHAIN-ATTESTATION`
(record: `docs/ops/iterations/backend_contract_supply_chain_attestation_20261002.md`).

Still open and owner-gated: (b-residual) the runtime-attribution probe extension; (e) the
re-baseline decision for the 119 stale snapshot references; and the topic (c) external
trust root — the attestation is self-signed, so L5 is still not declared. Deployment,
version release and product delivery stay separate and unauthorized.
