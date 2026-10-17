# Performance Baseline Governance

## Purpose

This document defines how performance baseline numbers are produced and consumed by regression gates.

## Baseline Metadata (Required)

- Baseline source report: `artifacts/backend/platform_sla_report.json`
- Baseline commit/tag: must be recorded in PR/Release notes when baseline is refreshed.
- Baseline environment:
  - DB name
  - role/login used
  - host/container mode
  - cache state policy (cold/warm)

## Sampling Policy

- Warmup requests per round: default `20`
- Measured rounds: default `3`
- Iterations per round:
  - `system.init`: `200`
  - `ui.contract`: `200`
  - `execute_button`: `1000`
- Metrics:
  - `P50`, `P95`, `P99`, `max`, `variance`
  - status/error rate

## Regression Grading

- `PASS`: all rounds under warn threshold, error rate `0`
- `WARN`: threshold warning exceeded in one or more rounds, but fail criteria not met
- `FAIL`:
  - non-2xx status exists, or
  - fail-threshold exceeded in at least `2/3` rounds (configurable)

## Threshold Policy

- Generic fail threshold: `max(baseline*1.10, baseline+abs_delta)`
- Generic warn threshold: `max(baseline*1.05, baseline+warn_abs_delta)`
- `execute_button` uses extra absolute floor (default fail floor `80ms`) to reduce noise sensitivity.

## Baseline Refresh Rule

Refresh baseline only when:

1. major infra/runtime condition changed, or
2. validated performance improvement is accepted.

Any baseline refresh must include:

- previous vs new baseline diff
- reason for refresh
- exact command and environment notes

## Extended Baseline Carrier (2026-10-16)

The sampling policy, regression grading and threshold policy above are unchanged and still
grade the SLA-guard numbers in `artifacts/backend/platform_sla_report.json`.

A separate normalized carrier now records broader runtime observations without redefining
those thresholds:

- engine: `scripts/verify/system_performance_baseline.py` (schema `system-performance-baseline/v1`)
- managed collection: `make local.dev.runtime.performance.baseline`
- unit test: `make verify.system.performance.baseline.unit`
- record: `artifacts/backend/system_performance_baseline.json`; view: `docs/ops/audit/system_performance_baseline.md`
- rules: missing timings are recorded as gaps and never as zero; nested stage values are never
  summed; the observed and retained sample counts must agree
- layers: `controlled_regression` / `daily_experience` / `capacity`, each independently
  satisfied; `daily_experience` stays `not_run` and `capacity` stays `target_unresolved` until
  their identities are confirmed

`platform-sla-guard/v1` declares no product-code hash, so its layer identity stays `unknown` by
design and it is not a controlled-regression identity carrier.

### Mature-System Benchmark Targets (2026-10-16)

The SLA thresholds above grade this system against its own history; they are not the product
target. A machine-checked declaration now records the published external bar the same operations
are judged against, so "benchmark against mature systems" is evidence rather than prose.

- declaration: `BENCHMARK_SOURCES` / `BENCHMARK_LADDER` / `MATURE_SYSTEM_TARGETS` inside
  `scripts/verify/system_performance_baseline.py`, schema `mature-system-performance-targets/v1`
- external references: RAIL (`0-100 ms` instant), Core Web Vitals INP (`p75 <= 200 ms` good),
  Nielsen Norman Group (`0.1 / 1.0 / 10 s`), TTFB (`<= 800 ms` good), LCP (`<= 2.5 s` good),
  Salesforce EPT (healthy `< 3 s`), SAP Fiori Timing (`1-3 s`; `> 3 s` disrupts flow)
- every target cites at least one reference and its `target_ms` must equal its ladder tier budget;
  an unknown source, a mismatched budget or a tolerance below the target fails closed
- verdicts: `met` / `within_tolerance` / `failed` / `not_evaluated`; a target without supporting
  samples is `not_evaluated`, never a pass and never a zero
- the historical SLA budget for the same intent is reported beside each target as
  `historical_budget_ms` with `historical_budget_vs_target_ratio`, so gate looseness is measured
- this layer does not relax or replace the SLA budgets, and is not a capacity, SLO or production
  acceptance; `capacity` stays `target_unresolved`

