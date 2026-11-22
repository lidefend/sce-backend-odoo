# Mainline Performance 02: System Initialization Diagnosis

## Identity

- Repository: `lidefend/sce-backend-odoo`
- Base main: `cb182c9e94abe515b0d987fc514bc46ca98d1cfb`
- Main performance run: `44980704390`
- Candidate: PR #960
- Candidate performance source: `5a0405f85def553cca950b7f55b991aec51978bd`, run `44985395085`
- Candidate validation follow-up: `0e4292232a0f35a5e4019f261463095c8de0f370`
- Formal product layer: P4 diagnosis over a P0 startup boundary

The candidate is an optimization comparison point. It is not approved for
merge until the full gate passes and the remaining startup cost has an
evidence-backed owner.

## Boundary

This batch is read-only. It does not change ACL, record rules, product
publication, scene eligibility, route authority, menus, frontend behavior,
runtime caches or performance budgets. It does not write business data.

## Measurement Identity

- Main source: `cb182c9e94abe515b0d987fc514bc46ca98d1cfb`, tree
  `6a9cafd0c8fbd110f25237da57b03c599a435f4d`.
- Candidate source: `5a0405f85def553cca950b7f55b991aec51978bd`, tree
  `61550398f5fb7bd75939a38a545678b3d72f2b66`.
- Candidate follow-up source: `0e4292232a0f35a5e4019f261463095c8de0f370`,
  tree `713926018fc116c11ed900a5d2d6dc941e272553`.
- Remote frontend environment: GitHub Actions `ubuntu-latest`, 4 CPUs,
  15983 MB, Chromium `147.0.7727.15`, database `sc_frontend_acceptance`.