### First-Call Cost Boundary (2026-10-16)

The process-first hard breach needs a finer split than "the first call is expensive": a provable
process-level one-time initialization must be separated from the first cache build plus first
assembly, and neither may be inferred from a model name.

- capture: `_canonical_sample` keeps `profile_top` (top 40 cumulative frames); only a
  profile-bearing sample can carry the annotation, so a missing profile is `not_declared`
- markers: `FIRST_CALL_ONE_TIME_MARKERS` matches `translate.py` / `polib.py`
  (`odoo_code_translation_load`); `one_time_process_init` takes the MAX cumulative of matched
  marker frames and never sums nested frames; the annotation is attached only to targets declared
  `first_call_boundary`
- attribution (this round): of the 3593.4 ms process-first assembly only 560.26 ms (15.6%) is a
  provable one-time process initialization, all of it Odoo code-translation (PO) loading via
  `_get_code_translations` 524.83 ms then `polib.parse` 472.89 ms
- the `res.currency` ~540 ms is `res_currency.py:332 _get_view` 523.68 ms, the outer frame of that
  same one-time load and NOT a model cost; it must not be special-cased per model and must not be
  credited to on-demand materialization
- the remaining approx 3033 ms is first native view read plus first contract compile / relation
  dialog assembly; those frames are nested (`stage_sum_forbidden`) and are not additive; the same
  flow drops to 143.97 ms on the second request and 197.204 ms on a cold rebuild
- consequence: the breach is neither "process init" as a whole nor a steady-state per-request
  cost, so the legitimate follow-up directions are warming the first view read / first contract
  compile, or the steady-state assembly algorithm itself

### Role-Dimension Contract Variation (2026-10-16)

A single-principal baseline cannot see whether the contract surface, the navigation capability or the
per-role cost varies. The role dimension is therefore captured by one read-only probe and folded into
the same normalizer and the same record; nothing is re-derived, averaged or relaxed.

- probe: `scripts/verify/local_dev_runtime_contract_role_matrix_probe.py`, reached through
  `make local.dev.runtime.contract_role_matrix.probe` and, inside the baseline shell,
  `PRODUCT_PERFORMANCE_BASELINE_SOURCES=role_matrix`; 9 declared demo principals, a fixed action (878)
  and two declared cases (`list_action_open`, `form_action_open`)
- isolation: the `form` case uses the first `payment.request` record readable by the acting principal;
  a principal with no readable record is recorded `unavailable` and the case is skipped instead of
  borrowing another role's record. The `cold_role` phase clears only the process-local
  `CONTRACT_PROJECTION_HOT_CACHE`; native views and translations stay hot so a one-time load is never
  charged to a role
- refusal semantics: a gate denial is `denied_by_permission`, a raised/`ok=false` handler is
  `handler_error`, and the two are never merged; `refused_roles_never_report_a_contract` must stay true
- what this round observed: contract identity, contract surface and the relation surface vary by role;
  the surface digest is stable across a dispatched role's hot repeats, so the differences are
  role-driven and not noise. Navigation capability is role-driven: only `role_finance` holds the
  released menu carrier for action 878, and in the `form` case all four dispatched roles materialize
  the same three relation targets and three search dialogs while only `role_finance` carries
  navigation authority (`with_navigation_authority` 3 vs 0)
- rejections stay explicit: `list_action_open` dispatched 6 / refused 3 / unavailable 0 (the three
  refusals fail closed because the `requests`/`payment.request` search view is not resolvable);
  `form_action_open` dispatched 4 / refused 0 / unavailable 5
- accounting: every role/case sample is retained with its own label, so a sample can never be dropped
  to make a role look cheap; the role entry is `96/96` with `identity_match=match` and the record stays
  `status=baseline gaps=0 samples=142/142`
- scope limits: this is a role-dimension slice at one fixed action, not a per-menu or per-model
  capacity claim; it does not close the performance topic and does not prove any R2/R3/R4 gain, and it
  does not relax the mature-system targets, the historical SLA budgets or `capacity=target_unresolved`

### Profiler Perturbation Isolation (2026-10-16)

- measured: the same request alternated profiled / unprofiled in one environment gives a profiled
  first call of `3814.6 ms` versus an unprofiled first call of `1962.52 ms` with an identical SQL
  count of 1040 (approx `1.94x`), and hot median-to-median `148.74` versus `76.35 ms` (approx `1.95x`)
- rule: a profiled sample is an analysis instrument only. It must not be used as a baseline value and
  must not be compared against an HTTP or browser number; a before/after comparison must hold the
  sampling mode fixed and be reported separately from unprofiled steady state
- rule: profiling adds no SQL. If the SQL count differs, the query difference must be explained
  first; profiler overhead is never the explanation for a query count change
- registration: `backend_runtime_investigation.profiler_inflation_calibration` keeps the paired
  evidence paths and hashes so a later executor reuses this calibration instead of re-measuring it

### Preference Path Leaves Page Assembly (R5, 2026-10-17)

- attribution: a preference read could reach the full page assembler (observed 27
  `get_contract_api/build_final_contract` calls and 24 relation search-dialog builds per read). R5 separates
  the preference identity from assembly instead of special-casing a model
- identity is enforced server-side: an illegal identity is `400`, missing read access is `403`, an
  unresolvable declared surface is `422`, and the SET path resolves the policy before it writes, so it can
  never persist an invalid or mismatched identity. `build_scope_key` now raises when neither `action_id` nor
  `model` resolves, so the legacy `model:unknown` sentinel can no longer be persisted
- stored reads return storage facts only and never compile a page or resolve a list profile; effective reads
  take their constraints from the declared policy projection and a missing policy is a hard `422` refusal, not
  an empty-policy fallback. The real-ORM test patches `PageAssembler.__init__` and `assemble_page_contract` and
  shows neither is instantiated on either branch
- the preference is applied exactly once: the contract/assembly layer carries no preference token, the single
  server-side application helper is defined only in the preference handler, and the frontend has one
  application site. `ui_contract_v2` still declares `preference_policy` for the consumer and no longer
  reorders the declared contract columns from the stored choice
- snapshot identity rule: the tracked preference snapshot carries an environment-assigned `id`. In the
  registered snapshot database `id=1` today resolves to another principal's `action:809` scope and not to the
  snapshot's own declared scope, and there are `0` rows under a `model:unknown` scope. The `id` is therefore
  never a proof of existence and never a deletion handle; any handling resolves a row by `(user_id, scope_key)`
  through a governed entry, read-only first
- limits: this slice proves the preference path no longer triggers full page assembly, a single application
  site, and the refusal semantics. It does NOT prove an end-to-end latency gain, does not close the
  performance topic, does not relax the mature-system targets, and does not authorise R6. R4's
  first-permission-cost closing evidence was not formally cited at the time of this slice, so R4 was
  open then (superseded on 2026-10-17 by the R4 closing section below)
- evidence: `artifacts/main-scheduled-ci-closeout-20261016/sce-r5-preference-orm.log` (10 tests, 0 failed),
  `sce-r5-list-preference-single-application.log`, `sce-r5-preference-record-probe.log`,
  `sce-r5-contract-snapshot-preference-record-probe.log`, `sce-r5-iteration.log`, `sce-r5-ledger-unit.log`;
  the run index records them under `backend_runtime_investigation.preference_r5_closure`

### First-Permission Cost Closed by Measured Level Split (R4, 2026-10-17)

- question: the controller `permission` segment of the first `ui.contract.v2` list request was observed at
  `215.173 ms`, while a registry-cleared rebuild measured `132.648 ms` and per-request cost measured
  `1.5-1.7 ms`. The residual was previously named "process-first module/ORM cold" but explicitly not
  re-measured. This closure measures it instead of inferring it
- instrumentation: the earlier `first_touch_of_process` reading (`2.373 ms`) was never the process-first cost,
  because probe setup derived the menu carrier through `sc.product.policy.published_route_authority()`, an
  `@tools.ormcache` process cache that had already built the authority. The P4 read-only probe gained one
  governed optional input (`PRODUCT_PERFORMANCE_PERMISSION_CARRIER`, forwarded through the existing
  `PRODUCT_*` allowlist in `scripts/ops/odoo_shell_exec.sh`) so the genuinely first gate can run before any
  other ORM warm-up. No product code, schema, fixture or ACL change; no sudo, no cache widening, no skipped
  check