- Remote source files: [main performance](https://github.com/lidefend/sce-backend-odoo/actions/runs/44980704390),
  [candidate performance](https://github.com/lidefend/sce-backend-odoo/actions/runs/44985395085).
- Local governed runtime: `sc-local-dev` / `sc_dev_demo`, PostgreSQL `15.19`,
  system identifier `7674830867180216358`, Odoo `17.0-20260630`, Python
  `3.10.12`, 18 host CPUs, 16512512000 host memory bytes.
- Local runtime files were reloaded by recreating the Odoo container at
  `2026-11-22T05:27:23Z`. `SC_SOURCE_REVISION` remained `unknown`, so source
  identity is bound by the exact file hashes below rather than that environment
  label.

The following local source hashes bind the restarted runtime used for
attribution. The same hashes were read back from
`sc-local-dev-odoo-1:/mnt/source-addons/` after the restart:

| Source | SHA-256 |
| --- | --- |
| `addons/smart_core/handlers/system_init.py` | `0465d324f0144490721d91016f1f41f256a7b5f130bdc892e99129115dd30d23` |
| `addons/smart_core/delivery/effective_delivery_service.py` | `43093abd8f8804ebe73a151477a703b6ad44fd596df9021474398f98f69bf41b` |
| `addons/smart_core/delivery/delivery_engine.py` | `7a88d49e01db26a85e2ab7279b4b7da34f91f6bfc380da8e300af4d87840c91b` |
| `addons/smart_core/delivery/menu_service.py` | `5968a53e54a21af821bb573e6efa17033f3e55511a2fc6a2df46b93f63831418` |
| `addons/smart_core/delivery/effective_delivery_inputs.py` | `c311990a0deaf8fa29ab7a07861bbb65acebf66f7ab4dc21b12ab6b536e9e290` |
| `addons/smart_core/delivery/product_policy_service.py` | `407a20eee9a369eae79a91890a98b9f10ed8d6f5511fe31a543ef40e2956bde4` |
| `addons/smart_construction_core/services/scenario_surface_projection.py` | `dc4ad4f5dfafe806e3e2f2a127db9a43c14eb532fe727afc553dfba56fe66885` |
| `addons/smart_construction_scene/scene_registry.py` | `d86c968d7d8183f6ee9ee33c7bd2e8758b7aaf0ea9b7a6dd80aa61ca9dcf5ad2` |
| `addons/smart_construction_scene/core_extension.py` | `019316ac3423349a9688f0be410299a64aee3bc273ebe4d20aa22fbc8ecbcd88` |

## Profile

### End-to-end scenario result

| Scenario | Main median / p95 | Candidate median / p95 | Main budget median / p95 |
| --- | ---: | ---: | ---: |
| `login_to_interactive` | 3411 / 3761 ms | 3152 / 3260 ms | 3000 / 5000 ms |
| `my_work` | 1618 / 1861 ms | 1116 / 1250 ms | 1200 / 2500 ms |
| `payment_detail` | 455 / 458 ms | 406 / 422 ms | 1200 / 2500 ms |
| `settlement_detail` | 327 / 420 ms | 291 / 376 ms | 1200 / 2500 ms |
| `execution_detail` | 304 / 327 ms | 290 / 301 ms | 1200 / 2500 ms |
| `form_open` | 1604 / 1775 ms | 1491 / 1647 ms | 1600 / 2500 ms |
| `company_switch` | 2210 / 2570 ms | 1888 / 2493 ms | 2000 / 4000 ms |

PR #960 moved six scenarios into budget. Only `login_to_interactive` remains
over budget, by 152ms at the median. Four of its five samples were over
3000ms, so this is not a single outlier and does not provide a stable margin.

### Browser phase decomposition

Median values from the five `login_to_interactive` samples:

| Interval | Main | Candidate `5a0405f8` |
| --- | ---: | ---: |
| Browser work before the first measured request | 530 ms | 516 ms |
| Login request | 584 ms | 571 ms |
| `system.init` HTTP request | 1943 ms | 1596 ms |
| UI work after the final response | 368 ms | 332 ms |
| Total | 3411 ms | 3152 ms |

The intervals come from independent request timing records; they are
descriptive rather than an additive stopwatch and can overlap at request
boundaries. The candidate's `system.init` profile takes 1521ms at the median
while its HTTP request takes 1596ms, leaving about 65-75ms per sample for
transport, response decoding and scheduling.

The remote browser artifact does not export `startupTiming.ts` marks for the
login scenario. A separate read-only local browser probe used the existing
marks and the governed dev namespace login. Its served frontend build was
`fe635515dda270ed230d07a77ed4bcc9ab4fe5ac`; `git diff --quiet` proves the
`frontend/apps/web` tree is identical from that build through the current
candidate, so the served frontend bytes are relevant to the stage structure.

Five warm local login samples produced:

| Local browser interval / marker | Median |
| --- | ---: |
| Navigation response start | 2.3 ms |
| DOM interactive | 42.0 ms |
| `DOMContentLoaded` | 95.1 ms |
| load event | 98.7 ms |
| `boot_start` mark | 34.3 ms |
| First measured login request start | 233 ms |
| Login request | 342 ms |
| `system.init` HTTP request | 1072 ms |
| `session_ready` mark | 1616.6 ms |
| UI work after final response | 878 ms |
| Total login-to-interactive | 2488 ms |
| Warm script resource duration | 94.4 ms |
| Warm stylesheet resource duration | 43.6 ms |
| Resource transfer / decoded bytes | 2819359 / 2811259 |

The local result is faster than the remote gate, so its absolute values are not
compared to the remote budget. It does show stage ownership: static resource
timing on the warm local browser was small, `session_ready` arrived shortly
after the response, and the remaining post-session navigation, mount and ready
interval dominated the local browser side. The remote 332ms
`ui_after_last_response` remains materially different and must be measured on
the release browser before selecting a frontend change.

Only `boot_start` and `session_ready` startup marks were present on the role
home journey. `contract_loaded` and `record_ready` belong to record-form
lifecycle journeys and were not fabricated for the home surface.

### `system.init` stage profile

Median server profile values:

| Stage | Main | Candidate |
| --- | ---: | ---: |
| `build_nav` | 1386 ms | 1066 ms |
| `finalize_startup_surface` | 235 ms | 221 ms |
| `execute_scene_runtime` | 84 ms | 76 ms |
| `prepare_runtime_context` | 60 ms | 57 ms |
| `collect_intents` | 46 ms | 49 ms |
| `apply_surface` | 24 ms | 22 ms |
| Other named stages | about 18 ms | about 18 ms |

The duplicate `NavDispatcher` navigation build is confirmed and PR #960 removes
it for eligible boot requests. The remaining navigation cost is effective
delivery, not the compatibility navigation path.

### Effective Delivery attribution

The restarted local process-first profile is a diagnostic attribution sample,
not a budget measurement. Instrumentation adds overhead, so its absolute values
are not compared to the remote gate.

| Effective Delivery owner | Nested cumulative time |
| --- | ---: |
| `EffectiveDeliveryService.resolve` | 984 ms |
| `DeliveryEngine.build` | 486 ms |
| Navigation authority extension hook | 196 ms |
| `_internal_actions` | 143 ms |
| Platform release gate | 123 ms |
| Remaining filters, landing and authority finalization | approximately 36 ms |

`DeliveryEngine.build` contains distinct work that cannot be deleted merely
because it has the same parent:

- product policy load and normalization: 133ms;
- delivery navigation build: 129ms;
- two route-authority builds for product delivery and native execution:
  124ms total.

The two route-authority outputs remain semantically distinct. This diagnosis
does not recommend collapsing them.

### Repeated scene declaration loading

One startup request loaded the effective scene declarations five times:

| Consumer | Time | Calls |
| --- | ---: | ---: |
| `EffectiveDeliveryService._internal_actions` | part of 168 ms hook total | 1 |
| `scenario_surface_projection._scene_targets_by_pair` | part of 168 ms hook total | 1 |
| `smart_core_navigation_authority_filter` | 36 ms | 1 |
| `OdooNavAdapter` scene-map derivation | 43 ms | 1 |
| `load_scene_configs_with_timings` tile projection path | 36 ms | 1 |
| Total `load_scene_declarations_with_timings` | 284 ms | 5 |

The effective declarations contain 96 scenes and about 77992 JSON bytes before
the consumer-specific projections. There is no request-scoped reuse in
`scene_registry.py`; every call repeats database/imported/asset merging and
normalization.

### Menu identity and SQL

SQL tracing observed 1080 warm-request statements and 2208 first-request
statements. Instrumentation measures 189ms in the warm trace for the statements
it attributes.

The same 132-menu scenario index is built twice in one request:

- `runtime_menu_scope`;
- `_scenario_entries_by_menu`.

Each build resolves each XMLID twice, producing 528 `env.ref` calls:

| Origin | Statements |
| --- | ---: |
| `_scenario_entries_by_menu` first pass | 132 |
| `_scenario_entries_by_menu` second pass | 132 |
| `runtime_menu_scope` first pass | 132 |
| `runtime_menu_scope` second pass | 132 |

The two `_resolved_menu_index` calls consume 170ms cumulatively; the 528
XMLID resolutions consume about 140ms cumulatively. These times overlap and
must not be added to the stage totals.

Other material SQL origins include:

- 72 scene-pair target resolutions;
- 69 `scene_provider._ref_id` resolutions;
- 56 delivery navigation XMLID/action resolutions;
- 84 runtime policy-target authorization checks;
- 44 tenant scene enablement reads.

### Release snapshot duplication

The active `construction.standard` release snapshot is:

- 734059 JSON bytes total;
- 504480 policy bytes;
- 11 menu groups;
- 132 menus;
- 132 capabilities;
- snapshot id `1`, SHA-256
  `412d744ff47b70ea4bd1277cc73f2a54efccd4787e661197548abc87be6b076f`.

In one request, `ProductPolicyService.get_policy` reads and normalizes the
active released snapshot, then `_load_platform_release_gate` independently
searches and projects the same active released snapshot. Their profiled owner
times are 131ms and 123ms. The projections answer different questions, but
they currently duplicate snapshot read/deserialization and large nested copies.

### Deep-copy attribution

Profiled `copy.deepcopy` consumed 446ms cumulatively. The material direct
callers were:

| Caller | Cumulative |
| --- | ---: |
| Odoo field conversion while copying scene declarations | 221 ms |
| Product-center policy normalization | 82 ms |
| Scenario menu index copies | 22 ms |
| Edition diagnostics copy | 20 ms |
| Scene orchestration definition copies | 19 ms |
| Navigation contract compiler | 16 ms |
| Effective route-authority coalescing | 16 ms |
| Safe-landing merge | 14 ms |
| Business-scene authority filter | 14 ms |

Instrumented field-conversion copies were dominated by scene dictionaries with
keys such as `layout`, `action_specs`, `data_sources`, `target`,
`role_variants`, `tiles` and `zone_blocks`. This confirms that repeated scene
materialization is not only an SQL issue; it also repeats large Python object
graphs.

### Startup finalization

The restarted local profile attributes 153ms of the 160ms
`finalize_startup_surface` sample to
`smart_core_scenario_surface_projection`. Inside its 170ms contract compiler
path, the scenario projection hook owns about 153ms and the compiler's
remaining own work is about 17ms.

The remote candidate has a 221ms median for finalization and one 549ms sample.
This stage is secondary to effective delivery, but it still contains a repeated
scene declaration hook and must be included in the request-scoped fact plan.

## Confirmed Facts

- The former boot-mode startup built a second navigation tree through
  `NavDispatcher.build_nav()` and immediately discarded it when effective
  navigation replaced the payload.
- PR #960 removed that duplicate materialization for eligible boot requests.
- The remaining startup cost is concentrated in `EffectiveDeliveryService`,
  with additional cost in `system.init` finalization and browser-side startup.
- One request performs five effective scene declaration loads and repeats the
  132-menu scenario index twice.
- The same release snapshot is independently read and projected by product
  policy and the effective-delivery release gate.
- Remaining deep-copy cost is dominated by repeated scene declaration object
  graphs, not one unexplained framework cost.
- The two route-authority computations remain separate product and native
  authority questions; there is no evidence for deleting either one.

## Hypotheses To Measure

- Whether scene consumers can share one immutable request-scoped declaration
  fact and copy only at their own mutation boundary;
- whether `runtime_menu_scope` and `_scenario_entries_by_menu` can share one
  resolved menu index without changing fail-closed foreign-database behavior;
- whether product policy and the release gate can share one request-scoped
  active snapshot projection while retaining their distinct outputs;
- whether route-authority construction can reuse native facts without merging
  product publication and native execution authority;
- which part of the 516ms pre-login browser interval is document load, bundle
  execution, Vue mount and login-form readiness;
- which part of the 332ms post-response interval is session commit, navigation
  store application, router transition and first render. The local probe
  confirms the post-session interval is large enough to justify this split.

## Proposed Implementation Queue

No item below is implemented in this read-only diagnosis.

| Priority | Owning layer | Candidate | Why the profile supports it | Required proof before acceptance |
| --- | --- | --- | --- | --- |
| P0 | P1 scene registry seam | One request-scoped immutable scene declaration fact with copy-on-write at mutating consumers | Five loads consume 284ms and repeat large scene dictionaries | Same effective scene list, identical navigation/authority SHA, at most one base load, focused scene tests |
| P0 | P1 scenario menu scope | Build the 132-menu resolved index once and pass it to both consumers | Two indexes consume 170ms and duplicate 528 XMLID lookups | Same menu scope and denial reasons; SQL count reduced; fail-closed foreign DB tests |
| P0 | P0 release snapshot | Share one active released snapshot fact between policy and release gate | 734059-byte snapshot is independently read/projected twice | Same policy digest, page gate and denial semantics; one snapshot conversion per request |
| P1 | P0/P1 copy boundaries | Replace blanket deep copies with immutable/read-only projections or copy-on-write | Deepcopy is 446ms and scene declarations dominate field conversion | Consumer mutation tests, identical response hashes, no shared-cache leakage |
| P1 | P0 route authority | Reuse already loaded menu/action facts between the two authority builds without merging their semantics | Both builds cost 124ms total and already share some menu fact snapshots | Product/native authority parity and route validation rejection tests |
| P1 | Frontend instrumentation | Export `startupTiming.ts` marks in the authoritative login performance sample | 516ms and 332ms intervals remain opaque | Non-zero samples with ordered marks before considering frontend optimization |

These candidates overlap. Their individual upper bounds must not be summed as
an expected total. The first implementation batch should change one ownership
seam and remeasure before the next.

## Evidence

| Evidence | SHA-256 / result |
| --- | --- |
| Main `performance.json` | `dc1de004488a37bb668f1f2646efe3324dcffe80a1e80ca3ab5082995fc76147` |
| Candidate `performance.json` | `4f3b785cbb00271309a6c04e85de1c9f6b72795b1a2aeac960c582243502d5ba` |
| Restarted exact-tree profile | `16ea174b5b6f03d39388f4cae6508a5928b0fc8fcf22be7536b8ddce34d04baf` |
| Restarted shape trace | `b27874257d22c2d5e8b56e8e65a77bd3a2b27f92016747e97420de123af54aee` |
| Restarted SQL trace | `2b99862c75a4d132d84b8f78e9b0ae786a8f29f51a41a5760ef7cad71bc6dbbc` |
| Restarted release profile | `33d9d68f9969feb51c649483ed41a08394d223c423627eea3e0b563289462df9` |
| Restarted deep-copy keys | `a15da76d29679cbef86eedeed837b5e65dc91f33f38c4ff53c55afc878b88c6b` |
| Restarted local login startup marks | `0394635efcfcf40afb154adf24287a80460aaedeb426f90a3e85c526a58a001f` |
| Runtime unit | PASS, 34 tests |
| Performance baseline unit | PASS, 72 tests |

Original logs live under `.runtime/ci-recovery/` and are intentionally not
committed. They contain only source identities, counters, timings and sanitized
object keys.

## Decision

PR #960 is an optimization comparison candidate, not performance acceptance.
It must not be merged from this diagnosis. The next work should be authorized
as a bounded implementation batch after the request-scoped fact ownership above
is reviewed.

## Next Step

Request authorization for one P0 implementation seam. Do not start a broad
cache or menu rewrite, and do not weaken ACL, publication, scene or route
authority checks.