- measured levels (same principal, state-less request shape with `menu_id`): warm per-request median
  `1.81-1.96 ms` (ACL 2 / SQL 3) and `0.242-0.262 ms` without `menu_id`; registry-cleared cold rebuild
  `125.286 ms` (ACL 133 / SQL 288); **process-first gate `484.830 ms`** (ACL 219 / SQL 371); controller
  observed first segment `215.173 ms`
- decomposition: the process-first gate is `principal_group_signature` `263.464 ms` (the ormcache key / role set
  fingerprint) plus `_build_runtime_route_authority` `218.245 ms`. The process-first premium over the cleared
  reading is `359.544 ms` (`54.3%` of the first gate) and lives entirely in the first process-wide population
  of model/field/group state that `registry.clear_cache()` does not restore - the same
  `principal_group_signature` call costs `1.03 ms` after the clear and `1.09 ms` warm
- attribution: the observed `215.173 ms` sits inside the measured envelope `[125.286, 484.830]` and matches the
  process-first authority body within `3.072 ms` (`98.57%`), consistent with the serving worker having already
  paid part of the ORM cold in the same request's auth/context stage. Repeat proof: exactly one
  `build_runtime_route_authority` per gate and zero `_build_runtime_route_authority` calls warm, so there is no
  redundant duplicate build to remove
- rule kept: measuring the process-first premium never authorises special-casing a model, skipping the check,
  elevating with sudo, or widening/TTL-extending a cache. The separation is measurement only and R4 needs no
  product change
- still open and not folded in: the pre-existing P0 `ir.actions.act_window.groups_id` gap when `action_type` is
  omitted (registered P0 item, needs its own authorization and counterexample set), company-scope-switch
  coverage (`second_company_id=null`), the controller ingress/session/transport residual, plus R3 cache
  duplication, the gen-2 GC pause, and the undeclared SET-response `id`. (2026-10-17 supersede: `ctime` is no
  longer the code identity; it is a file-change signal only. The code identity is a sha256 content digest over the
  managed `.py`/`.xml` sources, and a formal deployment must still bind an immutable build or content digest.)
- evidence: `artifacts/main-scheduled-ci-closeout-20261016/sce-r4-permission-probe-9.log` (process-first, carrier
  supplied), `sce-r4-permission-probe-8.log` (derived carrier), `sce-r4-permission-probe-unit.log` (9 tests PASS);
  run index `backend_runtime_investigation.permission_gate_attribution.closure`. Still dirty: no freeze, no
  `ci.local.quick`, no push, no merge, no deployment, no history rewrite

### Profiled Samples Are Never Graded Against an Absolute Target (2026-10-17)

- problem: the only hard breach in the previous record (`profile_first_contract_assembly`, `failed`
  at `3814.60 ms`) was judged from a **cProfile-instrumented** sample (`profiled:true`), while the
  same record already held an unprofiled `process_first` sample of `1567.163 ms`. Grading an
  instrumented number against an absolute millisecond budget is a calibration error, not a system
  finding, so the rule was fixed instead of the threshold
- rule (in the single normalizer, schema `mature-system-performance-targets/v1`): profiled samples are
  never graded - they are reported, and their values stay in the row as `profiled_values_ms` and
  `profiled_basis_ms`. Only unprofiled samples produce a verdict. A target may declare
  `measurement_basis` (`unprofiled` | `profiled`) and `diagnostic_only`; a profiled-basis or
  diagnostic-only target never yields a pass or a failure, only `not_evaluated` plus a reason
- anti-abuse guard: `diagnostic_only` must declare `measurement_basis: profiled` and the declaration
  check fails closed otherwise, so the flag can never hide an **unprofiled** measurement that could
  have been graded. A target without a comparable basis is reported through
  `ungradeable_by_declaration`, and `complete_over_comparable_targets` is true only when every target
  with a comparable declared basis has a verdict - the ungradeable target is never counted as a pass
- comparable counterpart: `first_contract_assembly` (`selector.sample_labels: ["process_first"]`, same
  `keeps_flow` tier 1000/3000) answers the same first-call question on the unprofiled capture, so the
  first-call boundary keeps a gradeable owner instead of losing coverage
- verdict change on the identical payloads: `profile_first_contract_assembly` `failed 3814.60` ->
  `not_evaluated`; `first_contract_assembly` (new) `within_tolerance 1567.16`; overall `failed` ->
  `within_tolerance` (met 3 / within 3 / failed 0 / not_evaluated 1). Unchanged: `samples 142/142`,
  `entries 5`, `gaps 0`, `stage_sum_forbidden`, `capacity=target_unresolved`
- honesty boundary: `1567.16 ms` is still above the 1000 ms `keeps_flow` target, so the first call
  remains **not met**; this rule produces no speed-up, relaxes no ladder budget, and is not a
  capacity, deployment or delivery claim
- regeneration method: the captured payloads were **not** re-captured. The single normalizer was
  re-run over the same hash-bound payloads, so the verdict change is attributable to the rule alone.
  Command, input digests and before/after verdicts:
  `artifacts/backend/system-performance-baseline/comparability-rule-replay.json` (`494ff82b...`),
  record `artifacts/backend/system_performance_baseline.json` (`f894ccee...`), report
  `docs/ops/audit/system_performance_baseline.md` (`20f2ccfc...`). Two replays agree byte for byte
  except `generated_at`. A full re-capture over all sources is still required before any delivery
  freeze
- evidence: `make verify.system.performance.baseline.unit` 61 tests PASS (was 54), including the
  profiled-only counterexample, the "unprofiled first call is graded, not hidden" case, the
  `diagnostic_only`-may-not-hide-unprofiled counterexample, and the completeness accounting; run
  index `backend_runtime_investigation.benchmark_comparability_rule`. Still dirty: no freeze, no
  `ci.local.quick`, no push, no merge, no deployment, no history rewrite

### Full source-set re-capture executed (2026-10-17)

The "a full re-capture over all sources is still required before any delivery freeze" item above is
now satisfied as a *capture*: one bounded run over the declared 7-source set
(`sla,observe,contract_profile,contract_request,permission,cache_identity,role_matrix`) on the
registered `sc-local-dev`/`sc_dev_demo` profile produced `status=baseline`, `entries=7`,
`samples 142/142`, `gaps=0`, `controlled_regression=passed`, with entry identity `match` on the five
payloads that declare product-code hashes and `unknown` (never zero) on the two that declare none.
Evidence log `artifacts/main-scheduled-ci-closeout-20261016/sce-r7-baseline-refresh.log`
(`9fab4166d69fced00bbcf7df2cdf6703f9383d4ffac717e1050388881fe0523c`), record
`artifacts/backend/system_performance_baseline.json` (`de155d884c98e800829e04b8d52809280b7b9454e58dc66c874d6a7930f641b9`),
report `docs/ops/audit/system_performance_baseline.md`
(`85baf13a639354d0cacc9ab937875456a24fce5b284b8c3a20ee0e563a61671c`). Still dirty: no freeze, no
`ci.local.quick`, no push, no merge, no deployment, no history rewrite.

- coverage rule (counterexample, replayable without any capture): regenerating the report from a
  narrower source set is a **coverage regression**, not a variant. Feed the normalizer only
  `contract_profile,contract_request,permission,cache_identity` and it reports
  `status=incomplete / entries=4 / samples=37 / gaps=1`, with `controlled_regression` blocked on
  `visible_scale` (the field is `observe`'s visible-record count). Replay artifacts:
  `artifacts/main-scheduled-ci-closeout-20261016/sce-r7-baseline-narrow-sources.log`
  (`b9ad9dafc59141fd4fe4c18400fb2f146b8a91706f6686eed8307561a07ff3d2`) and the same-named `.json`
  (`e20c325d22967b3a502f7ec61e3e2ea1823e3aece235bbd75c8dfdcdd0e12664`); both replays leave the
  tracked report digest unchanged, so the counterexample never touched the delivery report. A
  baseline re-render must therefore be gated on "entry set does not shrink", not on `status` alone.
- role dimension is part of the same baseline, not a side note: 9 declared principals,
  `contract_surface_varies_by_role=true`, `surface_digest_stable_within_dispatched_role=true`,
  `all_refusals_are_explicit=true`, `refused_roles_never_report_a_contract=true`. `list_action_open`
  dispatches 6 roles (3 refused, 0 unavailable) and `form_action_open` dispatches 4 (0 refused,
  5 unavailable, each keeping its `AccessError` reason). Recorded without smoothing:
  `relation_surface_varies_by_role` is `true` for the form case and **`false`** for the list case.
- honesty boundary: `warm_contract_dispatch` p95 `172.88 ms` is still above its `100 ms` target
  (within the `200 ms` tolerance) and is not claimed improved; `first_contract_assembly` `1711.16 ms`
  is still above the `1000 ms` `keeps_flow` target. The hot p95 tail is reproduced as a CPython
  generation-2 GC pause and disappears under the paired gc-disabled control. This rule produces no
  speed-up and is not a capacity, deployment or delivery claim.

### Source-Envelope Identity Excludes Per-Request Measurements (R7, 2026-10-17)

- rule: a value hashed into `sourceSha256` must be a property of the **source**. Transport identity
  (`trace_id`, `request_id`) and per-request measurements (`elapsed_ms`) are properties of the
  **request**; they are registered in `core/contract_lifecycle.py::SOURCE_META_PER_REQUEST_KEYS` and
  dropped by `source_meta_for_identity()` where the envelope meta enters the source payload and the
  cached projection entry. The delivered contract is untouched because the assembler only *reads*
  `source_meta`.
- counterexample (before): same identity, same request, two processes - `contractSha256` constant
  `b90852db1fce92b49585e338450a3f181fee881359f43bede7c0054572a5f367`, `sourceSha256` per process
  (`ff70e121...`, `74081823...`). A truncation-free path->digest index over 37223 nodes differed at
  exactly three paths: `$`, `source_meta`, `source_meta.elapsed_ms`. The earlier bounded path map
  (depth 4 / 1400 nodes / first 24 list items) and the all-scalar unsorted-list scan both missed it.
- counterexample (after): six processes, `sourceSha256` constant
  `42d7bb3fa002084ae280660175c7f5418eb86aca2ea4f5a23d0ff27368ff2d20`, `contractSha256` unchanged,
  37222 nodes with zero pairwise path differences, delivered-object re-verification `ok == checked`.
- negative control: the filter is narrow, not a blanket drop. `SourceMetaIdentityTests` proves the
  identity does not move when only `elapsed_ms` changes and **does** move when a source fact
  (`model`, `op`) changes; the caller's meta is never mutated. Entry:
  `make verify.backend.contract_lifecycle.authority`.
- sealed semantic digests: `sourceSha256`/`contractSha256` are pure functions of one stored graph, so
  they are memoized per assembled cache entry and now cost 1 recomputation per hot request instead of
  3 (measured before/after in the same probe: `payload_sha256` 3.0 -> 1.0 calls and 12.413 -> 1.145 ms
  per request, `strip_request_transport_identity` 3.0 -> 1.0 calls and 32.596 -> 1.396 ms). The memo
  is a hint, never an authority: `verify_unified_page_contract_integrity` still recomputes both
  digests from the delivered object on every request, and the probe confirmed memo == recomputation
  on every seal call. Request-level identity stays unique per request.
- determinism rule: a member **set** must not carry an iteration order into identity-bearing output.
  `page_assembler.py` now emits `layout_fields` as `sorted(...)`; before the fix two processes had the
  same 68 members with different `order_digest` (`ed5e4da22e9faf86` vs `5984aa691c48c1c0`), after it
  the digest is stable (`60b33572e04dfafd`). Order-significant lists are not sorted this way.
- measurement boundary: these are identity and determinism closures with a same-probe before/after
  latency comparison, **not** a steady-state baseline and not an overall target pass. The mature
  system target stays `failed` on `profile_first_contract_assembly`; warm dispatch p95 stays above its
  100 ms immediate target. Evidence:
  `artifacts/main-scheduled-ci-closeout-20261016/sce-r7-source-identity-evidence.json`.

### Cache Layers and Assembly-Time Redundant Hashing (R12, 2026-10-17)

- rule: the runtime contract has exactly one authority - per-request dynamic computation. Caches may
  only carry record-independent facts. The binding table and invariants live in
  `docs/architecture/contract_runtime_cache_layers_v1.md`; the machine check lives in
  `scripts/verify/unified_page_contract_v2_assembler_guard.py::check_cache_layer_boundaries`.
  I9 pins the hit-path ordering (seal then return, no entitlement/policy/action/modifier/trim); I10
  pins the principal group digest in `build_projection_cache_key` and the ACL/rule/user/policy
  definition authorities in `build_projection_source_token`. The runtime unreachability claim is
  additionally covered by 48 cache unit tests and the governed identity probe.
- record boundary: a request carrying `record_id` may read the source projection but must never read
  or write the assembled-contract cache. The guard pins the read gate
  (`not runtime_record_id and (not is_create_request)`), the write gate
  (`not runtime_record_id and (not is_create_request) and cache_key and source_token`), the presence
  of `apply_runtime_record_overlay(` in the assembly path, and the absence of `_assembled_v2` /
  `contract_v2` in the persistent runtime asset repository.
- frontend boundary: `createContractCache` may only serve a record-free, preview-free create
  contract, and its key must bind `sessionDb`, `token` and `contextEpoch`. The guard fails closed if
  any of those markers disappears.
- counterexample (before): `_base_contract` called `_fingerprint(source_payload)` to fill
  `meta.etag`/`snapshotId`/`traceId`/`requestId`, then `assemble_unified_page_contract_v2` sealed the
  contract and overwrote all four from the lifecycle digests. Every assembly therefore hashed the
  whole source graph twice (placeholder + seal). Replacing the placeholder with a stable page
  identity cut `v2_source_assembly` from `130.5 ms` to `111.0 ms` median on the uninstrumented
  record-form probe.
- copy-ownership rule: `trim_unified_page_contract_v2` owns the only top-level `deepcopy`;
  `_trim_container`/`_trim_widget` must not copy again. `strip_request_transport_identity` is
  copy-on-write and may return the caller's object, so any mutating caller must copy first
  (`contract_semantic_payload` does). The guard pins the first two rules structurally.
- equivalence evidence: the earlier field-name filter was too broad - it removed the real business
  field `data.business.timing.deadline` at any depth, so a 1 -> 2 change still compared equal. That
  `4bfa3c1a6d2254fe...` claim is withdrawn; the R13 logs remain timing evidence only. The corrected
  filter exempts exactly 10 registered paths (top-level `meta.elapsed_ms`/`meta.projection_cache`,
  four request/trace identity keys under `data.meta`, and `trace_id`/`request_id` in the two contract
  `context` containers). Corrected same-probe window: full-tree SHA-256
  `ff6db9d1bdd3beb91a2f5f183c87321573677506d19d2141d994dffd010bbefb` on both sides,
  `contractSha256` `1673cb0b2f037845...` on both sides, all section digests equal, and only
  `meta.elapsed_ms` plus `meta.projection_cache.stages_ms.*` differ. The `data.business.timing.deadline`
  counterexample is a non-zero unit test. Latency: hot median `688.528 -> 501.288 ms` (`-27.2%`),
  window maximum `711.902 -> 551.859 ms` (`-22.5%`, observation only). Recomputing the original R12
  samples with the correct even-sample median gives `697.437 -> 483.499 ms` (`-30.7%`). Evidence:
  `artifacts/main-scheduled-ci-closeout-20261016/sce-r14-record-form-{baseline,after}-precise-semantic.log`
  and `scripts/verify/test_local_dev_runtime_record_form_probe.py`.
- cache-identity counterexamples: removing finance-manager group 128 moves both `cache_key` and
  `source_token`; changing draft `ui.business.config.contract` id 27 `priority` moves `source_token`;
  both savepoints roll back to byte-identical identities and commit is refused. Non-zero unit tests
  also cover role/ACL/rule/user/policy-definition changes and prove the old assembled entry is
  unreachable. Seal refreshes identity, not authorization. Evidence:
  `artifacts/main-scheduled-ci-closeout-20261016/sce-r14-projection-cache-identity.log`.
- boundary: not a freeze, Quick, push, merge, deployment, batch-acceptance or product-delivery
  claim. First open/startup and the gen-2 p95 tail remain open.
