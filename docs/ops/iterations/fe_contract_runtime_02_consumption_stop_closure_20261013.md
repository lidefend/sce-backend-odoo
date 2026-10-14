# Frontend contract consumption stop-closure: T1–T9 (P0 runtime + P4 verification)

Run: `.agent/runs/FE-CONTRACT-RUNTIME-02/run.json`
Branch: `fix/fe-contract-runtime-02-consumption-stop-closure`
Baseline: `e4b8fd957e364a4d1749127d563398c8de80256d` (`main` == `origin/main`)
Date: 2026-10-13

## Purpose

Owner-directed read-only audit (bound `669902012f9d`, a child of `0f13a238`) concluded
that the official-component and page-composition main return is **done**, but
"rendering and interaction full closure" is **not** complete. Nine confirmed gaps remain;
this goal closes the six consumption gaps (T1–T6) with declaration-first stop semantics,
registers them in the contract-basis ledger/guard (T7), corrects the evidence reuse
identity (T8), and re-binds evidence through the single `evidence_scope` authority (T9).

The governing rule is unchanged and is the point of this batch: the frontend may only
render and interact; every missing or invalid declaration must **stop** the surface
through `ContractGapError` instead of being defaulted, guessed or silently dropped.

## Confirmed gaps (audit-verified at the audit binding)

| ID | Gap | Owner layer | Target |
|---|---|---|---|
| T1 | Create form hides fields whose name/label ends with 状态, overriding contract visibility (`pages/contractForm/nativeLayoutUtils.ts` `isCreateWorkflowStateField`) | P0 consumer | remove name/label inference; consume an explicit create-visibility declaration |
| T2 | Missing layout `span` decoded as `24` (`app/contracts/v2/schema.ts`); invalid span rendered full-width (`components/template/layoutSpan.ts`) | P0 declaration + consumer | declare which nodes must carry a span, fill producers, then remove the consumer fallback |
| T3 | Numeric stop primitive coerces `true`→`1` and truncates `1.9`→`1` (`app/contract/contractGap.ts` `requireDeclaredNumber`/`requireDeclaredNumberList`) | P0 mechanism | strict type/integer/range validation; never mutate the declared value |
| T4 | Collection capabilities default a missing `actions` to `[]`; items missing `action/scope` are dropped (`app/runtime/actionViewCollectionCapabilityRuntime.ts`) | P0 action consumer | distinguish a legal empty set from an illegal declaration; the latter stops |
| T5 | Record entry downgrades an illegal intent and a missing write authority to read-only; `auth=none/read/admin` merged (`app/runtime/recordEntryContract.ts`) | P0 contract semantics + consumer | explicit permission enum; separate "explicitly forbidden" from "declaration missing" |
| T6 | Master-detail relation pagination fixed at `20` by the frontend (`components/template/X2RelationRenderer.vue`) | P0 relation contract + consumer | consume the relation pagination declaration; remove the second parameter source |
| T7 | Contract-basis guard scans three pagination/limit regexes only; strings/tests do not prove visibility/action/permission correctness (`scripts/verify/frontend_contract_basis_guard.py`) | P4 tooling | register T1–T6 in the ledger, add consumption counter-examples, state the guard's coverage boundary |
| T8 | Evidence reuse identity lacks actual company/permission context readback and folds the whole bundle into every entry key (`scripts/verify/business_entry_matrix_model.mjs`) | P4 evidence | add the authoritative context readback; invalidate per unit's real dependency |
| T9 | Some template-ledger paths are shadowed by other reports; the latest 89-entry result is not aligned with the default reuse ledger; `.runtime/final-acceptance/list-surface-structure.json` is 12 create/edit checks with the list gated at 0, i.e. a mis-bound artifact | P4 acceptance | recover the original evidence, correct the index, reuse the approval binding, then patch only affected keys |

## Execution order (owner-set, not reordered)

1. **Fix mechanisms first (T1–T6)** in declaration → decode → consume order; each item runs
   only its owning layer's non-zero targeted test. T3 goes first because T2/T4/T5/T6 consume it.
2. **Add the regression lock with the fix (T7)**; T8 may run from an independent tool executor
   under one-worktree-one-writer.
3. **Bind evidence last (T9)**: derive the affected keys from the original ledger, approve the
   contract first, then verify the frontend executes the same contract. One consolidated
   closure review; unchanged evidence is reused, never a matrix per commit.

## Boundary

- Formal Product Layer: **P0** contract-runtime mechanism, with **P4** verification tooling as support.
- No business page layout rewrite; no new component unless a semantic has no renderer; no new
  environment/credential/fixture authority; no contract capability reduction; no guard relaxation;
  no state-machine DSL in this goal.
- Completion boundaries are reported separately: this goal proves batch/product-review evidence
  for the consumption gaps and guard/evidence bindings — not deployment, not target-user delivery.

## T8 — evidence reuse identity bound to the acting company/permission context

The matrix reuse identity previously had no authoritative company/role readback and folded the
whole bundle into every entry key, so an identity could be reused across a different acting
company (false reuse) while an unrelated change forced a full re-run (false invalidation).

Now the identity is derived from the captured authority, not from the request shape:

- `business_entry_matrix_model.mjs` reads the acting company and login from the closure snapshot
  (`acting_company_id` / acting login), fails closed when they are missing or mismatched, and
  binds per-unit permission context (`released_targets`, `capability_closure_sha256`, `company_id`)
  into the unit fingerprint. `environmentIdentity` now requires a positive-integer `actingCompanyId`
  and no longer folds `denied_role_candidates` into the environment identity.
- `business_entry_matrix_scope.mjs` resolves the acting company via `actingContext(closures, {login})`
  and re-verifies it against `summary.session_company_id` on `--emit-results`.
- `business_entry_negative_closures.mjs` requires `ACCEPTANCE_LOGIN`, records `acting`
  (`login`, `company_id`, `error`) in the snapshot, and rejects a missing/ mismatched acting company.
- `make/frontend.mk` forwards the required `ACCEPTANCE_LOGIN`.

Outcome: a company/permission context change invalidates only the affected keys; an unrelated
deployment no longer forces every key to re-run. The single `scripts/ops/evidence_scope.py` remains
the only scope authority.

## T9 — list-surface evidence re-binding (mis-bound artifact corrected, not re-run)

The audit chain reached the real defect first, without re-running the browser matrix.

**Confirmed mis-binding.** `docs/frontend_productization/rendering-detail/page-pattern-reference-detail-ledger-v1.json`
(`collection.header-actions`, `collection.toolbar-surface`) and `page-pattern-reference-contract-gaps-v1.md`
cited `.runtime/final-acceptance/list-surface-structure.json` as `316/316 gated`. That mutable path
had been overwritten by a payment.request create/edit run whose document records `records 12/12`,
`gated 0/0`, `negative_fixtures 0/0` — it gates no list surface at all. The ledger therefore asserted
list-surface coverage no artifact supported.

**Original evidence recovered (not regenerated).** `.runtime/final-acceptance/list-surface-all-7add8be3.json`
and its `-dark` twin (`list-surface-all-7a58470d.json` is the same value) are the real list-surface
observation: schema `frontend_list_surface_structure_browser.v1`, `gated 108/108`, `negative_fixtures 5/5`,
`runtime_errors 0`, `passed true`. The ledger text `316/316` was never self-consistent with any document
(the document states 108), so the reference — not the run — was corrected to `108/108 gated` over the
viewports/states the document actually observes (`1440/390 x normal/batch/empty`).

**Regression lock.** New `scripts/verify/list_surface_evidence_binding_guard.py` mechanics: every
`X/Y gated`/`gates X/Y checks` claim must name at least one artifact that (a) exists, (b) declares the
list-surface schema, (c) gates the list surface (`summary.gated.total > 0`) and (d) records counts equal
to the claim. Any supported-by-nothing / non-list-surface / count-mismatch / path-less claim is DENY.
Unit-tested in `scripts/verify/test_list_surface_evidence_binding_guard.py` (supported passes; gates-nothing,
count mismatch, no-path, non-surface-schema, CLI-failure all rejected). The defect is recorded as
`CD-20261013-LIST-SURFACE-EVIDENCE-MISBINDING` in the contract-basis ledger; the guard runs in the quick
gate, PR/release unit lanes and `ci.delivery.freeze.prepare`.

## Independent review rework (REQUEST_CHANGES, 2026-10-13)

The frozen-candidate independent review returned REQUEST_CHANGES with four S1 blockers, one S2
and one pre-existing gap. All are fixed and lock-tested; the identified checks were invalidated
by their changed inputs and re-recorded (no full re-run).

| Finding | Fix | Lock |
|---|---|---|
| S1-1 status-bar suppression regressed to field-name level | `resolveStatusFieldSuppression` (`pages/contractForm/nativeLayoutUtils.ts`) now takes the node identity (`nodeIdentity` / `statusbarNodeIdentity`); `useRecordFormLayout` passes node identity, never the bare field name, so a same-name field at another occurrence stays visible | consumption cases cover "same field, different occurrence position" |
| S1-2 auth enum not wired to real consumption | `app/contract/contractAuthLevel.ts` adds `resolveOccurrenceAuthVerdict` (admin implies edit; missing/illegal → `ContractGapError` gap; unresolved → blocked); `useRecordFormLayout` consumes it and computes `readonly = gap || unresolved || (verdict && !edit)`, so admin is editable and a missing declaration stops | `contract_consumption_verdicts_test.ts` covers none/read/edit/admin plus missing-declaration |
| S1-3 acting principal's own permission change did not invalidate evidence | `business_entry_negative_closures.mjs` records and snapshots the acting principal's `role_xmlids` and rejects a missing closure; `actingContext` returns `role_closure_sha256`; `environmentIdentity` binds the acting company closure and fails closed without it | `business_entry_matrix_reuse_identity.test.mjs` + `test_business_entry_matrix_incremental.py` permission-change counter-examples |
| S1-4 required lanes depended on a git-ignored machine-local `.runtime` report | tracked archive `docs/frontend_productization/rendering-detail/evidence-archive/manifest.v1.json` + `scripts/ops/evidence_archive_fetch.py` (`--verify` / `--archive-root --apply`); the guard decides on archived identity (a present local copy must match its sha256; absence is still decidable), and `make/frontend.mk` adds `evidence.archive.verify`/`fetch` with `verify` as the guard's prerequisite | `test_list_surface_evidence_binding_guard.py` (machine-independent) |
| S2 unrelated deployment still invalidated everything | deployment source split out of the shared identity into `deploymentProvenance` (`served_revision` + `frontend_build_sha256`); each unit binds `surfaceInputs` (scope `declared_surfaces` / `whole_artifact` / `served_revision_degraded`) | `environmentIdentity` no longer folds bundle/deployment; per-unit invalidation cases in the reuse-identity test |
| pre-existing read-only master-detail filter | `components/template/X2ManyRelationRenderer.vue` returns `props.adapter.visibleOne2manyRows(...)` instead of filtering rows by non-empty display text | `detail_collection_pagination_test.ts` (declared-visible rows with legal empty values persist) |

The three offline counter-examples the review proved (bundle change alters the shared identity;
acting role change not in the identity; guard rejects when local evidence is missing) are now
locked by the rewritten tests. Ledger entry `CD-20261013-EVIDENCE-ARCHIVE-AND-ACTING-CLOSURE`
records the closure; `closedContractDefects` is now 10, `openContractDefects` remains 0.

## Verification index (living; receipts are the only verdict)

`.agent/runs/FE-CONTRACT-RUNTIME-02/run.json` is the result index (declared targets, inputs, receipts).
Current recorded checks:

| check | target | tests |
|---|---|---|
| contract_basis_guard | `verify.frontend.contract_basis.unit` | 15 |
| contract_gap_primitive | `verify.frontend.contract_gap_primitive.unit` | 40 |
| native_form_structure_responsibility | `verify.frontend.native_form_structure_responsibility.unit` | 18 |
| form_canvas_layout | `verify.frontend.form_canvas_layout.unit` | 60 |
| collection_view_semantics | `verify.frontend.collection_view_semantics.unit` | 54 |
| collection_action_capability | `verify.frontend.collection_action_capability.unit` | 59 |
| professional_detail_collection_guard | `verify.frontend.professional_detail_collection.unit` | 136 |
| agent_ledger | `verify.agent.ledger.unit` | 15 |
| business_entry_evidence_scope | `verify.frontend.business_entry.evidence_scope.unit` | 123 |
| list_surface_evidence_binding | `verify.frontend.list_surface_evidence_binding.unit` | 12 |
| contract_consumption_verdicts | `verify.frontend.contract_consumption_verdicts.unit` | 21 |
| verification_lane_coverage | `verify.verification.lane_coverage` | 66 |
| trusted_scan_scope_unit | `verify.trusted_scan.unit` | 68 |

Auxiliary (not a registered run check): `make verify.frontend.typecheck.strict` rc=0
(`.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/logs/typecheck_strict.log`).

## Freeze-gate lane closure (2026-10-13)

The first exact-head Quick surfaced one remaining blocker: `audit.verification.lane_coverage --check`
DENY, because this batch added verification surface. Both halves were closed by wiring, not by
rewriting the frozen baseline (the ratchet may only shrink):

- `verify.frontend.contract_consumption_verdicts.unit` was defined but referenced nowhere
  (zero-reference `761 > 760`). It is now a prerequisite of `verify.frontend.pr.unit`,
  `verify.frontend.release.unit`, `verify.frontend.quick.gate` and `ci.delivery.freeze.prepare`, so
  the S1-1/S1-2 consumption locks run on the remote frontend lanes and at freeze instead of sitting
  as dead surface.
- `scripts/ops/evidence_archive_fetch.py` and `scripts/verify/list_surface_evidence_binding_guard.py`
  were reachable only from remote lanes (remote-only `85 > 83`). `verify.frontend.list_surface_evidence_binding.unit`
  is now a prerequisite of `verify.contract.architecture.suite` — the single source consumed by both
  `ci.local.quick.run` and `ci.professional.backend.shard-verify` — so the evidence-binding guard (and
  its `evidence.archive.verify` prerequisite) is enforced on the local exact-head lane and the remote
  gate at once. The suite wire carries no pnpm/esbuild token, so `static_suite_frontend_toolchain_guard`
  stays satisfied.

`python3 scripts/audit/verification_lane_coverage.py --check` → PASS at the frozen baseline
(zero-reference 760, remote-only 83, unregistered `0/0`; no baseline or exemption file changed).

Invalidation was limited to the changed inputs: `make/frontend.mk` invalidated
`contract_gap_primitive`, `business_entry_evidence_scope`, `list_surface_evidence_binding` and
`contract_consumption_verdicts`; the `run.json` check registration invalidated `agent_ledger`. All
five were re-run and re-recorded, and one new check (`verification_lane_coverage`, 44 tests) was
added. No unrelated check was re-run.

The consolidated product review / browser journeys for the affected list, form, read-only detail,
master-detail, action and permission surfaces are the final step after the mechanisms above are frozen.

## P4 verification-system governance closure (2026-10-13)

The owner-directed P4 governance task (9 items) landed in this same run and is verified separately
from the product gaps:

- `scripts/audit/verification_lane_coverage.py` now freezes item identities (a count-neutral
  replacement of a registered problem fails), replaces the blanket `review_by=2026-12-31` with
  per-class `review_triggers`, hard-checks owner/basis/expiry/unwired-gate-candidate, and prints the
  structural coverage separately from a functional verdict.
- The three ledgers moved only what the facts required (3 `gate_candidate` reclassifications to
  `release_runbook` / `ops_runbook`); nothing was deleted to make a gate pass. The ratchet counts
  may only shrink.
- `scripts/ci/trusted_scan_scope.py` bounds transient `git` spawn failures (EAGAIN/ENOMEM/EFAULT)
  with a bounded retry instead of failing the Quick gate on a flake.

## Declared-visible detail collection: regression lock (2026-10-13)

The independently reviewed T6/pre-existing read-only filter removal had no behavioural lock; the
source-grep guard only asserted "the amount total is not narrowed to the current page". The
declared-visible rule is now single-sourced and locked:

- `pages/contractForm/one2manyUtils.ts` owns `visibleOne2manyRows(rowsByField, fieldName)`: the only
  exclusion is a declared removal (`!row.removed`). A blank display value is not a visibility fact.
- `pages/contractForm/useOne2manyRuntime.ts` delegates `visibleRows` to that helper, so the runtime
  cannot carry a second visibility rule.
- `frontend/apps/web/scripts/detail_collection_pagination_test.ts` (run by
  `verify.frontend.collection_action_capability.unit`, the ledger binding `[5]` regression guard)
  asserts that every-blank rows stay in the set, that record identity/count/pagination all read the
  same set, and that an undeclared field yields an empty set rather than a fabricated default.
- `scripts/verify/frontend_professional_detail_collection_guard.py` fails if the helper filters by
  display text, if the runtime stops delegating, or if the renderer adds a second visibility rule;
  two negative fixtures prove those branches fire.

## Contract producer → consumer chain re-verified (2026-10-13)

Every declaration the strict consumers now require is produced by the real backend and bound in
`docs/architecture/frontend_contract_basis_ledger.json` (`frontend_contract_basis_guard` asserts the
declaration symbol still exists at the producer and the consumption symbol at the consumer):

| declaration | producer | consumer |
|---|---|---|
| `surfacePolicies.collection_capabilities.actions[]` (action/scope/intent/available) | `addons/smart_core/utils/collection_action_capability.py` `build_collection_capabilities` | `app/runtime/actionViewCollectionCapabilityRuntime.ts` |
| `relation_entry.page_size` | `app_config_engine/services/assemblers/page_assembler.py` `_build_relation_entry_for_field` | `components/template/detailCollectionPagination.ts` |
| containerTree `span` (1..24) | `handlers/ui_contract_v2_projection.py` | `components/template/layoutSpan.ts` |
| `entry_target.record_entry` (`entry_intent`, `model_write_authority`) | `core/navigation_entry_target.py` `_build_record_entry` | `app/runtime/recordEntryContract.ts` |
| permission auth level `none\|read\|edit\|admin` | `core/unified_page_contract_v2_permissions.py` `permission_auth_level` | `app/contract/contractAuthLevel.ts` |

Lane evidence at this candidate: `verify.frontend.contract_basis.enforce` PASS (`open_defects=0`),
`verify.frontend.canonical_form_presenter.unit` PASS, `verify.frontend.page_pattern_reference_parity.unit`
PASS (`owned_gaps=0`), `verify.frontend.product_page_pattern.unit` PASS. `make ci.local.iteration` PASS
(L1 only; `unmappedPathCount=17` by design).

Invalidation was limited to the changed inputs: the new/changed frontend sources invalidated
`contract_basis_guard` (its input is the `frontend/apps/web/src` tree), `run.json` invalidated
`agent_ledger`, and the changed `scripts/verify` sources invalidated `verification_lane_coverage`.
All three were re-run and re-recorded; `collection_action_capability` and the new
`professional_detail_collection_guard` were recorded against their corrected input lists. No
unrelated check was re-run.

Still open (not part of this step): the consolidated affected-surface product review with real
representative roles/companies, and the target-environment upgrade/user acceptance.


## Controller takeover and independent review (2026-10-13)

Stage identity: b5728a5220dabdd98ea1ec9f549df5646c2bcc4d, initially clean; subsequent metadata and explicitly assigned P0/P4 edits are iteration scope, not frozen delivery. agent.run.resume resolved 13 reusable registered checks. Local health passed sc-local-dev/sc_dev_demo and exact filter/volumes; runtime-version readback reported unknown.

Boundary: P0 generic record-entry consumption owns rejection of a present malformed formal carrier; P4 existing local.dev wrappers own the exact-instance approval and observation binding. No model-specific frontend rule, new profile/database/credential or fixture system. Impact: formal record navigation plus existing payment list/form/detail representative consumer. Backend page_size addition is Python-only; reload via governed local.dev.restart, no schema/module upgrade unless a real prerequisite requires it. Build only after affected L1/L2 pass.

Independent review found a remaining T5 defect: missing model/id/intent in a present record_entry returns null and can reach legacy/route. A-line owns the bounded fix, B-line reviews; root is the controller. Required checks remain not_run downstream of the failure. Runtime review reuses the existing internal development tenant sc_dev_demo, not a customer-production or control-plane database; existing filestore sc_local_dev_odoo_data and filter ^sc_dev_demo$ were confirmed by local.dev.health. No business data writes or resets are scheduled. Restart/build are authorized by the owner takeover and governed Make entries; preserve the existing data and infrastructure.

Affected evidence plan: derive exact list/create/edit/readonly/navigation/relationship keys from the governed target and approved contract for desktop/narrow views. Malformed declarations remain controlled negative tests, not shared database corruption. The sole evidence_scope engine decides reuse. Existing independent passing units are retained; final Quick and publication wait for product convergence.

T5 follow-up fixed by A-line (3 files, 20 new discriminating cases); L1 and collection_view_semantics/collection_row_action_identity passed. Original logs: /tmp/fe-cr02-t5-iteration.log, /tmp/fe-cr02-t5-collection-view.log, /tmp/fe-cr02-t5-row-identity.log. The eight malformed-formal-carrier navigation combinations assert ContractGapError and zero router pushes; absent-carrier compatibility remains.

P4 independent review additionally found closure snapshots not checked against their base_url/database, and record_existing observations rebound with only company identity checked. These invalidate only affected scope import/record paths, not existing product units. Repair source/actor/input binding before new evidence is recorded; never pretend an old observation carried fields it did not capture.

P4 identity follow-up: six existing model/scope/browser/incremental/test files now bind closure snapshots to source URL/database and record actual observation identity + per-unit inputs. Import compares observed/original-plan/current identities and executed fingerprints; missing historical binding is rejected, partial unexecuted siblings are untouched. L1 /tmp/fe-cr02-evidence-iteration-fixed.log PASS; L2 /tmp/fe-cr02-evidence-unit-fixed.log Python66 + JS57 + binding16 =139 PASS. First fixture failure retained /tmp/fe-cr02-evidence-unit.log; recovery changed fixture source identities, not assertions. B-line source re-review PASS.

Runtime preparation: make local.dev.restart SC_SOURCE_REVISION=b5728a5220dabdd98ea1ec9f549df5646c2bcc4d PASS (/tmp/fe-cr02-local-restart.log), readback source_revision exactly b5728a52 and database sc_dev_demo; no module/schema/data writes. make local.dev.frontend PASS (/tmp/fe-cr02-local-frontend-build.log) for current iteration frontend including T5 dirty scope; not frozen evidence. Post-restart make local.dev.health PASS (/tmp/fe-cr02-local-health.log). make evidence.archive.verify read actual original files, 3/3 hashes matching (/tmp/fe-cr02-evidence-archive-verify.log); this is actual local artifact verification, not proof of external archive retrieval.

Approved P4 adapter scope: existing local_dev_payment_request_native_parity_ids.py, floorplan_readonly.sh/.mjs and make/dev.mk; preserve fixed local.dev identity/credentials and before/after readback. Reuse dev_acceptance_release_probe.py and acceptance_contract_receipt.mjs, no new profile. Backend approval precedes browser; observed HTTP request/response must match the approved exact instance and semantic digest. Parameter context derives from system.init, never hardcoded company.

P4 local.dev adapter L1 and registered local_floorplan_contract_binding L2 passed (Python22 + local prerequisite11, existing unnumbered receipt suite also passed). Original log .runtime/agent-runs/FE-CONTRACT-RUNTIME-02/logs/floorplan_contract_binding.log. Approval separates edit and readonly exact record seals; list/create remain live-contract observations, never mislabeled approved record instances. Eight declared keys are list/create/edit/readonly x 1440/390, derived from the existing actor/record/declarations and per-unit inputs through evidence_scope; no full 89-entry matrix.

Runtime attempt 01: both backend approvals PASS for sc_dev_demo/demo_role_finance/company1, b5728a52; browser stopped before any executed key because .first() selected the hidden mobile row at desktop width. Classified P4 locator defect, corrected to the visible declared record row, with production ListPage row-attributes through ScTable as selector authority. Business fingerprint unchanged. Original .runtime/agent-runs/FE-CONTRACT-RUNTIME-02/logs/local_floorplan_runtime_01.log retained. Targeted helper test passed after correction (.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/logs/floorplan_contract_binding_visible.log). Attempt02 is justified by this changed probe input; all eight keys remain uncovered, not a reassurance rerun.

T6 mounted consumer evidence added to the existing readonly_block_component_test.mjs and existing professional_relation_field target: actual X2ManyRelationRenderer.vue retains the blank row, total5, declared page_size2, next/previous events produce 2/2/1 windows, and six invalid declarations reach ContractGapError without publishing a table. Mounted assertions38 (previous attachment15 + collection23) passed; model/descriptor/option/guard subtests also passed. Original .runtime/agent-runs/FE-CONTRACT-RUNTIME-02/logs/mounted_detail_consumption.log. This complements the production visibleOne2manyRows pure tests and does not claim a database sample with nondefault pagination was observed.

Receipt reuse boundary: switching the run environment from offline to the governed runtime makes existing local advisory receipts non-reusable under the current agent context engine, even for unchanged pure tests. Their original results remain referenced with impact analysis; no environment is relabeled offline and no old pass is forged. Runtime approval uses actual authoritative readback; final exact-head gates remain pending.

Owner feedback (same active task): duplicate More controls and persistent current-task/help content must be closed. P0 narrow recordActions were rendered both directly and in mobile overflow; fixed to one responsive host with identity-preserving dispatch, including colon-containing keys and busy/disabled protection. Actual mounted19 + model28 + Python70 passed (header_action_unique_fixed3.log); no new browser claim yet. Native smart groups separately invent a four-action truncation and More label without declaration: explicit open ledger gap blocks freeze until removed or declared. Selected minimal fix is consume all declared visible native smart buttons in original order, preserve existing explicitly declared header/canonical overflow. P1 project-create guidance groups belong in the XML declaration; P0 action feedback must move to interaction carriers, while configuration contract gaps remain persistent stop states. No frontend label/model filtering is authorized.


### 动作提示事实层收口（进行中）

本轮 P0 删除前端 warning/evidence 常驻主体及其无用 props/computed 接线。后端 workflow evidence 仍是动作可用性判定输入；拒绝原因由同记录、同方法的 availableActions.blocked_message 与 reason_code 成对投射到正式 actionRule/buttonStatus，再由动作交互呈现。此变更不删除业务风险事实、审批信息、严格契约缺口停机或操作后字段反馈，不将 actionKeys/evidenceGate 文案猜配为动作权限。P1 创建指导布局声明另批处理。定向反例覆盖旧常驻模板注入和严格停机被删除，浏览器证据待后续受影响集验证。


### 同入口布局事实核查

所有者明确系统未设计角色选择不同布局。相同 action/menu XMLID、视图、记录、公司、编辑态必须共享布局声明；ACL 只影响获权字段/动作与只读，不能切换模板、分区或 layout authority。历史 action807 与当前809 是同一 action_payment_request_user_payment_apply/menu_sc_user_payment_apply，不据数字变化判为不同入口。只读 authority scope 对比普通 actor 的最终契约，保留节点/字段 occurrence、顺序与 span，权限另表；拒绝记 not_comparable，禁止 sudo 补齐 actor 契约。旧图片未与 summary 做 hash 绑定，不宣称精确图片 SHA。

布局核查边界：模型默认视图仅为基础来源，action 绑定的 pay_form 是入口布局基线；ACL 投影负责授权可见/只读/动作，role_key 命中布局配置必须单独报告，不能混称权限裁剪。前端只消费终契约。相同入口、视图、有效编辑态的模板/章节/顺序/宽度不得因角色权限另选或重排（产品约束，尚非本次事实结论）。requested edit 与实际 effectiveRenderProfile 分别记录；模式不同不能作为同编辑态比较。结构保留所有字段 occurrence，原始结构与具体差异保留，差异本身不证明角色因果。

### 同入口跨账号实测与架构边界纠偏

身份仍为 HEAD `b5728a5220dabdd98ea1ec9f549df5646c2bcc4d` 加本运行的显式 dirty scope，未冻结。
Formal Product Layer：P0 平台契约职责、P4 受管只读诊断；Layer Target：视图解析／权限投影边界、既有 local.dev 探针。
Module：smart_core 职责规范及 scripts/verify 工具。本次规范是平台规则，不是付款模型特判或客户偏好；
不在前端猜权限原因，不修改行业字段／角色授权。影响范围为边界文档、已有架构决策、当前结果索引；
文档修正不失效已经通过的组件行为证据，也不宣称机制已全部落实。

原始截图目录 `sce-offrepo/artifacts/playwright/systemwide-public-metric-acceptance` 的报告记录历史 HEAD
`2f4072ca01dd84bc57b4feb1b909e28759812490`、`sc_test_admin`、业务分类任务结构。截图与该报告无独立哈希绑定，
不能当成当前版本页面证据。历史 action807 与当前809 按 XMLID 指向同一入口，不是不同菜单。

本次只用受管入口 `make verify.local.dev.payment_request.floorplan.readonly` 的 `authority` scope，
在 sc-local-dev/sc_dev_demo 内通过实际非 sudo actor 调用后端契约处理器；未重置数据、未跑浏览器或修改业务记录。
它证明当前工作树后端处理结果，不冒称已部署 HTTP 进程或前端构建产物一致。

| 实际核验 | 固定条件／结果 | 原始证据 |
| --- | --- | --- |
| 历史受管记录的当前实例 | floorplan XMLID 当前解析为2880，已办结；两actor实际均readonly，不能证明edit | `.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/authority-completed-record.json`；`logs/layout_authority_runtime_01.log` |
| 现有受管草稿 | `sc_demo_pay_req_010_003`，record3/draft/company1；同action809/menu559、专用pay_form2096；模型基础view1759单独记录 | `.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/authority-editable-record.json`；`logs/layout_authority_runtime_02.log` |
| actor及有效模式 | `sc_test_admin` uid51/system_admin 与 `demo_role_finance` uid43/finance；均env_su=false，effective profile=edit | 同上原件 |
| 实际命中配置 | 两方均145:v2、4:v3、207:v11；role_key均为空 | 同上原件 |
| 布局 | 两方均native_view/container_tree；121结构节点、83字段节点的位置、顺序、类型、标题、span/cols相同 | B线对两份原始树分别递归核验；未承袭readonly结论 |
| 权限及关联差异 | 1434条独立访问标志相同；319原始差异=关联入口260+关联动作权限36+创建／写入属性20+审计授权3，无其他差异 | 同上原件；关联action/menu变化不是主表入口变化 |

结论仅限这个付款申请编辑实例：主表布局相同，关联操作与审计能力不同；不能用角色解释历史截图中的另一套任务布局，
也不能外推所有模型／角色。后端确有role_key配置筛选机制，旧规范也含角色布局作用域；所有者已明确不授权该产品能力。
本轮同步修正 backend_contract_boundaries、native_view_reuse_frontend_spec 和 ARCH-DECISION-003；
角色结构配置的发布／解析拒绝机制尚待专项收口，仍在契约缺陷台账，禁止把文档改动称为门禁已通过。

探针 L1／精准 L2：`layout_authority_iteration_focused_final.log` PASS；`verify.local.dev.layout_authority.unit`
首次5项、补受管editable选择后6项PASS（`layout_authority_editable_unit.log`），begin/record成功。
此前生命周期旧类20测中的3项旧token失败保留于`layout_authority_probe.log`；它未执行新增只读类，
不能据新类通过宣称生命周期全套通过。第二次运行是因为第一次记录已办结，替换为既有草稿这一明确输入变化，
不是对未变失败重复尝试。

补记已完成的实际组件观察：`native_action_browser_hmr_fixed.log` 为NativeFormTreeRenderer桌面／窄屏
声明动作完整性PASS；`action_denial_browser.log` 为ScDropdown+ScPopover桌面鼠标与390触屏、键盘显示、
逐次关闭／打开均PASS且业务事件0。仍不等于目标页面构建、声明升级或整批交付完成。

### 角色作用域布局机制约束（P0，本轮增量）
角色结构检查与旧 native ownership 分类分开：角色配置只保留现有字段可见/只读注解及精确节点权限 patch；标签、组件、章节、顺序、跨度、composition 与整体动作替换显式拒绝。权限裁剪保留节点身份、顺序、跨度，不补成员；原生更严格限制不放宽。发布约束包含 role_key，预览/正式解析同一判据，非法历史配置抛配置错误而非 continue 回退。全局布局仍可合法配置。L1 与定向 L2（135+9+58+5=207）通过，原始日志及边界见 run.role_layout_guard_execution；这不等于真实 ORM 写入或部署验收通过，未重跑浏览器。

### 低代码布局边界补充（2026-10-13）

所有者要求保留低代码布局能力并限定职责。已在原规范 §14.4 与 ARCH-DECISION-003 固定：逻辑分组／顺序／页签／列数／24 单位跨度；稳定出现位置身份及父容器坐标；能力白名单；配置编辑权限与发布作用域分离；后端唯一合成；生效约束不得静默不消费。权限隐藏允许自然空间收缩，不允许改写剩余业务跨度。任意 DOM/CSS/脚本及授权扩张禁止。

本次只修改架构文档和当前 run，无新产品／环境写入；diff 检查及 YAML 解析通过，不使原页面观测失效，也不证明新规范全部实现。角色结构防护独立源码复核通过；真实 ORM 发布拒绝与版本回滚尚未实测。列数默认／夹取、投影坐标映射及受影响实际页面仍待闭合，不能宣布批次或分支完成。

### Columns declaration convergence

Backend210, canonical239 reported +7 column negatives, native layout pure80 + mounted5 + guard22, and strict typechecks passed. Original failed logs remain in the run. Governed columns-authority-editable.json readback verifies both non-sudo edit contracts: 121 nodes, 19 grids, 83 matching widget occurrence spans; native tree coordinates/order/columns unchanged. This is contract projection evidence, not served-browser geometry. Low-code owner/target role separation and real ORM tests remain pending.

### 生成视图基线的受管环境回读

P4 扩展原 local_environment_doctor，只读已验证 profile 的三个精确卷名、Compose 标签与挂载者，不创建环境、不打印凭据。shell/diff 与 ci.local.iteration 通过；原 lifecycle 目标32项通过（含4项实际脚本 mock transport）。原 run登记回执，日志 doctor_readback_unit.log、doctor_readback_iteration.log。

旧 clean 凭据归档仍可解析 sc-local-clean/sc_clean，但受管 local.clean.logs 实测三个固定卷均不存在、无服务容器；证据 view_baseline_volume_readback.log。不能称作仅服务停机，也不能用 local.dev 冒充 clean 生成基线。当前未创建环境。先完成剩余已授权页面工作，再提交精确恢复动作供所有者授权。

### P1 项目创建指导退役：原生回读

首次升级在 fast guard 前置拒绝，未开始数据库升级；按真实模型/XML变更声明 CODEX_NEED_UPGRADE=1 与 CODEX_MODULES 后，既有 local.dev 升级通过。TestProjectInitiationNativeLowcode 实际 15 tests、0 failed、0 errors；两原生视图、字段退役、业务顺序/必填/标签与隐藏依赖保持由真实 ORM 校验。原日志位于当前 run 的 project_guidance_upgrade_declared.log、project_guidance_native_orm.log。

引用回读 guidance-references-after.json 对比原 before：project 指导引用载体 2→0；payment 六项载体及引用内容完全不变。此结果不替代页面几何验收。生成投影仍因原 local.clean 三个固定卷不存在而 blocked，不用 local.dev 冒充 clean baseline，也未新建环境。

### 状态栏最终 occurrence 消费与精确执行恢复

后端来源独立核实：P1 SYSTEM_FIELDS state 与 readonly_all 声明所有模式只读，P0 投射 read；模型禁止普通 state 写入，两个实际账号一致。前端原来选中 statusbar 节点后丢弃 occurrence，读取同名聚合；同字段两个 occurrence 时聚合故意不提供，结果误作 writable。本次直接消费选定 widget 的最终 verdict，并保留同字段 workflow 只读收紧。实际 composable→Header 挂载 34、模型 28、Python 70 与 strict 两配置通过，受管前端已构建；真实页面仍待恢复。

精确 executor 消费唯一 evidence_scope 的 affected 集合；空集合不执行/不记录，新旧部分结果不混用。普通后项失败保留已完成 key PASS，readback/全局错误或业务写企图使完成结果失效。entry 指纹与 form header/semantic seal 分离；本次因工具导航执行控制流实际变化，授权 entry 一次迁移验证，加六个尚未完成产品键，共七键；不是 header 导致 entry 产品失效，不伪造迁移收据。最终 L1、绑定 51 项与生命周期/真实 engine 36 项通过，日志均索引原 run。

### Readonly empty occurrence and payment guidance follow-up

Five consumption keys passed (entry plus edit auth/span at 1440/390); readonly two did not execute after the visible empty cost-category field was omitted. Evidence is preserved under `.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/readonly-occurrence-failure/`. FormSection and canonical native bridge no longer derive visibility from empty values. L1 and layout (80 pure + 9 mounted + 22 guard), canonical, and both strict configurations passed; original failure logs remain. Current consumption did not generate fresh screenshots: old edit PNGs are not current evidence.

Payment guidance remains open at declaration level: the pay view still inherited conditional blocked/review alerts and its productized configuration retained old task/risk guidance anchors. Eligible sample data cannot waive these declarations. Partial P1/P0 changes are retained, but the owner now requires a single structured backend declaration of conditions, fact references, action association, trigger, severity, presentation and continue/block outcome. Dedicated new status branches must be reconciled to that authority before L2 or browser acceptance. Existing action-bound presentation and confirmation executors can be reused; business facts remain persistent, guidance is interaction-bound. No new environment, runtime write or browser was performed by this executor.

Owner refinement: native facts and business guards remain the sole business-decision source. The newly added generic action_guidance module and XML condition/outcome rules are retained as dirty, unvalidated work and must be reconciled; they must not become a parallel fact authority. Configuration may publish fact references and interaction metadata only. No guidance L2, upgrade or browser pass is claimed.

### 风险级别编辑能力边界（当前）

P1原生风险事实与默认soft由同一后端policy消费；现有force_block参数为数据库全局运维设置，不是公司隔离低代码能力。现通用变更集没有risk编辑/发布/回退入口，P3用户调整能力尚未交付，本批不新建设计器或条件引擎。后续仅开放产品支持风险项的severity覆盖，必须合成同份原生policy。

### 正式产品提示族统一收口（最新目标）

付款专用入口修复不代表全局收口。shared payment base/receive 的条件alerts及task字段、execution task/risk锚点和其余正式声明须经同一原生事实用途分类与交互迁移；未声明用途不能由前端当普通事实兜底。当前产品源保持稳定，待独立声明清单及定版执行单。P4新增付款guidance两key和project-create四key的L1与67项定向检查通过，浏览器未执行；旧pay-only观察暂停，不能写验收完成。


### 系统提示统一：根执行器接管（2026-10-13）

两个协作执行器因额度限制中断，root 接回唯一写入职责。身份仍为 `b5728a5220dabdd98ea1ec9f549df5646c2bcc4d` 加明确 dirty 范围，不是冻结候选。完整结果以 run 的 `guidance_system_closure.root_takeover` 为唯一索引。

P1 `native_guidance_form_retirement.xml` 声明八条退役模板；P4 既有生成器按该声明把精确八条生成种子转为不生效的草稿占位，保留 XMLID、其他记录不变；同一 XML function 用于已有库升级。没有手改生成文件、没有安装期校验豁免。原有三条退役重复执行为幂等；补齐其余五条。生成器及原生用途后继声明五项检查通过。新安装还须既有 clean profile 恢复后验证，源码顺序和单测不等于实库新装。

P0 动作通知新增对新记录、录入列表及关联弹窗的受管交接：使用同一原生通知类型，父页 owner 在打开弹窗时创建；关联回复需原 nonce、来源窗口和上下文匹配，不能在收到迟到回复后新建 owner 伪造有效性。已通过 46 项通知行为检查及相关 header/lifecycle 测试、两套严格类型检查；布局 95 项、原生动作声明 66 项通过。用途约束的 217 项结果输入未变，沿用原始日志。

当前进入既有 sc-local-dev/sc_dev_demo 受管升级；升级、ORM、浏览器、最终独立审查、主线集成与用户交付仍未判通过。clean 环境缺失以及协作审核额度中断分别保留为环境与交付审查前置。

本次升级首次拒绝付款登记契约残留的责任提示字段；按原生 `sc_ui_usage` 声明追踪并清除原生视图、产品契约和业务类别策略的同类引用后，第二次受管升级及权威回读通过。六项 ORM 方法首次执行：两项通过，其余四项存在测试身份、收款合同方向、旧提示正文断言和隐藏依赖断言问题；仅修改这些测试输入后重跑四项。隐藏依赖须保持原生 invisible 声明，不得作为可见事实放行。产品代码未因此更改；其余定向证据沿用。

后续两项中，收款原生 soft/per-code/global-hard 路径通过；付款反向断言实际发现 Python 业务策略模板仍引用 `partner_transaction_eligibility_reason`。已在 P1 源删除两处，防回流检查增加实际 Python 模板输出（不只扫描 XML）。五项声明检查与最后付款 ORM 方法通过；六项 ORM 现按受影响集合闭合，原始失败日志保留。此产品变更使策略同步升级失效，正在重新执行 P1 受管升级，前端及其他原生用途机制测试输入未变。

浏览器前置身份首次为 unknown，已用原 local.dev.up 入口注入当前 HEAD 恢复（dirty 范围仍显式记录）。编辑/只读契约审批随后通过，证据引擎选择九项；浏览器在列表入口遇到 P0 单记录提示错误，实际执行零项，未形成通过证据。P0 修复仅在 form 表面求值原生记录提示，列表不读取单记录事实；缺少表面声明或表单记录身份仍失败。同层测试还发现平台菜单配置的正文教程，已迁到原生 menu_id.help；原生布局测试增加恢复 alert 必须失败的反证。149 项 P0 测试与 L1 通过，正在升级 smart_core；前端输入未变，复用已成功构建产物，不重复构建。

## Menu fact unification — owner scope extension, 2026-10-13

Owner requires quick project creation on the formal product surface and complete menu-fact unity. This is P1 product metadata with P0 projection/ACL clipping and P4 generated evidence; no frontend product rule is added. Exact findings and execution status live in run.json `menu_fact_unification`.

The source audit found split ownership: config/product_menu_contract_v1.json owns product paths, scripts/ops/promote_product_ten_center_policy.py owns target bindings and repeats labels/paths, and runtime loads scripts/verify/baselines/formal_business_product_menu_policy_v1.json. Both products currently declare 90 entries without quick creation. Quick is overlaid by four manifest-ordered native XML files and remains in the unpublished set after its native active flag was restored. Native restoration alone is not publication.

Required execution order: consolidate P1-owned menu declarations; make config and locked verification artifacts deterministic projections; validate native identities and hierarchy; restore quick in the unique source and remove contradictory retirement; test drift rejection; upgrade and clean-install readback; observe only affected navigation/create keys. Explicit low-code changes must carry their source and remain distinct from role permission clipping. Historical 62-menu normalization methods have no callers found by repository Python search; that is static residual evidence, not proof of runtime execution.

Known independent prerequisite: clean DB module install command now succeeds after nonempty inactive JSON payload correction, but the overall install fails at dist-clean/runtime-config.js EACCES. Repair the exact output ownership and resume frontend stage; do not repeat successful DB installation to diagnose build permissions. Daily native upgrade succeeded, but formal quick publication remains pending. No unified-menu completion or final delivery claim.

### Native-source consolidation continuation

The owner clarified that editable module source is the first correction point:
native model/field/view/action/ACL facts must not be shadowed by release lists or
persistent generated configurations. External module adapters require explicit
source provenance; actual low-code customization remains a scoped user capability.
The original 90 released menu identities remain the standard edition floor.
Preview includes real unreleased product capabilities, has no 92-entry ceiling,
and excludes development experiments and roadmap-only carriers.

P1 source selection now references native facts in manifest/dependency order;
the ops generator only serializes derived files. Runtime rejects source/projection
drift and no longer prefers image/verifier copies. Missing actions cannot be
fabricated by policy synchronization. Installed menu names, ordering, targets,
and actual actor/company visibility are compared independently of aggregate counts.
The 59-pair observation found no removed/changed old node identities, but eight
pairs had accounting-order drift. Its three external placements have been corrected
in source; the failed command teardown and outstanding runtime recheck remain
recorded in the single run. The later expanded preview scope supersedes that
intermediate affected-set plan.

The current intermediate source contains 90 standard entries and 109 preview
entries. Seventeen restored candidates have independent native business models,
views and ACL declarations; seventeen roadmap-only entries are explicitly retired.
The full native inventory is evidence, not publication authority: other true
business capabilities, duplicate views, internal tools and historical read-only
surfaces still require individual dispositions. No claim that 109 is final.

All 109 historical generated form mirrors now carry inactive, empty payloads;
101 were still effective before this continuation, eight had already been retired.
The generator's new-mirror path was removed. XMLIDs remain only as migration
tombstones for exact existing-database retirement; user-created low-code records
are outside this set. Other semantic-bearing XML cannot be removed before its
unique facts are migrated. For tender.doc.purchase, six unique trace/archive fields
were moved to its native form, their edit/read constraints preserved, attachment
visibility restored to the native declaration, and two conflicting projection
records retired, including an upgrade write outside legacy noupdate data.

L1 and 217 focused backend contract tests passed; eight native migration tests
passed. A stale test requiring at least four configuration records was replaced
with exact active semantic identities while preserving its structure/semantic
behavior assertions. Latest governed local.dev upgrade/readback is tracked in
run.json; neither source tests nor the earlier intermediate upgrade imply current
runtime acceptance, frozen baseline, mainline integration or product delivery.

### Continuation: native retirement readback and retained supply capabilities

Stage identity remains HEAD `b5728a5220dabdd98ea1ec9f549df5646c2bcc4d` plus owned dirty scope; not frozen. The exact noupdate repair upgrade completed. `make local.dev.native_projection.audit` passed four runtime checks: 111 retired configurations inactive/draft, installed standard90/preview109 identities and release states equal the then-current source, and actor51/company1 tender native form delivered all seven retained fields with container_tree/native_view ownership and no effective old configuration. Probe list-vs-recordset assumption was repaired; both original failures remain referenced in the run.

P1 source now retains 20 additional material/labor/equipment/rental/subcontract entries in preview and restores five native parent groups directly beneath the project center. Standard90 identities equal HEAD exactly (no additions/removals); source preview129 retains all original90. Native actions, models and ACL remain their existing source owners. Runtime remains at preview109: new source scope has not been upgraded. L1 passed; projection22, native guards2, contract/ownership14 tests passed. The menu-contract guard was missing preview vocabulary; it now additionally rejects inconsistent or absent release states. Source classification and complete real-user usability remain open.

An offline diagnostic using the real MenuService.build_nav implementation reproduced a P0 version-boundary failure: policy declared menu101 only, role exposure declared101+102, delivered navigation included102. Artifact `menu_edition_native_bypass_diagnostic.json` is mechanism evidence only, not proof of a specific deployed principal. Block further menu runtime publication until product-edition membership is intersected with role/native authorization and platform administration is explicitly separated. Do not solve this by dropping legitimate admin menus or silently narrowing the historical90. Subsequent work resumes from this owning-layer defect, not a full browser matrix. See run.json for commands, original logs, counts and next exact step.

### Continuation: P0 edition navigation and primary authority

P0 MenuService now treats an explicit menu_groups declaration (including empty) as a closed product navigation set. Native menu discovery and role exposure cannot add entries to it. Independent ADMIN_ROUTE/CONTEXTUAL_ROUTE declarations remain separate. Primary/role-home authority is intersected with the final delivered navigation before the existing explicit-denial partition is completed. The admin-role unconditional authorization shortcut was removed; native menu or action/model authorization is still required. Two layout-only unit fixtures now supply native facts instead of relying on that shortcut.

`make verify.backend.navigation_delivery.unit` is the extracted existing backend portion of navigation_shell.unit, plus the existing final-authority integration static tests. It passed 46 tests, including a 12-case role/edition/native-visibility matrix and independent management/context preservation. Earlier failures and changed recovery inputs are preserved in the run. L1 passed (`edition_boundary_final_iteration.log`); no frontend build or browser was needed for this backend-only change. The managed P1 upgrade installs source90/129 in the existing development profile, followed by actor51/company1 standard+preview startup readback. Upgrade/readback final outcomes remain in run.json, not inferred here. Full historical actor monotonicity and complete remaining capability classification are still outstanding.

### Owner clarification: functional capabilities are not customer-data access

The owner explicitly confirmed system-admin functional permissions with no implicit user-business-data permission, and required reuse of the existing capability model. The previous native-ACL-only interpretation of function visibility is superseded. Current candidate uses the existing native platform discovery capability for function visibility, not a role-name grant; action/model data checks remain independent. 48 focused tests pass, but the complete admin path is NOT closed. Actor51 carries many business groups and cannot prove pure platform-admin data isolation.

Research traced startup through P0 capability_provider and P1 capability_registry, while sc.capability in scene_orchestration owns role/group/entitlement/dependency evaluation and permission.check/intent_permission query ORM capability records. Registry/model synchronization must be established per key; different read paths alone are not proof of runtime disagreement. permission.check currently mostly evaluates entitlement flags and can allow on missing entitlement/capability; do not interpret it as a complete function/data grant. Registry role inference also defaults an unresolved role to owner and requires audit. Continue at these existing declaration/evaluation carriers, without adding a parallel permission layer.

The managed upgrade completed (standard90/preview129). Initial two-edition readback passed but the historical navigation comparison caught112->53 nodes. Native authority repair recovered111 nodes before the later function-visibility correction. These are intermediate observations, not final monotonicity or administrator acceptance. The run records exact logs and superseded evidence. No business-data grants were added.

### 管理员与多维数据隔离：所有者确认后的实施边界

所有者进一步明确：统一业务数据归属身份，并同时完善公司、角色、项目的数据隔离。
此前按每条业务记录分别保存 customer/demo/test 分类的建议不作为实施方向。
归属引用现有 `sc.tenant.company.registration` 事实；用途由数据空间唯一声明，
根对象绑定、明细和附件继承。历史混合公司、未注册记录不能整体标记为 demo。

授权结果 = 功能能力允许 ∩ 数据归属上限 ∩ 公司授权 ∩ 项目授权 ∩ 原生 ACL/记录规则。
管理员即使兼任业务角色，也不能扩大到客户业务空间。前端仅消费结果，不改变布局。
切换当前公司/项目属于查询上下文，不构成授予该公司/项目访问权。

实施顺序与责任：

1. P0 原生注册事实：复用 tenant/company registration，声明 customer/demo/test 用途及
   不可自行改归属的约束；保留客户 signed import，演示/测试走用途限定受管入口。
   禁止用客户端 context 布尔值、数据库名、记录名或 XMLID 直接授予数据访问。
2. P1 模型事实：逐类声明根归属、父单继承、共享产品元数据和 SQL 投影分区。
   res.partner 中认证身份与客户往来单位必须区分；company_id=False 不代表公开。
   无项目单据也必须有归属；SQL 汇总必须在聚合前保留归属，原表规则不自动保护 SQL。
3. P0/P1 原生授权：管理员限制为全局 AND 上限，不能用会被组规则 OR 扩大的组限制；
   保留现有能力模型，分别验证 ACL 操作许可和数据规则，不授予全部业务组补菜单。
4. 业务调用：读写、导出、附件、统计、关联和派生记录遵守同一归属；消除未经授权 sudo。
5. 受管验收：纯管理员、管理员+业务组、普通业务角色，覆盖 customer/demo/test/未知归属、
   跨公司/跨项目、直读/list/count/read_group/export/附件及创建/修改/删除。
   当前 sc_test_admin 混合角色观察不能替代纯管理员证据。

本轮实际有界修复：payment_slice_entry_service 移除查询/创建主动 sudo；传入项目与伙伴
重绑调用环境后检查 read ACL/rule，付款 create ACL 在解析关联前检查。7 条定向替身测试
通过（包含拒绝不写入、传入特权 recordset 重绑、不得 sudo 重试）。独立 B 线复核通过
此有界结论；服务如果整体传入 sudo env，仍不受此修复覆盖，完整数据隔离尚未实现。

原始证据：`.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/logs/payment_slice_data_authority_unit.log`。
L1 首次因新路径未登记 run scope 失败；修正准确路径后运行
`admin_data_boundary_iteration_scoped.log`。未执行升级、浏览器矩阵或 Quick；原因是
归属事实与全模型覆盖的前置尚未完成，不把局部服务测试当作系统隔离验收。
# 数据边界体系补充（2026-10-13，进行中）

所有者后续批准收敛实施强度：所有访问路径须受正确边界约束，不要求每个模型新增全部隔离字段，
不建设平行权限引擎。完整注册表 744 项（510 持久模型、118 transient、116 abstract）为检查范围，
不是重写清单。复用 native company、父关系、ACL 与 ir.rule，仅补事实缺失和绕过点。

工资源模型已补原生公司归属、可选项目一致性、父对象公司变更约束、付款明细继承、
状态与付款派生值入口保护。最终两项 context 默认状态／带付款事实转工资缺口通过新增反例，
与原项目工资发放守恒用例合计 3 项通过；此前测试按影响保留，不能把重复执行次数当覆盖数量。
模型和汇总的生产升级、用途规则接入仍未完成。

P0 用临时 native `res.company` 记录规则验证机制，未激活生产公司规则：实测删除注册后缓存
仍放行（1 项红例），修复成功删除后的 registry cache 失效；6 项原生规则用例和签名删除
用例通过，再单独补公司授权撤销／旧上下文拒绝 1 项通过。作用域、精确命令、失败与通过的
原始日志仅登记于 run 的 `admin_data_isolation.native_rule_validation_plan`。
该证据证明原生全局规则交集、组规则并集和缓存撤销机制可用，不代替业务 create/write、
附件、SQL 汇总及 sudo 服务的逐路径验收。

所有者要求整套数据边界一次收敛。架构权威已在
`docs/architecture/backend_contract_boundaries.md` 的“统一数据事实与授权边界”固定：
归属、用途、共享、公司／项目、操作权限五个维度相交；公司／行业／平台共享不扩大用途边界。
执行与原始证据仍只登记在既有 run，不建立第二张结果台账。

P0 原生注册与用途解析已有 12 个纯策略、20 个真实 ORM 用例通过；其中 ORM 是原先 18 项
加新增签名删除／公司初始化范围 2 项，未重复原套件。该结果不证明业务记录规则已经接入。

B 线对 31 个非自动表模型完成源码分类：6 个明确聚合缺口、16 个保留归属但规则待接入、
8 个源码空投影、1 个物理 provider 协议缺口。共享资料审计发现启动字典消费者把公司配置
映射为全局配置；根模型原生归属与发布声明需先补齐，不能豁免整个“字典”模型。

本次 P1 工资汇总修复公司／项目／币种分组及下钻，拒绝未知归属参与汇总，统一空值分区，
不再以任意公司的币种补齐来源。真实 ORM 建单、完成、SQL 汇总和下钻 6 项通过；测试中
事务性创建的候选视图随回滚恢复，不是日常服务器升级证明，也不是用途授权证明。
首轮 4 项通过后，独立评审指出空归属与空值问题；更改 SQL 输入后仅重验这个受影响类的
4 项及 2 项新反例。命令、原始日志、精确用例和未覆盖项见 run 的
`admin_data_isolation.salary_projection`。

后续顺序：完成原生模型分类与余下投影／provider 修正 → 公司、行业、平台参考资料的
归属与发布载体 → 全局权限上限及关联写入约束 → 受管升级 → 逐入口允许／拒绝验证。
已知缺口关闭前不冻结、不跑完整浏览器矩阵、不宣称全产品数据隔离完成。

工资根单、付款明细和汇总已接入同一原生全局公司／用途规则，候选 XML 在真实 ORM
事务中加载验证后回滚。7 个独立用例覆盖列表、直接读、导出、聚合、建单、写入、父对象
及撤销边界；导出先证明允许端，再验证拒绝端。精确失败、恢复和未变用例复用记录于 run，
不能将事务测试描述为服务器已升级。只读运行时核对仍为 blocked：日常库没有有效公司注册，
两条工资属于未注册公司 1，汇总列和安装规则待升级；不按数据库名称推定历史数据用途。

P4 原有验收数据创建器改为通过 P0 注册入口创建原生 test 公司；未注册历史公司、其他
租户及同名无归属数据拒绝认领。验收用户显式获得非客户数据身份，功能仍由原业务组决定。
公司注册生成的 P1 税率只读引用，不再由 fixture 重复创建或绑定所有权。活动凭证原先
从全库取第一本日记账，现改为在本 fixture 的已注册测试公司创建／复用自有日记账，
消除隐式使用其他公司数据的路径。

此差量的验收范围为 17 个不重复真实 ORM 方法：7 个身份边界、3 个税率引用边界、2 条原业务链、
5 个日记账／凭证归属用例。新税率测试首次错误假设税率名称可任改且 copy 可生成重复，
按实际 P1 规范化／去重行为修正测试输入后，仅重跑受影响的两项；业务断言没有放宽。
原始日志、命令与各次失败保留于 run 的 `admin_data_isolation.fixture_identity_slice`。
未执行完整 fixture 初始化，未重标记历史数据，未激活持久规则，未冻结或集成主线。

B 复核补充发现固定旧 XMLID 可能经通用 upsert 跨公司迁移；仅在活动日记账和凭证 helper
补齐已注册测试公司及既有 model/company 校验，不改通用 upsert。新建与旧 XMLID 重用都须
守住公司事实；旧归属不符要求受管 reset。仅重验 3 个受影响活动用例及 2 个新反例。

Step 1 下一项：销项发票台账 `sc.output.invoice.ledger`（`_auto=False` 的 SQL 视图）的
收款发票去重窗口原按发票号单列分区。不同公司或不同币种打印出相同发票号时被合并为一条，
`ROW_NUMBER()=1` 只保留一行，另一公司的发票静默消失。修复为按
`（规范化发票号，项目公司 company_id，币种 currency_id）` 三元分区，新增
`LEFT JOIN project_project` 取项目公司，并在登记反连接上补公司维度，避免其他公司的
登记行压掉本公司的收款行；收款行金额按公司／币种分别守恒。

验证：L1 `ci.local.iteration` PASS（16 tests，日志
`invoice_ledger_partition_iteration_resolved.log`）；离线静态边界守卫 9 tests OK
（新增用例断言所有 `PARTITION BY` 行同时含 `pp.company_id` 与 `ril.currency_id`、存在项目
JOIN、反连接含公司断言；日志 `invoice_ledger_static_boundaries.log`）；旧源码反例使该守卫
FAIL。L2 定向 ORM 反例 1 test 0 failed（日志 `output_invoice_ledger_cross_company_orm.log`）：
同号发票在两家公司各建一条收款行，断言两条均在、金额各 100.0／250.0 守恒、合计 350.0；
旧源码同用例 1 failed。3 个改动文件 `py_compile` 通过。

残余与边界：`sc_dev_demo` 只有单公司数据，混公司反例由事务内 ORM 用例覆盖，不为此重置
fixture；事务内 `Ledger.init()` 随回滚恢复，不是日常服务器升级证明。`sc_dev_demo` 中已安装的
`sc.output.invoice.ledger` 视图仍是旧定义，受管模块升级与部署视图回读待写授权，不据此
宣称已部署。下一项：`sc.p1.relationship.review.queue`。

Step 1 下一项：P1 关系人工复核队列 `sc.p1.relationship.review.queue`（只读派生视图）的
项目归属。原 `grouped` CTE 对每个「来源模型＋来源字段」分组取
`MIN(project_id) FILTER (WHERE project_id IS NOT NULL)`，分组根本不按项目切分；一个跨多个
项目的分组因此被发布成某一个任意项目，视图与列表还提供「按项目分组」的入口，属于把
错误归属直接暴露给复核人。修复为仅当该分组全部候选属于同一个项目时才发布项目
（`COUNT(project_id) = COUNT(*) AND MIN(project_id) = MAX(project_id)`），混合或含未知
归属一律留空。来源表无 `project_id` 列的模型（如 `sc.business.entity`）自然为空。

验证：L1 `ci.local.iteration` PASS（日志 `relationship_review_queue_iteration.log`）。
L2 定向 ORM 反例 1 test 0 failed（日志 `relationship_review_queue_project_orm.log`）：
同一分组内两家项目各建一条 `sc.financing.loan` 候选，断言该分组不发布任何项目，并另用
独立 SQL oracle 复核「仅单一项目才发布」；再断言无项目列的来源分组不伪造项目。
负向对照：还原 HEAD 旧视图后同用例 1 failed
（`AssertionError: {project.project(5883,)} is not false`），日志
`relationship_review_queue_project_orm_negative_control.log`；修复源随后已恢复。

残余与边界：`Queue.init()` 仍在事务内建视图并随回滚恢复，不是日常服务器升级证明，
`sc_dev_demo` 中已安装视图仍为旧定义；受管升级与部署视图回读同样待写授权。
下一项：Step 1 剩余投影（`sc.ar.ap.company.summary`、`sc.finance.counterparty.position.summary`、
`sc.ar.ap.project.summary` 及 20 项归属待定源模型）。

## 执行器交接计划（2026-10-13，所有者要求记录后停止）

### 批次信息与入口

- 沿用唯一批次／run：`FE-CONTRACT-RUNTIME-02`，不新建平行结果表。
- 当前直接目标：从原生事实到访问路径完成客户／demo／test 双向隔离，保留管理员功能能力，
  为本分支整体收口提供可验收基础；不是仅让工资或 fixture 测试通过。
- 分支：`fix/fe-contract-runtime-02-consumption-stop-closure`；交接 HEAD：
  `b5728a5220dabdd98ea1ec9f549df5646c2bcc4d`，工作区含大量既有已跟踪和未跟踪改动，未冻结。
- 唯一索引：`.agent/runs/FE-CONTRACT-RUNTIME-02/run.json`。本节是执行方案，结果仍写回 run。
- 允许范围：P0 `smart_core` 原生注册、授权机制与共享声明；P1 `smart_construction_core`
  事实模型、标准权限和投影；P4 已有受管测试与 fixture。逐层实施与复核，不混成一个大补丁。
- 不做：重写 744 个模型、给所有模型复制五组字段、另建权限引擎、凭名称重标历史数据、
  给管理员叠加全部业务组、在前端修权限、创设新数据库／profile／凭据或绕过门禁。
- 首次接手依次执行 `pwd`、`git rev-parse --show-toplevel`、`git branch --show-current`、
  `git status --short`、`make agent.run.resume`；读 run 和本节，只核对发生变化的身份／依赖。
  不 reset、不 clean、不 stash 掩盖现场，不重新完整盘点菜单、仓库或环境。
- A 是唯一写入者；B 做同层只读复核。B 可并行审计不争用运行时的独立源码，不能共同改文件。
  共享验收库的测试／升级串行执行。交接后由新执行器接管，原执行器停止。

### 已通过证据如何复用

原始日志统一位于 `.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/logs/`，具体命令和限制见 run。

- P0 注册／用途：12 个纯策略及 20 个 ORM；原生规则组合与撤销 8 个相关 ORM 已通过。
  这些是机制证据，不代表全部产品规则已安装。
- 工资源模型、状态／付款入口、SQL 分区及下钻已修；工资根单／明细／汇总 7 个独立
  规则方法已覆盖允许和拒绝。候选视图和规则在测试事务中加载后回滚，不是持久升级。
- fixture 共 17 个不重复方法：7 个身份边界复用 `fixture_data_scope_orm.log` 中已通过方法；
  缺失税率及两条原业务链复用 `fixture_native_tax_orm.log` 中已通过方法；
  2 个税率恢复用例见 `fixture_native_tax_recovery_orm.log`；
  5 个活动归属用例见 `fixture_journal_ownership_orm.log`，替代较早的 3 个活动用例。
  原命令包含失败仍记失败，不改写成整次 PASS；复用单位是有确定输入依赖的已通过方法。
- fixture 源头保证新测试身份；税率引用不认领；活动链拒绝误用公司和旧 XMLID 跨公司迁移。
  B 有限范围审查通过，但尚未执行 `ensure_fixture` 整体持久初始化。
- 每次修改先登记 changed inputs → affected keys → 复用理由，再执行精确集合。
  使用现有 `scripts/ops/evidence_scope.py` 权威，不建立新的检查专用缓存。

### 实施顺序与完成判据

#### Step 1：关闭剩余事实与 SQL 分区缺口（P1）

依赖：接手身份与 run 有效。**下一项具体动作**：定位
`sc.interfund.movement.project.summary` 与其 `sc.interfund.movement.fact` 来源，
核对公司／项目／币种原生字段和现有测试，先为混公司／混币种及下钻越界建立反例，
再修来源或聚合归属；禁止只把 `MIN(company_id)` 换成表面字段而保留混合分组。

随后按已有审计逐项处理，不重新审计所有 SQL：

| 模型／范围 | 已知问题与必要产物 | 完成判据 |
| --- | --- | --- |
| `sc.interfund.movement.project.summary` | 公司／币种取 MIN，分区与下钻需一致 | 同项目／类型不同归属和币种不混合，下钻精确 |
| `sc.output.invoice.ledger` | 发票号独自参与去重／窗口，可能跨公司 | 同号不同公司不合并，金额守恒 |
| `sc.p1.relationship.review.queue` | 多来源项目用 MIN 归并 | 来源归属明确，未知或混合归属不可公开 |
| `sc.ar.ap.company.summary` | 项目维度不能代替公司，空项目混合 | 有公司无项目仍按公司隔离，未知归属拒绝 |
| `sc.finance.counterparty.position.summary` | 丢失来源项目边界 | 公司／项目权限不能被汇总绕过 |
| `sc.ar.ap.project.summary` | 物理 provider 缺公司协议 | 保留物理表和数据，提供可验证来源边界，禁止 drop 当视图重建 |
| 已分类的 20 项归属待定源模型 | 优先 workflow.instance、tier.review、material.price；再处理可选项目事实 | 业务记录继承真实业务根，不从流程模板或当前环境猜公司 |

`sc.salary.summary` 已有证据，不因开始另一模型重新跑。其余 16 个保留归属的 SQL 模型
还需规则证明；8 个源码空投影不能记作可用产品。220 个 P1 模型的分类表在 run，
对其余注册模型只补适用性结论／真实访问路径，不做无差别字段改造。

输出：源事实修复、对应投影／下钻修复、非零定向测试、B 复核和 run 差量结果。
每个家族 L1/L2 通过后处理下一家族；已知同层失败先处理，不靠 Quick 发现兄弟缺陷。
风险／回滚：分组变化影响总额和 ID，须测试金额守恒与引用；仅回退本次家族变更，
不回退他人／历史工作区，持久 SQL 升级前保留受管恢复路径。

#### Step 2：完成共享参考资料原生归属与发布（先 P0 声明，再 P1 标准）

依赖：Step 1 的根归属口径可用；可先做只读设计，不得先改消费者绕过缺声明。
定位 `smart_core/core/system_init_dictionary_data_helper.py`：现有 sudo 消费把公司级字典
映射为 `__global__`，这是已确认缺口。先查 `sc.dictionary` 原生模型及 scope_ref 载体，
补公司／行业／平台范围、明确发布状态和发布权限，再调整契约投影消费。
公司、行业、平台共享仅适用于显式参考资料；客户业务事实不能靠发布或 company=False 变公共。

输出：原生声明、发布／撤销权限、契约读取与缓存失效测试。具体载体在源模型决策中记录，
禁止先建一份配置表替代模型事实。完成判据：未发布不可见、授权范围外不可见、撤销立即生效、
共享不赋予修改权、客户与测试用途边界不被扩大；res.partner/users/bank 的必要身份引用
只声明最小字段，不豁免整个模型。风险／回滚：防止公开面扩大；失败保留拒绝，不兜底全局。

#### Step 3：接入剩余原生规则和真实访问路径（P0 机制／P1 声明分开）

依赖：对应模型的 Step 1 归属已明确，涉及共享的模型 Step 2 已通过。
复用 `_sc_data_company_ids()` 与 Odoo 全局规则交集，不改变组规则并集的原生语义。
按家族覆盖 root/detail、附件、关联字段、read/search/name_search/export/read_group、
写入／导入、流程执行及 sudo 服务；每一项记录适用、已证明或明确阻断，不能只测菜单。
单独使用“纯产品系统管理员”验证能力模型；现有管理员＋业务组测试不等于纯管理员功能验收。

完成判据：管理员可办授权功能但客户数据不可见；普通用户客户数据允许、demo/test 拒绝；
专用测试用户仅允许非客户空间；公司／项目／操作权限继续相交；混合角色不能放大用途上限；
已知 ID、关联父对象、聚合和 sudo 服务无旁路。输出为每类允许与拒绝实测证据。
风险／回滚：全局规则可能锁住合法功能，必须先证明合法端；不能删除规则恢复“可用”。

#### Step 4：准备并升级受管基线（P4，前置未满足不得执行）

依赖：待激活范围的 Step 1–3 L1/L2 通过，且原生注册、凭据、数据角色与恢复路径已明确。
当前只读 readiness 已给出：`sc_dev_demo` 有效注册 0、公司 1 有两条工资、汇总列／规则未升级。
这是 blocker，不能凭 `sc_dev_demo` 名称将公司 1 注册成 demo/test。

复用 `make local.dev.*`、`sc-local-dev/sc_dev_demo`、固定卷和既有凭据。
`make local.dev.payroll.data_scope.readiness` 的现有失败先复用，只有相关环境事实改变才重跑。
既有 fixture guard 仅声明 `sc_frontend_acceptance` 和旧 `sc_demo`，不允许直接在
`sc_dev_demo` 调 `ensure_fixture` 绕过 guard。需要适配时走最小 P4 受管入口改动，明确
现有环境权威、精确作用域、非零工具测试、恢复和写后回读；不得手拼 Compose／数据库命令。
用户已允许开发数据适配和隔离验收，但这不代替工具对具体重置对象的身份／确认要求。

输出：复用或受管重建的已注册基线、备份／恢复点、精确模块升级结果、权威回读。
先核对现有 `make local.dev.upgrade` 参数和升级依赖，不在计划里猜造写命令。
完成判据：合法 test/demo/customer 数据来源明确；安装视图／规则等于候选声明；fixture
整体初始化及幂等通过；历史未注册行有明确处置，不得以“查不到”充当迁移成功。
风险／回滚：仅用受管恢复入口还原匹配 DB/filestore；失败停止后续浏览器与发布。

#### Step 5：分层产品验收与本分支剩余阻断对账（先后端，再前端）

依赖：Step 4 回读通过。先验后端真实角色契约、允许／拒绝结果，再以确定契约验前端消费。
布局来自模型／动作正式视图，角色只裁剪可见／可办，不重新布局；readonly 保留权限／状态
原因。统一提示、快速创建、标准／预览产品边界和菜单单调性仍属原分支目标。

首先逐项对账 run 顶层既有 blocker（含 P3 提醒强度编辑／发布、菜单产品／平台边界、
预览停用项、纯管理员能力与历史菜单、旧运行中记录）。有有效完成证据才清除，旧文字不
自动认定现在失败或成功，也不能在完成数据隔离后遗漏这些原目标。
菜单口径按用户“标准产品至少 90、原可见只能多不能少、真实预览能力保留”及已登记事实
逐项验证，不用旧 89 或中间 92/109/129 的总数替代职责验收。

使用 `make verify.frontend.business_entry.matrix.incremental` 等既有入口按影响集执行；
冻结前产品复核只覆盖受影响面。完成判据：后端事实→运行时契约→前端行为三段对应，
所声明验收集合 uncovered=0，正反例真实命中，未声明权限／文案／默认产品语义不由前端补齐。
失败返回责任层，不放宽探针、不重跑无关矩阵。截图是观察，不能代替契约和交互结果。

#### Step 6：冻结与交付边界（P4）

依赖：所有本次交付 blocker 关闭、B 独立复核、阶段产品复核通过。更新生成证据和文档，
按实际选择的发布车道执行现有 Make 门禁；用户既有方向为 GitHub 优先，先核验现有远端，
不能因仓库同时存在 Gitee 规则就自行切换。适用 GitHub／正式交付车道时，干净候选完整
指纹绑定一次 Quick、独立审查、远端检查与外部归档。Gitee 特定例外不外推到其他车道。
不同 SHA／目标基线不能继承远端通过；不直接推 main，不将合并等同部署。

完成状态分别回报：批次验收、主线集成、版本发布、用户产品验收。只有目标环境中的账号、
数据边界与关键业务闭环通过才能称产品交付完成；最终 17 项 fixture 通过不代表任何后三项。

### 验证与停机规则

- 每个修改先登记层级、风险、最早验证层和跳过理由；默认 `make ci.local.iteration`
  为 L1，再用 `make local.dev.test MODULE=<所属模块> TEST_TAGS=<精确类或方法>` 做非零 L2。
  上述占位符须由已有测试实际名称解析，禁止把占位符原样执行。
- `make verify.data_space.policy.unit` 仅在相关纯策略输入变化时重跑；规则／模块改变需要
  实际 ORM，不用静态 token 出现证明授权效果。契约改变才更新相应快照并检查消费者；
  UI smoke 等后端与安装态通过后执行。L0–L5 不得跳过失败前置。
- 验证失败停止受影响下游，可继续独立且前置已通过的廉价检查；不重复同输入失败命令。
- 未知数据归属、共享发布语义未定、数据库身份不明或工具强制确认未满足时，停止依赖写入；
  先完成可独立的源码／测试工作。已有授权不重复询问，但不得靠延时或历史计划推定写授权。
- 本次交接仅写计划与台账，不新增产品修改、不运行产品测试、不升级、不提交、不推送。

## 接手执行器 A／B 段收口记录（2026-10-13，FE-CONTRACT-RUNTIME-02）

### A 段：往来对象位置 oracle 分区收口

- 缺陷：两个已接线审计守卫 `verify.finance_project_counterparty.position.audit` 与
  `verify.finance_counterparty.position_summary.audit` 的行数 oracle 重建聚合时漏
  `company_id`／`currency_id`，而被验证的投影视图把公司、币种作为身份键的一部分。oracle
  键因此严格更粗，跨公司／跨币种塌缩对它不可见：当投影把两家公司或两种币种的往来对象位置
  并成一行时，守卫仍显示 PASS。
- 参考正确写法：`addons/smart_construction_core/models/projection/interfund_movement_project_summary.py`
  （`GROUP BY project_id, movement_type, company_id, currency_id`）。
- 修复：两个审计脚本的 `GROUP BY` 补齐 `company_id, currency_id`——summary 1 处；
  project 4 个 CTE 分支各补 `f.company_id, f.currency_id`，以及 oracle 1 处，使 oracle 键
  与投影身份键一致。
- 新守卫：`scripts/verify/finance_position_audit_partition_guard.py`——静态扫描 2 个投影模型
  与 2 个审计脚本，凡 `GROUP BY` 已含身份锚 `counterparty_project_id` + `counterparty_name`，
  就必须同时含 `company_id`、`currency_id`；含 `--selftest`。
  防回归单测 `scripts/verify/test_finance_position_audit_partition_guard.py`（3 用例）。
- 接线：`verify.finance_position.audit_partition_guard`（`make/runtime_ops.mk`），
  作为 `verify.finance_interfund.position.all` 前置。
- 证据（`.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/logs/`）：
  - `finance_position_partition_guard.log`：守卫 PASS，`Ran 3 tests ... OK`。
  - `finance_position_audit_partition_guard_selftest.log`：`SELFTEST_PASS`。
  - `finance_position_audit_partition_guard_negative_control.log`：修复前 HEAD 上两脚本
    各报 company_id+currency_id 缺失共 4 处（负向对照，exit 0）。
  - `finance_position_audit_oracle_equivalence.log`：`sc_dev_demo` 只读 psql，改后 oracle SQL
    与投影一致（summary 3=3；project position 3=3）。
  - `finance_position_audit_partition_iteration.log`：`make ci.local.iteration` PASS（L1_only，dirty）。
- 边界：本轮未做数据库写入，psql 全只读。`sc.ar.ap.company.summary` 与 `sc.ar.ap.project.summary`
  均为 `_auto=False` 普通表（`relkind=r`），当前 `sc_dev_demo` 中 0 行，无公司／币种维度；
  补齐属破坏性 schema 变更（`AR_AP_COLUMNS` 受指纹校验，`refresh_ar_ap_project_summary` fail-closed），
  留待 Step 1 剩余投影单独裁定。

### B 段：两个必需远端门禁的验证面棘轮修复

两个门禁同属 `ci.professional.backend.shard-verify` 必需链，不修则无法合并。9 项零引用目标与
7 个 unwired 脚本 100% 源自本分支 `2acccf85` 新增工具未接线（main 上不存在）。本次是**接线**，
不是修改基线。

- 门禁 1 `make audit.verification.lane_coverage.check`：
  - 原 FAIL：`targets_zero_reference 769 > 760`、`unregistered 9 > 0`，且 9 项在冻结身份集外。
  - 修复：6 个 L2 单元接入 `verify.contract.architecture.suite`（`make/ci.mk`）——
    `verify.product.menu.monotonic.unit`、`verify.product.menu.native_inventory.unit`、
    `verify.local.clean.frontend_output.unit`、`verify.payment_slice.data_authority.unit`、
    `verify.data_space.policy.unit`、`verify.local.dev.layout_authority.unit`；
    `make/dev_test.mk` 新增 `verify.product.menu.native_inventory.unit`；4 个运行时目标按其脚本
    docstring 声明入口目标名（与既有 `local_dev_menu_fact_snapshot.py` 惯例一致）：
    `contract.product_menu.generate`、`local.dev.native_projection.audit`、
    `local.dev.data_scope.inventory`、`local.dev.payroll.data_scope.readiness`。
  - 证据：`lane_coverage_closure.log` PASS；`verification_lane_coverage_closure.log`
    `Ran 69 tests ... OK`；`lane_coverage_selftest.log` `Ran 69 tests ... OK`。
- 门禁 2 `make verify.guard.registry`：
  - 原 FAIL：7 个 unwired／orphan 脚本。
  - 修复：`scripts/verify/registry.yaml` 新增 8 条 `wire_or_retire: file-consumed` 登记
    （`menu_fact_monotonic.py`、`product_native_menu_inventory.py`、`test_data_space_policy.py`、
    `test_local_clean_frontend_output.py`、`test_menu_fact_monotonic.py`、
    `test_payment_slice_data_authority.py`、`test_product_native_menu_inventory.py`、
    `test_finance_position_audit_partition_guard.py`），理由为模块式 `python3 -m unittest`
    调用是粗文件名匹配看不见的文件引用。
  - 证据：`guard_registry_closure.log` PASS（1437 scripts，198/198 unwired dispositioned，
    3/3 gate_required enforced）。
- 新接入 suite 的 6 个单元已逐个实跑确认非零通过，且均为纯 Python／bash，不依赖前端
  node_modules（遵从 `make/ci.mk` 对 tsc 车道隔离的既有约束）：`new_suite_prereqs.log`
  （6/2/2/7/12/6 tests 全 PASS）。
- 未改 `scripts/audit/verification_lane_baseline.json`；未执行 `guard.registry.export`
  （`registry.yaml` 与 `docs/audit/guard_registry/guard_registry.json` 是不同文件）。

### 本轮状态

- 批次验收：A／B 段目标完成，非零定向测试与 L1 通过；`ci.delivery.freeze.prepare` 与
  最终 Quick／远端门禁待干净 HEAD。
- 主线集成、版本发布、用户产品验收：均未达成。
- 下一步（Step 1 剩余投影）：`sc.ar.ap.company.summary` 与 `sc.ar.ap.project.summary` 已按
  非破坏性归属边界收口（见 D 段）；`sc.finance.counterparty.position.summary` 及上游已核对
  按完整属性分组、无塌缩缺陷。下一项是 `sc.output.invoice.ledger`（发票号可能跨公司去重），
  再 `sc.p1.relationship.review.queue`（多来源 MIN 归并），之后处理 20 项归属待定源模型
  （优先 `workflow.instance`、`tier.review`、`material.price`）。

### C 段：冻结准备暴露的两个本分支回归（已修其一，另一个为刻意门禁）

执行 `make ci.delivery.freeze.prepare` 时按顺序暴露两个阻断：

1. **`contract.semantic.registry.generate` ImportError（本分支回归，已修）**
   - 现象：`make verify.semantic.registry.lint` 与冻结准备的生成步骤均以
     `ImportError: attempted relative import beyond top-level package` 失败。
   - 根因：`core` 是双根包——Odoo 以 `smart_core.core.*` 导入，而语义注册表构建脚本
     （`scripts/contract/generate_semantic_registry.py`）与其定向测试
     （`addons/smart_core/tests/test_contract_runtime_semantic_resolver.py`）刻意以顶层 `core.*`
     导入（把 `addons/smart_core` 放进 `sys.path`，避免触发 `smart_core/__init__.py` 的 Odoo 引导）。
     本分支 `cfd8580e` 给 `unified_page_contract_v2_assembler` 新增
     `from .field_presentation_usage import ...`，该模块又导入
     `form_configuration_compiler`，其模块级 `from ..utils.backend_contract_boundaries import`
     只在 `smart_core.core.*` 身份下成立，于是在顶层 `core.*` 身份下 `..` 越过顶层包。
   - 修复（P0 内核导入边界，单文件最小根因）：`addons/smart_core/core/form_configuration_compiler.py`
     改为双根导入——优先 `..utils`，仅当 `ImportError` 文本确为相对导入越界时才回退
     `utils.backend_contract_boundaries`；其它导入失败一律 `raise`，不吞真实缺陷。
   - 证据：`tools_import_shapes.log`（两种导入身份均可用）；`semantic_registry_lint_diag.log`
     （修复前 FAIL，同栈回溯）；`semantic_registry_lint_diag2.log` 与 receipt
     `semantic_registry_lint`（修复后 `verify.semantic.registry.lint` 全链 PASS）。
   - 潜在同类：`core/context.py`（`..security.auth`）与 `core/system_init_payload_builder.py`
     （`..utils.product_release`）具有相同形态，当前不在顶层 `core.*` 导入路径上，未改；
     若后续被工具链触及，按同一方式收口。

2. **`verify.frontend.contract_basis.enforce` 契约缺陷 STOP（刻意 fail-closed，未修）**
   - 现象：`[frontend_contract_basis_guard] STOP 存在未闭合的契约缺陷：交付（freeze）车道禁止放行`，
     缺陷 `CD-20261013-LAYOUT-COLUMNS-FALLBACK`——缺失时
     `NativeFormTreeRenderer.normalizeColumns` 默认 columns=2、`FormSection` readonly
     `descriptionColumns` 夹取到 1..3/2，均无声明权威。
   - 判定：该缺陷条目在 `origin/main` 上不存在（main 的 `openContractDefects` 为空），属本分支
     登记；`verify.frontend.contract_basis.enforce` 只被 `ci.delivery.freeze.prepare`（本地交付车道）
     消费，不在远端必需门禁内。按计划该收口属 T2／Step 5（声明层补齐 + 前端原样消费、缺失即
     ContractGapError 停机），**本轮不做**。
   - 结论：交付冻结在缺陷闭合前保持 fail-closed，属预期；本批次作为迭代提交，不宣称冻结通过。

### D 段：Step 1 剩余投影——AR/AP 汇总公司归属边界（非破坏性裁定）

- 对象：`sc.ar.ap.project.summary`、`sc.ar.ap.company.summary`（`_auto=False`，物理表 `relkind=r`，
  `sc_dev_demo` 中 0 行）。
- 裁定：拒绝破坏性 schema 变更。物理 provider 的 14 列签名与
  `AR_AP_EVIDENCE_STRUCTURE_FINGERPRINT` 被 `refresh_ar_ap_project_summary`、
  `migrations/17.0.0.73/pre-migration.py`（就地保留）与单测共同锁定；新增公司列会打断冻结的
  迁移路径，且该 provider 无填充器、当前 0 行。改为**可验证归属边界**：公司锚点＝项目。
- 来源边界（P1，`projection_relation_lifecycle.py`）：`refresh_ar_ap_project_summary` 在
  `stage=project_isolation` 之后、正式 `ON CONFLICT` 写入之前新增归属校验——`stage.project_id IS NULL`
  或 `project_project.company_id IS NULL`（`LEFT JOIN project_project company_anchor`）命中即
  `AR_AP_PROJECTION_REFRESH_VALIDATION_FAILED:...:stage=company_ownership`，整事务回滚。
  迁移路径只调用 `ensure_ar_ap_project_summary_provider`（保留／创建），不调用 refresh，
  因此本次不改升级行为。
- 访问边界（P1，`security/sc_record_rules.xml`）：两模型此前对 7 个组有读 ACL 但无公司规则，
  存在跨公司可见。新增全局只读规则 `rule_sc_ar_ap_project_summary_company` /
  `rule_sc_ar_ap_company_summary_company`，域
  `[('project_id.company_id', 'in', company_ids)]`；无项目或项目无公司的行归属未知，保持拒绝，
  不由标签或当前环境回填。
- 证据（`.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/`）：
  - `logs/arap_ownership_boundary.log`：`Ran 17 tests ... OK`
    （14 生命周期 + 3 记录规则边界：锚点域、精确域等值、只读权限）。
  - receipt `ar_ap_projection_ownership_boundary_guard.json`：`status=passed`、`test_count=17`。
  - 只读 psql：两表存在且 0 行；provider 的 `project_id` 可空，故"无锚点行"可被表达，
    fail-closed 门禁有意义。
- 接线：`verify.ar_ap.projection.ownership_boundary`（`make/runtime_ops.mk`），作为
  `verify.finance_interfund.position.all` 前置；新增一个被引用的目标，不改变 lane coverage
  冻结配额。
- 边界与后续：`sc.ar.ap.report.summary` 有真实 `company_id` 列、动作限财务组、投影为空视图，
  同样缺公司规则——归 Step 3 原生规则覆盖，**本行不改**，已登入 run blockers。
- 未做：受管升级、fixture、业务写。安装态视图／规则仍等于改前状态，新规则的 L3 运行态回读
  待写授权。

### E 段：Step 1 item #7 首家族——`sc.workflow.instance` 公司归属来源

- 对象：`sc.workflow.instance`（其 `sc.workflow.workitem` / `sc.workflow.log` 经
  `instance_id.company_id` 继承同一归属，本次不改）。
- 缺口定性：归属来源（source ownership）而非规则缺口。读隔离此前已由
  `rule_sc_workflow_instance_tenant_business_admin_company` 与 ACL 限定到业务管理员证明；
  真正的"猜公司"发生在创建路径——`create_instance` 取
  `workflow_def.company_id.id or self.env.company.id`，即**用流程模板（配置）或当前环境（调用上下文）
  断定业务事实**。这正是 Step 1 完成判据禁止的形态。
- 归属规则（P1 声明，`models/support/sc_workflow.py`）：
  - 新增模块级纯函数 `resolve_workflow_instance_company(env, model_name, res_id, workflow_def)`：
    归属公司**只**来自业务单据（`model_name` + `res_id` 的公司锚点），以 `sudo` 读取该锚点
    （归属是系统事实，不是调用者需要被授权读取的业务数据）。
  - 无法归属即 fail-closed，不猜：目标模型未注册／名称为空 →
    `WORKFLOW_INSTANCE_UNATTRIBUTED_TARGET`；目标记录不存在或 `res_id` 为空 →
    `WORKFLOW_INSTANCE_TARGET_NOT_FOUND`；目标模型无 `company_id` 字段或该字段为空 →
    `WORKFLOW_INSTANCE_UNATTRIBUTED_TARGET`；流程定义声明了公司且与目标公司不一致 →
    `WORKFLOW_INSTANCE_COMPANY_MISMATCH`（把公司 A 的审批模板套到公司 B 的单据是配置错误，必须拒绝）。
  - `create_instance` 改为 `"company_id": owner_company.id`，不再出现 `env.company` 或
    `workflow_def.company_id` 回退。
  - 新增 `@api.constrains("company_id") _check_company_attribution`：实例必须有归属公司，
    堵住 `company_id IS NULL` 被规则当作"全局可见"的口子。
  - 字段声明补 help：归属公司由业务单据继承，不从流程模板或当前环境推断。
- 证据（`.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/`）：
  - `logs/workflow_instance_ownership_l1.log`：`Ran 13 tests ... OK`
    （10 归属解析用例：正文公司胜出、定义未声明不回填、定义不一致拒绝、记录缺失拒绝、
    `res_id` 为空拒绝、未注册模型拒绝、空模型名拒绝、目标无 `company_id` 字段拒绝、
    目标无归属公司拒绝、锚点经 `sudo` 读取；3 源码断言：`create_instance` 委派解析器且不再引用
    `env.company`/`workflow_def.company_id`、解析器不读调用者环境公司、实例归属为 fail-closed 声明）。
  - receipt `workflow_instance_ownership_boundary_guard.json`：`status=passed`、`test_count=13`。
  - 读数边界证据（既有，未重跑）：
    `tests/test_role_regression_minimal.py::test_workflow_runtime_is_scoped_by_allowed_company_without_count_leak`
    已证明业务管理员只看到本允许公司的实例且不泄漏计数。
- 测试装载安全性：新测试优先真实导入 `odoo.addons.smart_construction_core...`；仅在无 Odoo 的
  inner loop 才临时注入 stub，并在 `finally` 中恢复 `sys.modules`，不覆写真实 `odoo` 模块
  （现有 `test_ar_ap_projection_relation_lifecycle.py` 的同名 stub 是无条件覆写，本次不模仿）。
- 接线：新增 `verify.workflow_instance.ownership_boundary`（`make/ci.mk`），作为
  `verify.workflow_contract.backend` 前置；作为被引用目标登记 run check
  `workflow_instance_ownership_boundary_guard`，不改变 lane coverage 冻结配额。
- 静态门禁通过：`make verify.verification.lane_coverage`、`make verify.guard.registry`
  （1437 scripts，198/198 unwired dispositioned）、`make ci.local.iteration`（`L1_only`，dirty）。
- 分类台账差量：20 项归属待定 → 19 项；`sc.workflow.instance` 转入
  `native_classification.resolved_source_ownership`（含锚点、声明、守卫与限制）。
- 未做／限制：受管升级、fixture、业务写均未执行；未做安装态 ORM 回读，`create_instance` 是
  legacy 运行时入口（`LEGACY_WORKFLOW_RUNTIME_*` 门禁，仓库内无调用方），本次以解析器级非零测试
  为证据，运行态回读待写授权。`sc.workflow.def` 仍只有 `smart_core.group_smart_core_admin` 的
  写 ACL 且无规则（平台配置，非客户业务数据），本行不改。

### E 段附带发现（下一家族，已登 run blockers）

分类 19 项剩余模型时定位到一个**无归属事实族**：`sc.dashboard.cockpit.fact`、`sc.workbench.item`
的 ACL 是 `base.group_user` 全 1111 且**零 ir.rule**；共享抽象 `sc.business.fact.mixin`
（另被 `sc.document.admin.document`、`sc.office.admin.document` 及 hr 文档模型继承）**完全没有公司字段**，
因此公司隔离在该族无法表达。归属必须落到 `project_id`／公司声明后才能继续保留写能力。
该族需要 schema 变更 + 受管升级，属下一片切片，本次只登记事实，未改代码。

### F 段：价格族公司归属回到事实层单一来源（Step 1 第 7 项）

- 目标：`sc.labor.price`／`sc.equipment.price`／`sc.subcontract.price` 三个 P1 价格库的公司归属收口。
- 事实：三模型此前无任何公司字段；规则只有 `rule_sc_internal_*`（仅 creator／项目负责人／项目关注者，
  **无公司条款**）与 `rule_sc_super_admin_*`（`[(1,'=',1)]`）；ACL 仅
  `group_sc_internal_user`(1110)／`group_sc_super_admin`(1111)。
- 裁定（架构边界）：**后端必须回到事实层数据单一来源**。价格行的公司不是第二个可独立编辑的事实，
  它就是所属项目的公司；独立再存一份（哪怕带 `default=self.env.company`）等于制造第二来源与漂移口。
- 实现：三模型统一改为
  `company_id = fields.Many2one("res.company", related="project_id.company_id", store=True, readonly=True, index=True)`，
  与既有 `ScSubcontractPlan`（`subcontract_management.py:39`）以及材料样板 `sc.material.price`
  （派生自 `material_catalog_id.company_id`）同一范式；仓库内同型派生声明约 30 处，非新机制。
- 本切片内先前的**重复冗长逻辑**已移除：一是三份独立的
  `company_id = fields.Many2one(..., required=True, default=lambda self: self.env.company, index=True, ondelete="restrict")`
  字段块，二是三条 `@api.constrains("company_id","project_id") _check_project_company`。后者在派生写法下
  是恒真约束（拿项目公司比自己），属重复校验，无信息量。
- 规则：`rule_sc_internal_{labor,equipment,subcontract}_price` 的 `domain_force` 追加公司条款
  `('|', ('company_id','=',False), ('company_id','in',company_ids))` 并与既有项目成员条款 `AND`；
  `perm_read/write/create/unlink`、`groups`、group-scoped 声明不变；`rule_sc_super_admin_*` 仍
  `[(1,'=',1)]`。域形状与材料样板 `rule_sc_material_*_price` 一致。
- 边界语义：无项目的价格行没有公司事实，派生公司为 `False`，规则按“全局默认价”继续可见——与改动前
  行为一致，不会因派生而丢可见性，也不会凭空归到调用者公司。
- 测试与负向控制：`addons/smart_construction_core/tests/test_price_family_company_ownership.py`
  10 用例（派生声明唯一、无独立默认/可选写、无重复约束、规则公司条款、项目成员范围、权限、
  group-scoped、super_admin ALL、材料样板未回退、材料派生范式仍在）。负向控制：把某个模型改回独立
  `company_id` 声明 → 2 用例 FAIL；还原 → 10 用例 OK。
- 接线：新增 `verify.sc_price.company_ownership_boundary`（`make/ci.mk`），作为
  `verify.contract.architecture.suite` 依赖；该 suite 同时被 `ci.local.quick.run` 与
  `ci.professional.backend.shard-verify` 两个闸锚点可达，因此本地/远端无 lane 分叉。
- 同批真实红灯修复（非本切片业务能力，属边界治理）：本分支 `a74a5c9f` 把
  `models/support/product_policy_sync.py` 从写 `ui.menu.config.policy` 改为投影到 P1 产品事实模型
  `sc.product.policy` 后，`scripts/verify/backend_contract_boundary_guard.py` 的
  `ALLOWED_LOWCODING_POLICY_RUNTIME_WRITERS` 仍登记该文件，导致
  `test_backend_contract_boundary_guard.py` 断言 `lowcoding_policy_writer_count == 5` 失败（实测 4）。
  已退役该白名单条目并同步期望值（lowcoding 5→4、writer_boundary 12→11、writer_file 8→7）与
  `docs/architecture/backend_contract_boundaries.md`；未改扫描/判定逻辑，未回退产品迁移。
- 输入清单修正：`schema_digest_authority` 的 inputs 补
  `scripts/verify/backend_contract_boundary_guard.py` 与 `addons/smart_core/utils/backend_contract_boundaries.py`
  （前者被测试 import、后者被前者读取，属被遗漏的测试/工具依赖）。
- 证据（`.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/`）：
  - `logs/sc_price_company_ownership_boundary.log`：`Ran 10 tests ... OK`；receipt
    `sc_price_company_ownership_boundary_guard.json`（`status=passed`、`test_count=10`）。
  - `logs/backend_contract_lifecycle_authority.log`：四个套件 `12+10+11+13=46` 用例 `OK`；receipt
    `schema_digest_authority.json`（`status=passed`、`test_count=46`）。
- 静态门禁：`make verify.sc_price.company_ownership_boundary`（10 OK）、
  `make audit.verification.lane_coverage.check` PASS、`make verify.guard.registry` AUDIT PASS、
  `make ci.local.iteration` PASS（`L1_only`，dirty）。
- 分类台账差量：`unresolved_source_ownership` 19 → 16；三个价格模型进入
  `native_classification.resolved_source_ownership`（锚点＝`project_id.company_id` 派生 +
  公司域规则，guard＝`verify.sc_price.company_ownership_boundary`）。
- 未做／限制：无受管升级、无 fixture、无业务写；`sc_dev_demo` 仍是改动前的模型与规则安装态，
  派生列与新规则域的 L3 运行态回读待写授权。`sc.material.catalog`／`sc.material.price` 仍留在
  `unresolved_models`，等其 group-vs-ACL 覆盖证明后再收。
- 附带发现（已登 run blockers，非本批阻塞）：`make verify.backend_business_fact.model_standard`
  当前因文档计数漂移而 FAIL（`backend_business_model_audit_findings_v1.md` 记 372/0，实测 378/1）；
  该 target 是 zero-reference、不可达任何闸锚点的 lane 条目。

### G 段：数据隔离公司上限回到声明派生单一来源（`DATA-SCOPE-CEILING-01`）

- 目标：把 `DATA-SCOPE-CEILING-01` 的 26 个 deferred P1 业务模型补上公司上限，同时不让 99 个 enforced
  模型继续靠 99 条近乎重复的手写 `ir.rule` 维持——即“数据隔离不是每个模型添加隔离维度”，而是
  **一个声明派生一条统一上限**。
- 事实（改动前）：99 条 enforced 公司域规则全部内联在
  `addons/smart_construction_core/security/sc_record_rules.xml`（本段删除其第 3306–4201 行，共 892 行
  = 一段注释 + 99 条 `rule_sc_data_scope_*`）；26 个 deferred 模型只有 capability/project 范围的
  groups 规则（域形如 `(1,'=',1)` 或项目成员谓词），没有任何公司条款，因此 `group` 并集不设上限，
  经理级 group 可读他公司行。
- 裁定（事实层单一来源）：唯一事实源是 `scripts/verify/data_scope_declarations.json`。生成器
  `scripts/verify/sc_data_scope_ceiling_generate.py` 从该声明渲染
  `addons/smart_construction_core/security/sc_data_scope_ceiling_generated.xml`（125 条 =
  99 enforced + 26 deferred）；`sc_record_rules.xml` 的手写块删除，只留 4 行注释指向生成物与生成器。
  跨模块模型按引用前缀区分：`ui.business.config.contract` 归 `smart_core` 定义，生成记录仍落在
  `smart_construction_core`，`model_id` 用 `smart_core.model_ui_business_config_contract` 引用——
  该文件本已跨模块引用 `smart_core`（`depends` 第 20 行），非新机制。
- 等价性证明：删除前把生成物与旧手写块逐条比对，99 条 enforced 记录 **byte-identical**（内容差异 0），
  另加 26 条 deferred 新增，未改动任何已生效域的形状或 `perm_*`。
- 守卫语义升级：`scripts/verify/sc_data_scope_rule_coverage_guard.py` 现在对 enforced **和** deferred
  都要求“存在一条全局规则且其域约束声明的 anchor”；`deferred` 记录的是交付顺序，不是隔离缺失。
  因此删除生成文件会 fail-closed——实测移除
  `security/sc_data_scope_ceiling_generated.xml` → 20+ 条 FAIL、exit=120；还原 → exit=0、文件一致。
- 漂移闸：`python3 scripts/verify/sc_data_scope_ceiling_generate.py --check` 重新渲染并与已提交文件
  比对，不一致即 FAIL。接为 `make verify.sc_data_scope.ceiling.check`，并作为
  `verify.sc_data_scope.rule_coverage` 的前置；`verify.sc_data_scope.rule_coverage` 同时被
  `ci.local.quick.run` 与 `ci.professional.backend.shard-verify` 两个闸锚点可达，故本地/远端无 lane
  分叉。生成入口为 `make verify.sc_data_scope.ceiling.sync`（编辑声明后重新生成）。
- 测试：guard 用例 21 → **23**（新增：deferred 缺规则 FAIL、deferred 有规则 PASS、deferred 只有
  group 规则 FAIL）；生成器用例 **7**（声明与已提交记录集一致、enforced/deferred 各渲染一条、anchor
  去重优先 enforced、跨模块前缀、全局且无 `groups`、无归属模型 fail、根外路径打印）。
- 证据（`.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/logs/`）：
  `data_scope_coverage_batch2.log`（23 tests，`uncovered=0`）、
  `arch_suite_data_scope_ceiling.log`（30 个套件、合计 **335** tests、`exit=0`）。
- 未做／限制：无受管升级、无 DB 写；`sc_dev_demo` 仍是改动前的模型与规则安装态，新记录集的 L3
  激活回读（`local.dev.data_scope.inventory` 的 `installed_company_scoped_rule_count`）待写授权。

#### G 段续：L3 受管激活与权威回读（2026-10-14，所有者授权）

- 授权对象：`make local.dev.snapshot` → `make local.dev.upgrade MODULE=smart_construction_core` →
  `make local.dev.data_scope.inventory`。环境身份：`project=sc-local-dev`、`db=sc_dev_demo`（注册的
  persistent demo-backing profile），写入前 HEAD `e84b20e1`、工作区 clean。
- 回滚保障：`artifacts/local-dev/snapshots/20261013T190439Z/`（`sc_dev_demo.dump` +
  `sc_dev_demo-filestore.tar.gz`），升级前生成。
- 激活前事实（只读）：已安装的 `SC Data Scope - … by allowed companies` 规则 **0 / 125**。即 99 条
  enforced 与 26 条 deferred 此前都只是源码声明，从未在 `sc_dev_demo` 激活过；26 个 deferred 模型当时
  只有项目/能力范围的 groups 规则（`installed_company_scoped_rule_count` 是命中 `project_id` token 的
  粗口径，不等于存在公司条款）。
- 升级：`make local.dev.upgrade` `exit=0`，日志确认
  `loading smart_construction_core/security/sc_data_scope_ceiling_generated.xml`；升级后自带
  `local.dev.verify_authority` PASS（`finance_xmlid/membership/company_currency=CNY/sale_tax_9`），
  `make local.dev.health` PASS。
- 激活后权威回读：已安装同名规则 **125 / 125**，与生成物**逐名相等**（`missing=[]`、`extra=[]`），
  其中 enforced **99/99**、deferred **26/26** 各自带上了
  `SC Data Scope - <model> by allowed companies`。
- 证据链：源码守卫证明「全局 + 域约束声明 anchor」（23 用例）→ 漂移闸证明「已提交记录集＝声明」
  （7 用例）→ 激活前回读证明「确实待激活」→ 升级日志证明「加载了该文件」→ 激活后回读证明
  「安装集与源集一致」。因升级前该 xmlid 集合为空，不存在残留 `groups` 需要覆盖。
- 限制：本次回读按「规则名 × 模型」证明安装集与生成集一致，未逐条再断言安装态的 `groups`/`domain`；
  后者由源码守卫与「逐字加载该文件」共同覆盖。
- 证据日志（`.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/logs/`）：`l3_snapshot.log`、
  `l3_upgrade.log`、`data_scope_inventory_before_ceiling.log`、`l3_data_scope_inventory_after.log`。
- 状态边界：本批为**批次验收完成**（源码 + L3 激活回读）；**未**主线集成、**未**部署、**未**产品交付，
  push/merge 仍未授权。

### H 段：全量后端事实源复核与盲区收口（2026-10-14，所有者要求“复核全量后端审核有无遗漏”）

- 复核方式：不做叙述性审计，只用可复现扫描回答“后端是否还有多头事实被漏掉”。六个维度：
  模型身份、公司范围 universe、币种/金额默认、security XML 记录、声明载体接线、lane 面与生成物装载。
- **发现（真实遗漏，已收口）**：覆盖 universe 用 `_name = "字面量"` 正则推导，
  `addons/smart_core/model/ui_menu_config_policy.py` 的 `_name = MENU_CONFIG_POLICY_MODEL`（导入常量）
  因此**逃出 universe**：它有独立 `company_id`（`default=self.env.company`）、ACL 仅
  `smart_core.group_smart_core_business_config_admin`、零 ir.rule，却既不在声明台账也不在任何桶里；
  旧口径因此报出 `universe=137 / uncovered=0` 的**假绿**。
- 收口：
  - `scripts/verify/sc_data_scope_rule_coverage_guard.py` 增加模块常量表解析
    （`model_name_constants` / `resolve_model_name`），`_name` 为常量时同样得到真实身份；
    任何**声明了 `_name` 却无法解析**的类一律 fail-closed（`unresolved_model_names`），
    不再“解析不到就静默跳过”。`defined_models` 同步按同一口径归属模块。
  - `scripts/verify/fact_source_coverage_guard.py` 改用同一身份解析，
    公司范围与金额事实的 universe 不会在“模型身份”上分叉。
  - `ui.menu.config.policy` 按既有 `ui.*` 范式声明为 `enforced`（anchor `company_id`，class `root`），
    生成器产出 `rule_sc_data_scope_ui_menu_config_policy`（跨模块 ref `smart_core.model_ui_menu_config_policy`）。
  - 新增负向控制 4 条：常量命名模型进入 universe 且未声明即 FAIL；声明后 PASS；
    `_name` 不可解析即停机；常量命名模型的金额事实不得逃出标准币种声明。
- 收口后事实：`universe=138`、`enforced=124`（universe 内 75）、`exempt=33`（12）、`deferred=26`（26）、
  `source_bounded=25`、`uncovered=[]`、`unresolved_model_names=[]`；生成上限 **150** 条
  （124 enforced + 26 deferred），manifest 装载该文件。
- 其余维度结论（未发现遗漏）：多行安全的独立扫描复现出与守卫完全一致的 universe；
  272 处 `currency_id`/`company_id` 赋值无第三种默认表达式（无 `env.user.company_id.currency_id`、
  无 helper 默认）；`addons/*/security/*.xml` 495 条 rule/access 记录 **0 重名 xmlid、0 重名规则**；
  三个声明文件均有消费者、Make 目标与 lane 锚点；`verification_lane_coverage --check` PASS
  （无新增零引用/仅远端面）；生成物由 `__manifest__.py` 装载，不是孤儿文件。
- 登记未决（不属本轮缺陷，禁扩大范围）：①46 个模型同时声明 `project_id` 与非派生 `company_id`
  （11 个 `env.company` 默认、35 个独立），均已进入公司范围台账、不存在静默无界，
  但“是否必须由项目派生公司”属产品语义裁定（与价格族同类），不可机械判定；
  ②`verify.backend_business_fact.model_standard` 仍因文档漂移 FAIL，且是零引用 lane 项，未在本轮扩大处理。
- 证据（`.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/logs/`）：
  `backend_fact_source_closure_guards.log`（31 + 13 tests OK，uncovered=[]，failures=[]）、
  `arch_suite_backend_fact_source.log`（31 套件 / **356** tests / exit=0）。
- L3 状态边界（必须明说）：上次激活回读只证明**当时 125 条**逐名相等；当前提交集为 **150 条**，
  因此激活回读对本集合**已过期**，新增的 25 条目前只有源码与守卫证明。

### I 段：币种/金额事实源第二层盲区收口（2026-10-14，独立只读复核后的第二轮）

- 触发：H 段只证明“字段默认表达式”这一层；独立只读复核指出金额事实还有第二层写入面。
  复核结论经我独立取证后分为四类**真实遗漏（全部收口）**与两类**已核实非遗漏**。
- **遗漏 1——继承事实（5 个模型）**：`sc.business.fact.mixin` 声明
  `currency_id = default=self.env.company.currency_id`，被
  `sc.dashboard.cockpit.fact`、`sc.workbench.item`、`sc.document.admin.document`、
  `sc.office.admin.document`、`sc.hr.payroll.document` 通过 `_inherit` 继承，这 5 个模型自身没有
  `currency_id` 字段定义，任何“扫描字段默认”的口径都看不到它们的金额事实来源。
- **遗漏 2——无公司列事实（5 个模型）**：`project.settlement`、`sc.business.fact.mixin`、
  `sc.material.purchase.request.line`、`sc.material.rfq.line` 默认调用方公司币种且**没有任何
  `company_id` 列**——记录根本没有“自己的公司”来拥有金额事实；`sc.treasury.ledger` 的
  `company_id` 是只读（由投影写入），因此行公司可与调用方不同，属同一类。
- **遗漏 3——字段默认以外的写入点（6 处）**：`<record>.currency_id = ...` 在字段默认之后再次覆盖
  金额事实，字段默认口径完全看不到。6 处全部登记并绑定来源关系：
  `construction.contract._onchange_original_contract_id`、`sc.output.invoice.adjustment._sync_original_invoice_snapshot`、
  `sc.receipt.income._onchange_payment_request_id`、`sc.settlement.order._onchange_contract_id_fill_header`
  与 `_onchange_general_contract_id`（复制所属单据/台账，单一来源）；
  唯一**未决**是 `sc.norm.catalog._onchange_region_currency`：它复制
  `region_id.country_id.currency_id`（国家事实，非公司事实），境外区域可覆盖租户标准币种，
  以 `CURRENCY-OWNER-ALIGNMENT-01` 登记待裁定。
- **遗漏 4——扩展类字段重定义（1 处，且同一盲区同时存在于公司范围守卫）**：只有 `_inherit`、没有
  `_name` 的扩展类可以重定义 `company_id`/`currency_id`。`sc.labor.usage` 在
  `labor_product_extension.py` 重定义 `company_id`（仅加“所属公司”标签，关系不变）。更关键的是
  **公司范围守卫 `company_field_models` 同样只看有 `_name` 的类**：若某扩展类给一个自身没有
  `company_id` 的模型补上公司列，该模型会直接逃出 universe。两个守卫现已共用同一继承解析
  （`scope_guard.inherit_names` / `target_models`，不再各写一份），并新增 fail-closed：
  一个声明了 `company_id` 却用无法解析表达式写 `_inherit` 的类必须停机。
- **已核实非遗漏**：①`construction.contract`、`sc.general.contract`、`sc.office.asset`、
  `sc.settlement.order` 的 `company_id` 与 `currency_id` 同源于调用方公司，单一来源，刻意不登记；
  ②`res.company._sc_ensure_cny_currency` 不是遗漏而是**被遗漏登记的事实**：它是“公司币种＝租户标准币种”
  这一前提的权威实现，现已声明并由守卫校验（方法存在、仍引用 `base.CNY`），
  标准币种声明不再建立在未登记假设上。
- **登记但不设闸**：产品模块内另有 38 处 `vals` 字典式 `currency_id` 写入，经分类均为“所属单据派生”
  或“载荷复制”，目标不可静态判定，且其中非标准币种硬编码已由既有引用检查覆盖，故只做盘点不新增闸。
- 收口后事实：`currency_models=133`、`standard=12`、`caller_context=37`（其中 5 个为继承、5 个无公司列）、
  `currency_write_paths=6`、`company_field_overrides=1`、`company_currency_authority=verified`；
  公司范围 `universe=138`、`uncovered=[]`、生成上限 **150** 条不变（本轮未新增 enforced 模型）。
- 新增负向控制：金额守卫 13→**20** 用例（继承、无公司列、写入点、缺来源/缺理由、扩展类重定义、
  权威缺失/方法不存在）；公司范围守卫 31→**33** 用例（扩展类公司列进入 universe、
  `_inherit` 不可解析即停机）。正反两向都证明“缺席不是豁免”。
- 证据（`.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/logs/`）：
  `backend_fact_source_closure_guards_2.log`（ceiling 7 + fact_source 20 + scope 33 用例 OK，
  failures=[]）、`arch_suite_backend_fact_source_2.log`（exit=0，**366** 用例全绿，套件标记集与上一轮完全一致；
  其中本轮改动的两个守卫贡献 33 + 20 条）。
- 状态边界：仍为**批次验收完成（源码 + 守卫）**；L3 激活回读对 150 条集**仍过期**，
  未主线集成、未部署、未产品交付。

### J 段：主线定时 CI 失败收口（2026-10-14，所有者“定时 CI 有失败先排查一并收口”）

- 触发：`main` 最近一次定时运行（`schedule`，2026-10-13T00:52Z，head `2e2951ea81cd`，
  已是 `origin/main` 祖先）三车道同时红：`public_guard`（38329383719）、
  `professional_quality_gate`（38329459061）、`release_candidate_gate`（38329628180）。
  上一次同车道定时运行（10-11T22:10Z）是绿的，10-13 之前连续五次定时全绿。
- **根因（已用 CI 原始日志确证，不靠推断）**：`security.trusted_scan_group` 报
  `members=3 jobs=2 worker_budget_per_member=1 status=failed`，两个成员（`security.secrets.scan`、
  `security.personal_data_scan`）均以 `rc=2` 失败于同一断言——
  `scripts/ci/test_parallel_scan.py::ResolveWorkersTests::test_item_count_bounds_the_pool`
  `AssertionError: 1 != 2`。链路：`scripts/ci/trusted_scan_group.py:178` 把
  `SC_TRUSTED_SCAN_GROUP_JOBS` 写入自身环境，`run_members` 用它启动成员 make 进程，
  该变量经成员目标的前置依赖透传到 `security.parallel_scan.unit`；GitHub runner 为 4 vCPU，
  `machine_budget()` 得 `4 - CPU_HEADROOM(2) = 2`，于是 `resolve_workers(2)` 返回 `2 // 2 = 1`。
- **实现无缺陷，缺陷在单测**：组已持有 `jobs` 并发，成员按 `budget // jobs` 共享一台机器是
  `parallel_scan` 的既定语义（模块 docstring 与 `test_group_concurrency_divides_one_machine_budget`
  均已声明）。`test_item_count_bounds_the_pool` 要验的是“worker 数被 item 数上界约束”，
  却把该上界交给了调用方机器预算，因此只在 CI 的机器规模下暴露。
- **修复（`17b48549`）**：与同文件既有用例一致，显式声明 `cpu=18, memory=64GiB` 并清空
  `SC_SCAN_WORKERS`/`SC_SCAN_SERIAL`/`SC_TRUSTED_SCAN_GROUP_JOBS`；顺带隔离
  `test_invalid_group_concurrency_is_rejected`（环境存在 `SC_SCAN_WORKERS` 时会提前返回，
  永远走不到 `GROUP_JOBS_ENV` 校验，属同类隐患）。断言扩为 2/3/1000 三档，同时锁定
  “item 上界”与“机器预算不无界”两件事。
- **`release_candidate_gate` 为纯级联，无独立缺陷**：其失败步骤是 `test "$result" = success`
  对上游 `public_guard` 结果断言，日志显示 `result="failure"` 即为全部原因，未执行任何产品检查。
  两个真失败点（`public_guard`、`professional_quality_gate`）日志尾部同为
  `[trusted_scan_group] ... status=failed`，即同一根因，不是两个独立缺陷。
- **修复前/后 A/B（可复现证据）**：harness 以“环境预算=2 + `SC_TRUSTED_SCAN_GROUP_JOBS=2`”
  模拟 runner，对 `HEAD` 版本精确复现 `AssertionError: 1 != 2`（与 CI 日志逐字一致），
  对修复版本 7/7 通过。
- **车道内回归证明**：`make security.trusted_scan.group` 本地 `status=passed`，
  三个成员 `rc=0`（41.3s / 44.7s / 79.7s，`scan_workers=5`），且 `security.parallel_scan.unit`
  正是在 `SC_TRUSTED_SCAN_GROUP_JOBS=3` 已导出的组环境内 18 tests OK——即最初触发失败的
  环境条件本身已被覆盖。依赖该单测的其余 unit 同时复跑：`security.online_capture.unit` 13 tests、
  `security.personal_data.unit` 9 tests、`security.trusted_scan_group.unit` 16 tests、
  `verify.repository.clean_history.unit` 37 tests，全部非零通过。
- **观察（不改行为，登记待议）**：CI runner 4 vCPU 下 `resolve_jobs` 取 2、`machine_budget` 取 2，
  于是每成员 1 worker——PR #650 引入的并行机制在 GitHub runner 上收益为 0，只体现为组间并发。
  这是 `CPU_HEADROOM=2` 在 4 vCPU 机器上的保守取舍，属性能议题而非正确性缺陷，本轮不改动，
  避免过订。
- 影响面：仅测试隔离，未触碰 `parallel_scan`/`trusted_scan_group` 实现，扫描覆盖面不变
  （`scanned_blobs=24441`，`confirmed_matches=0`，`sensitive_values_recorded=false`）。
- 状态边界：该 CI 失败已**在源码层收口并本地验证**；远端车道只有在候选经受保护 PR 合并后
  才会重新评估，因此当前仍**未主线集成**，不得报 `main` 已转绿。

### K 段：后端唯一事实全量复核与收口（2026-10-14，所有者“必须让后端彻底统一唯一事实输入的目标彻底落实……彻底收口后再集成主线”）

- 触发：所有者要求把“后端唯一事实输入”在集成主线前彻底收口，并安排一次**全量后端审核**查漏。
  本轮不是新增扫描器，而是用既有声明式守卫对既有事实做一次全量只读复算，把复算出的分叉就地收口。
- 复算口径：`data_scope_declarations.json` / `fact_source_declarations.json` 两个已登记声明，
  分别由 `verify.sc_data_scope.rule_coverage`、`verify.fact_source.coverage` 消费；只读源为
  `config/tenant/module_sets.v1.json` 声明的 10 个产品模块。

#### K1：生成上限与手写规则“AND 取严”的 7 处纯冗余（生成上限 150 → 143）

- 复核发现：有 7 个模型同时存在“生成的数据范围上限规则”和“手写全局规则”，ORM 对同一模型的多条
  `ir.rule` 是 AND 语义。逐条比对手写域与生成域后确认：生成记录**没有表达手写规则之外的任何事实**，
  只是叠加了一层不减权限的同一约束，因此属于“同一事实的两个载体”。
  - 域完全相同（纯冗余）：`project.boq.analysis.norm.line`
    （`rule_sc_data_scope_project_boq_analysis_norm_line` vs `rule_sc_boq_analysis_norm_allowed_company`）、
    `project.boq.analysis.resource.line`
    （`rule_sc_data_scope_project_boq_analysis_resource_line` vs `rule_sc_boq_analysis_resource_allowed_company`）。
  - 生成域更宽（多一条 `=False`）、手写域更严：`sc.ar.ap.company.summary`
    （`rule_sc_data_scope_sc_ar_ap_company_summary` vs `rule_sc_ar_ap_company_summary_company`）、
    `sc.ar.ap.project.summary`
    （`rule_sc_data_scope_sc_ar_ap_project_summary` vs `rule_sc_ar_ap_project_summary_company`）。
  - 手写域更窄（带 `user._sc_data_company_ids()`）：`sc.hr.payroll.document`
    （`rule_sc_data_scope_sc_hr_payroll_document` vs `rule_sc_hr_payroll_document_company`）、
    `sc.hr.salary.payment`（`rule_sc_hr_salary_payment_company`）、
    `sc.salary.summary`（`rule_sc_salary_summary_company`）。
- 收口：7 个模型从 `enforced` 迁到 `source_bounded`，每条声明带
  `model/anchor/rule/file/reason`，reason 写明“生成记录未表达额外事实，AND 后冗余”。
  声明事实变为 `enforced=117`、`source_bounded=32`（其余 `exempt=33`、`deferred=26` 不变）。
- 生成物：`make verify.sc_data_scope.ceiling.sync` 后 `SC_DATA_SCOPE_CEILING=written rules=143`
  （原 150），即上限规则只保留真正新增事实的那些；被移除的 63 行只来自上述 7 条。
- 边界：手写规则保持原样，仍是这 7 个模型上唯一生效的范围事实，不存在“先删后补”的窗口。

#### K2：守卫核算不对称修正（`source_bounded` 不再被“必须在 universe 内”误判）

- 复核发现：`sc_data_scope_rule_coverage_guard.py` 对 `source_bounded` 沿用 `enforced` 的
  “模型必须落在 universe 内”硬失败，但 `source_bounded` 是“该模型的范围事实来自关系锚点而非自有
  `company_id` 列”，其模型本就可以没有自有公司列、因而不在 universe 内。关系锚定的 4 个模型
  （`project.boq.analysis.norm.line`、`project.boq.analysis.resource.line`、
  `sc.ar.ap.company.summary`、`sc.ar.ap.project.summary`）因此会被误报。
- 收口：删除该硬失败；核算改用新增的 `source_bounded_in_universe`，返回值补
  `source_bounded_in_universe=28`、`source_bounded_out_of_universe=[4 个关系锚定模型]`。
  “必须解析到真实产品模块 + 真实全局规则”的校验保留，幽灵模型仍然 fail-closed。
- 单测：`test_sc_data_scope_rule_coverage_guard.py` 的仓库断言改用
  `source_bounded_in_universe`，并新增 `test_source_bounded_relation_anchored_model_stays_explicit`
  （关系锚定模型 + `WIZARD_EXEMPT`：`universe=2`、`source_bounded_in_universe=0`、
  `source_bounded_count=1`）与 `test_source_bounded_unknown_model_still_fails_closed`（幽灵模型仍 FAIL）。

#### K3：业务编号“第二权威”登记（`BUSINESS-NUMBER-AUTHORITY-01`）

- 复核发现：业务编号这条事实此前只在“读”的一侧被看，发布侧与兜底侧从未进入同一张表，三条扫描
  互相漂移：
  - **读**：产品模块内 53 个**字面** `next_by_code` 码 + 1 个动态码
    （`support/contract_center.py::create` 的 `seq_code`），分布 32 个 reader 文件（全在 `smart_construction_core`）。
  - **发布**：产品数据 `ir.sequence` 码 53 条（`smart_construction_core/data/sequence.xml`）。
  - **不一致**：`sc.contract.change`、`sc.labor.deduction`、`sc.site.variation` 被读取却**无任何产品数据发布**
    （读永远落到声明标签）；`construction.contract.expense`、`construction.contract.income` 经动态码实际被读，
    `sc.project.document` 已发布但无任何产品代码读取（疑似孤立发布记录）。
  - **第二权威**：7 个 (file, function) 在序列缺失时会把编号落成第二个值——
    `business_menu_facts.py::_next_document_no`（`or "NEW"` 派生 token）、
    `general_contract.py::create`（`contract_no` 落到 `name`）、
    `hr_payroll_document.py::create`（`SALPAY-` 落到 `record.id`）、
    `material_plan.py::action_submit`（落到本字段声明标签，良性）、
    `project_core.py::create`（`project_code` 落到时间戳+uuid，且有 `unique` 约束）、
    `settlement_order.py::create`（落到本字段声明标签，良性）、
    `contract_center.py::create`（子类型序列 → `construction.contract` → 字面量，链式兜底）。
    其余约 50 处是“`name` 字段 + 本字段声明标签兜底”，属良性类别 `name_label_fallback` /
    `chained_sequence_then_label`。
- 收口：`scripts/verify/fact_source_coverage_guard.py` 新增 `sequence_codes_published`、
  `sequence_read_sites`、`business_number_authority`，接入 `check()`；声明写入
  `fact_source_declarations.json.business_number_authority`：32 个 reader 文件（逐文件列码）、
  6 条例外码（3 读未发布 + 3 发布未读）、1 条动态读取、7 个兜底落点（各自带 class，
  非良性类附 `BUSINESS-NUMBER-AUTHORITY-01` 与 reason）。
- **`codes` 语义收敛为例外登记**：reader 文件已经逐文件声明了“读哪些码”，若再把“发布且被读”的 50
  条码复制进 `codes`，声明层就多出一个必须同步的第二处事实源。因此 `codes` 只登记
  `(已发布 - 已读) ∪ (已读 - 已发布)` 两类例外，各带 reason；同时新增“登记为例外但源里已无
  publication/read 分叉”的失败分支，使例外一旦被修复就立刻失效，不再静默残留。

#### K4：证据与状态边界

- 证据（`.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/logs/`，本段新增）：
  `make verify.fact_source.coverage` → **52** 用例 OK（上一轮 37，新增 15 条业务编号用例），
  `status=passed`、`business_number_authority.reader_files=32`、`codes=53`、`published_codes=53`、
  `unpublished_codes` 3 条、`unread_published_codes` 3 条、`dynamic_reads` 1 条、`second_value_sites` 7 条；
  `make verify.sc_data_scope.rule_coverage` → **37** 用例 OK、`uncovered=[]`、`universe=138`、
  `enforced=117`、`source_bounded=32`（`in_universe=28`）；`make verify.sc_data_scope.ceiling.sync`
  → `written rules=143`；`make verify.contract.architecture.suite` → rc=0（套件标记与上一轮一致，
  Node syntax 384 files）。
- 状态边界：仍为**批次验收完成（源码 + 守卫 + 定向测试层）**。L3 激活回读的集合由 150 条变为 **143** 条，
  旧 150/125 回读全部过期；未主线集成、未部署、未产品交付。

### L 段：布局列数回退缺陷结项与交付冻结解除（2026-10-14）

- 触发：`make ci.delivery.freeze.prepare` 在 `verify.frontend.contract_basis.enforce` 处
  fail-closed，理由为 `open_defects=1`——台账仍挂着 `CD-20261013-LAYOUT-COLUMNS-FALLBACK`。
  同一台账还使 `verify.frontend.contract_basis.unit` 的
  `test_repository_ledger_has_no_open_defect` 持续失败，交付车道因此整体不可冻结。
- 复核（先证事实再改登记，不靠推断）：该条目描述的两个符号在当前源码**已不存在**——
  `frontend/` 下已无 `normalizeColumns` / `descriptionColumns` 实现（`git log -S` 显示
  `normalizeColumns` 的移除发生在 `265963f6`，早于登记该条目的 `9dfe9568`；
  仅验收脚本 `frontend/apps/web/scripts/low_code_form_layout_runtime_acceptance.mjs`
  内有同名局部函数，属验证工具而非渲染路径）。逐条核对收口条件：
  - **声明层发布显式列数**：`unified_page_contract_v2_assembler.py` 的
    `declared_container_columns` / `declare_container_columns` 只为“自带网格声明”的容器
    写入 `columns`，其余节点不发布。
  - **解码器不再造跨度**：`app/contracts/v2/schema.ts` 改为
    `requiredIntegerInRange(raw, 'span', path, issues, 24)`，缺失或非法进入 decode issue；
    `columns` 必须为 1..24 且整除 24，否则同样进入 issue。
  - **渲染器缺失即停机**：`components/template/layoutSpan.ts` 的 `isDeclaredLayoutSpan` /
    `requireDeclaredLayoutSpan` / `requireDeclaredLayoutColumns` 取代原默认与夹取，
    布尔或字符串跨度不再被当成合法宽度（注释明确记录 “`true` used to become a one-unit field”）。
  - **24 轨机制保留**：`layoutGridUnits()=24`，由 `frontend_form_canvas_wide_grid_guard`
    与 `frontend_form_canvas_layout_contract_test` 锁定。
  - 窄屏单列由前端视口断点表达，但断点分支前仍先调用
    `requireDeclaredLayoutColumns(props.columns)`，契约列数缺失照样停机。
- 取证（`.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/logs/`）：
  `verify_frontend_form_canvas_layout_guard.log`（`PASS cases=80 declared=7 undeclared=12`、
  wide-grid 22 tests OK）、`verify_frontend_native_form_structure_responsibility_unit.log`
  （`PASS cases=18`）、`verify_frontend_contract_basis_unit.log`（**15 tests OK**）、
  `verify_frontend_contract_basis_enforce.log`（`PASS bindings=9 exemptions=5 logic_sites=3
  open_defects=0`）。
- 收口：条目从 `openContractDefects` 结项到 `closedContractDefects`（保留原始 missing /
  owner / closureCondition，补 resolution / reVerified / closureEvidence）。
  结项既有事实依据、也有守卫依据，不是为了让门变绿而撤登记。
- 结果：`verify.frontend.contract_basis.enforce` 与台账单测恢复通过；
  `make ci.delivery.freeze.prepare` **rc=0**
  （`[ci.delivery.freeze.prepare] PASS candidate=unfrozen`，
  `[ci.generated_evidence.preflight] PASS all content-bound generated evidence is current`）。
- 冻结前生成物刷新（`dedd7e38`）：契约结构指纹补上 `sc.general.contract` 的已声明状态机
  （`GENERAL_CONTRACT` 表）、组件接管清单按当前生产消费者计数更新、测试台账 1494→1508
  （本分支新增业务编号 15 例 + 数据范围核算 4 例）。
- 状态边界：到本段为止可报**批次验收完成（源码 + 守卫 + 定向测试）**与**冻结准备通过**；
  尚未跑一次精确 HEAD 的 `ci.local.quick`、未推送、未开 PR、未主线集成、未部署、未产品交付。

## 冻结后 Quick 失败收口（2026-10-14，交接执行器）

冻结准备通过后按规约只跑一次精确 HEAD 的 `make ci.local.quick`，连续暴露两个
**冻结门禁自身的问题**，均为收口项、非产品缺陷，逐项定位后修复并重跑。

### 装配契约缓存版本/指纹重钉（`774dee1a`）

- 现象：`make ci.local.quick` shard `verify.unified_page_contract.v2.assembler` 报
  “assembled contract cache inputs changed without re-pinning”。
- 根因：本分支在 `f0a549ea` 之后修改了 3 个装配缓存输入
  （`addons/smart_core/contract/unified_page_contract_v2_assembler.py`、
  `handlers/ui_contract_v2.py`、`handlers/ui_contract_v2_projection.py`），
  但缓存版本串与内容指纹未同步更新，守卫按“输入变更未重钉”fail-closed。
- 修复：缓存版本 → `ui-contract-v2-2026-10-14-declared-layout-columns-and-action-denial-guidance`
  （`handlers/ui_contract_v2.py` 与 `scripts/verify/unified_page_contract_v2_assembler_guard.py`
  两处同步）；内容指纹 → `727e308bfca58642bc8716ed59420b653b3502ae55de3caed36a07bf117bf2c5`。
- 取证：`.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/logs/verify_upc_v2_assembler_repin.log`，
  `make verify.unified_page_contract.v2.assembler` **rc=0**。

### 工作流动作覆盖泳道测试桩与模型实现同步

- 现象：第二次 `ci.local.quick`（HEAD `774dee1a`）7/8 shard 通过，唯一失败
  `verify.native_view.workflow_action_coverage`：
  `test_native_view_workflow_action_coverage_guard.py:417`
  `test_signing_executes_the_existing_confirmation_before_draft_transition` 抛
  `AttributeError: 'types.SimpleNamespace' object has no attribute 'with_context'`，
  栈指向 `addons/smart_construction_core/models/core/general_contract.py:434`。
- 根因：模型 `action_signed` 已改为受控跃迁
  `rec.with_context(allow_transition=True).write({"state": "signed"})`，
  而测试辅助 `_sign_record()` 仍以裸 `SimpleNamespace` 打桩，缺 `with_context` 与 `write`。
  属**测试桩滞后于模型实现**，不是产品缺陷；同文件既有桩约定（约 163、617 行）
  本就是给桩补 `with_context`。
- 修复（限定在该测试文件）：`_sign_record()` 的桩补 `with_context`（记录传入 kwargs）
  与 `write`（更新桩属性）；草稿跃迁用例追加断言
  `self.assertIn({"allow_transition": True}, record.contexts)`，确认受控跃迁上下文
  确实被传入。**未放宽任何既有断言**。
- 取证：`logs/verify_native_view_workflow_action_coverage_stub_fix.log`，
  `make verify.native_view.workflow_action_coverage` **rc=0**
  （8 + 8 + 58 tests OK；守卫 `registered=40 document_helper=14 navigation=26`）。
- 生成物联动：测试文件 818 → 826 行，`docs/engineering_convergence/complexity_budget_report.md`
  的复杂度排序随之刷新，随桩修复一并提交（不改历史数字，只随源码如实刷新）。
- 复核：`make ci.delivery.freeze.prepare` 再次 **rc=0**
  （`PASS all content-bound generated evidence is current`，
  `PASS candidate=unfrozen next=review_generated_changes_commit_freeze_then_run_quick_once`）。
- 状态边界：本段仍只支撑**批次验收完成（源码 + 守卫 + 定向测试）**与**冻结准备通过**；
  精确 HEAD 的 `ci.local.quick` 仍在未推送状态下重跑，未主线集成、未部署、未产品交付。

### 同 shard 被 fail-fast 掩盖的下一项：Web 契约 v2 前端架构守卫令牌同步

- 现象：修复测试桩后，同一 shard（6/7）的下一项暴露失败
  `verify.unified_page_contract.v2.web_architecture` →
  `web_contract_v2_frontend_architecture_guard FAIL`：
  - `pages/contractForm/useRecordActionPresentation.ts` 缺 `resolveWorkflowContractFromStore(v2ContractStore.value)`
  - `pages/contractForm/useRecordActionPresentation.ts` 缺 `normalizeWorkflowEvidenceGateRows`
  - `pages/ContractFormPage.vue` 缺 `workflowEvidenceGateRows`
- 为什么现在才出现：上一轮 `774dee1a` 的 shard 6/7 在
  `verify.native_view.workflow_action_coverage` 处 fail-fast 中止，而该目标在
  `make/ci.mk` 的目标顺序中**先于**本守卫，故被掩盖。按“同一层独立失败一次收全”的要求，
  本次连带把该 shard 失败点之后的目标一并跑完，不再靠下一轮 Quick 才发现兄弟失败。
- 事实（先证后改）：
  - 本分支 `265963f6` 删除前端 warning/evidence 常驻主体，并在代码注释中明确
    “executable availability is already joined into Contract V2 action authority and
    must not be recomputed here”；该退休在批次记录 P0 段已登记，**只是本守卫的
    REQUIRED 令牌表未随之更新**。
  - `resolveWorkflowContractFromStore(v2ContractStore.value)` 仍存在，现由
    `pages/ContractFormPage.vue:1137` 的 `validateSubmissionRequirements` 消费，
    “表单必须从 v2 store 解析工作流契约”这一不变量仍成立。
  - `workflowEvidenceGateRows` 在 `frontend/` 源码中已无任何出现；
    `normalizeWorkflowEvidenceGateRows` 仅作为 `workflowContract.ts` 的导出序列化器保留、
    无消费者。
  - `scripts/verify/frontend_professional_workflow_guard.py` 已对
    “模板重新出现 `warnings|workflowEvidenceGateRows`” fail-closed。
- 修法（保意图、不降覆盖）：把 store 解析令牌改指真实消费点
  `pages/ContractFormPage.vue`；把两条已退休的重算令牌**从正向必需改为反向禁止**
  （新增 `FORBIDDEN_WORKFLOW_EVIDENCE_RECOMPUTE_TOKENS`，由
  `validate_workflow_contract_projection()` 执行），因此保护从“必须有重算”升级为
  “不得在表单呈现层重算”，与既有的 professional workflow 守卫同向。
- 反例验证（注入即必须失败）：
  - 向 `useRecordActionPresentation.ts` 注入 `workflowEvidenceGateRows` → **FAIL**，rc=2，
    报 `workflow evidence gate must not be recomputed ...`；随后已还原。
  - 改名 `ContractFormPage.vue` 中的必需 store 解析令牌 → **FAIL** 缺必需令牌，rc=2；
    随后已还原。
- 同 shard 其余目标（原先从未跑到的）：`make verify.unified_page_contract.v2` **rc=0**
  （整链含 web_architecture PASS / stable_projection / frontend_static 前端构建）、
  `verify.frontend.dev.incremental.unit` **29 tests OK**、`verify.frontend.lint.src`
  **rc=0（0 errors，65 warnings）**。
- 其它：`make verify.frontend.professional_workflow.unit` rc=0（8 tests OK）、
  `make verify.guard.registry` AUDIT PASS（1443 scripts）、
  `make ci.delivery.freeze.prepare` 再次 **rc=0** 且无生成物差异。
- 状态边界：仍只支撑**批次验收完成（源码 + 守卫 + 定向测试）**与**冻结准备通过**；
  精确 HEAD 的 `ci.local.quick` 重跑、推送、主线集成、部署、产品交付均未发生。

## 平台/行业初始化理顺 + 数据空间接入权威 + bootstrap 禁载业务数据（2026-10-14）

- 所有者裁定：平台初始化与行业初始化彻底理顺；单库多公司 / 每客户独立建库为**可选择策略**；
  正式客户公司必须独立建库；`DEMO_IS_FIRST_ONBOARDED_COMPANY=true`（demo 是一等数据空间，
  既不是技术件也不是 bootstrap 公司）；`BUSINESS_DATA_NEVER_IN_PLATFORM_BOOTSTRAP_COMPANY=true`。
- 唯一初始化顺序：平台技术基线 → 平台机制 → bootstrap 公司标记 → 数据库策略声明 →
  数据空间接入 → 行业初始化 → 客户差异化。违反顺序产生的业务数据即“归属未知业务数据”，
  只能由受管迁移处理。
- 本轮产出（P0 边界 + 守卫 + 单测，未新增字段）：
  - 边界文档 `docs/architecture/platform_industry_initialization_and_database_strategy_v1.md`
    （权威仍是 `docs/governance/database_architecture_policy.md`，本文件不复制政策）；
  - 声明 `config/tenant/database_strategy.v1.json`（三角色 `platform_internal_demo` /
    `industry_acceptance` / `customer_production`，两条策略，5 条不变量）；
  - 接入权威 `addons/smart_core/security/data_space_provisioning.py`：
    `strategy_for_purpose` / `validate_strategy_declaration` / `onboard_business_company`
    （customer 用途在此**拒绝**，仍走受签 `smart_core.tenant_payload_import`）/
    `assert_business_data_space_ready`（行业与 demo 初始化前置 fail-closed）/
    `unregistered_business_companies`（未注册公司归属未知不放行）/
    `bootstrap_company_business_data_violations`（探针模型由行业/ops 层传入，P0 不写行业语义）；
  - 守卫 `scripts/verify/database_strategy_guard.py`、`scripts/verify/data_space_provisioning_guard.py`；
  - 单测 `scripts/verify/test_database_strategy_guard.py`（11）、
    `scripts/verify/test_data_space_provisioning.py`（16）；
  - 挂载 `make/dev_test.mk` 新目标 `verify.database.strategy.guard`、
    `verify.data_space.provisioning.guard`，并登记进 `make/ci.mk` 的
    `verify.contract.architecture.suite` 静态套件。
- 验证回执：`make verify.database.strategy.guard` rc=0（PASS + 11 tests）；
  `make verify.data_space.provisioning.guard` rc=0（PASS + 16 tests）；
  `make verify.guard.registry` AUDIT PASS（1449 scripts, 198/198 unwired dispositioned）；
  `make verify.sc_data_scope.rule_coverage` rc=0（37 tests，universe=138，enforced=117，
  deferred=26，exempt=33，source_bounded=32，uncovered=[]，generated rules=143）；
  `make verify.agent.ledger.unit` rc=0。
- 受管只读回读 `make local.dev.data_scope.ceiling.readiness` rc=0：已安装上限与提交源一致
  （source 143 / installed 143 / mismatches=[]）；同一个回读同时给出环境事实：
  `sc.tenant.company.registration` **0 行**，40 个内部账号解析到 **0** 家公司，
  `payment.request` 141 / `sc.general.contract` 3 / `project.project` 72 **全部挂在
  bootstrap 公司 id=1 `My Company`**，company 3 `Demo Secondary Company` 存在但未注册。
  该事实直接违反 `business_data_never_in_platform_bootstrap_company`。
- 回读脚本同时修了两处事实缺陷：多跳锚点（`settlement_id.project_id.company_id`）改为逐跳解析，
  `project.settlement.line` / `tender.opening.competitor` 不再被误报 `anchor_is_not_a_relation`；
  新增 bootstrap 公司业务行探针。
- 本轮**未做环境写操作**：没有创建/注册公司，也没有把 company 1 的业务行改归属。
  后续受管 P4 迁移（先接入 `purpose=demo` 公司，再改归属，再回读直到 bootstrap blocker 清零）
  需所有者授权后才能执行；在完成前，浏览器验收无法观测 payment/contract 行。
- 状态边界：本轮只支撑**批次验收完成（源码 + 守卫 + 定向测试 + 只读回读）**；
  主线集成、版本发布、产品交付均未发生，交付链仍被上述环境 blocker 阻断。

### 迁移范围更正：216 行 → 31,240 行（2026-10-14，授权后实测）

所有者已授权受管 P4 迁移。执行前先做恢复点 `make local.dev.snapshot`
（`artifacts/local-dev/snapshots/20261014T012104Z`），再以只读计划入口
`make local.dev.demo.data_space.migrate`（未带确认 → 只读 + 回滚）实测真实写集：

- 之前“216 行”来自四模型探针，**是错的**，已作废。真实范围：
  - 数据上限集内 **81 个模型 / 31,240 行**，最大持有者
    `ui.business.config.mutation.audit` 30,118、`sc.audit.log` 198、`payment.request` 141、
    `sc.project.document` 129、`construction.work.breakdown` 88、`sc.expense.contract.ledger` 77、
    `project.project` 72；
  - 上限集之外还有 **61 个模型**挂 bootstrap 公司，含 `ir.attachment` 14,542、
    `tier.definition` 6,298、`sc.ui.base.contract.asset` 3,740、`tier.review` 384、
    `project.task` 155、`construction.contract` 121，以及
    `account.*`（科目/日记账/税）、`stock.*`（仓库/库位/路线）、`purchase.*` 等核心表；
  - 若走“换公司”方案还需改 56 个账号的公司成员关系与 58 个账号的默认公司。
- 事实判断：`base.main_company`（id=1「My Company」）由
  `addons/smart_core/data/platform_bootstrap_company.xml` 明确标记为 bootstrap，
  但本地演示库的**几乎全部数据**都挂在它下面；`sc.tenant.company.registration` 为 0 行。
  即：这不是少量“漂移行”，而是“整个演示库的归属事实与 bootstrap 标记语义冲突”。
- 因此本轮**停在不写**，并给出待裁定的两条路线：
  - **选项 1（标记/策略收口，0 行数据迁移）**：把 `base.main_company` 注册为本库 demo 数据空间
    （`adopt_business_company`，1 行），并修正 demo 角色下的 bootstrap 标记语义
    （bootstrap 标记的不变量约束 `customer_production`；`platform_internal_demo` 的主公司即首个已接入演示公司）。
    代价：policy 级，但需同步 `platform_bootstrap_company.xml`、
    `registration_scope_domain`、`smart_construction_seed` 税默认落点及相关测试。
  - **选项 2（全量改归属）**：保留标记，接入独立公司（id=3）并把 31,240 + 61 模型的行迁过去。
    代价：触及核心账务/库存/采购数据、1.45 万附件、6,298 条审批层级定义与 3 万条配置审计行；
    需要分阶段方案 + 可重放迁移模块，不适合一次性脚本写入。
- 本轮实际完成（可提交、可回滚）：
  `_register_non_customer_space`（既有公司接入，拒绝 bootstrap 公司与已注册公司）+ 唯一维护主体校验收敛
  （`_assert_non_customer_maintenance` / `_open_non_customer_registration`，去掉重复校验逻辑）、
  `data_space_provisioning.adopt_business_company`、只读迁移计划工具与 Make 入口。
- 验证回执：`make local.dev.test MODULE=smart_core TEST_TAGS=data_space_boundary`
  **0 failed / 0 error，33 tests**（含新增 6 项接入边界用例：可接入、加入非客户数据域、
  拒绝 bootstrap 公司、拒绝重复注册、拒绝 customer/非法用途、产品管理员 sudo 不可接入）；
  `make verify.data_space.provisioning.guard` rc=0（18 tests + guard PASS）；
  `make verify.data_space.policy.unit` rc=0（12 tests）。
- 状态边界：仍是**批次验收完成**；主线集成/版本发布/产品交付未发生，且交付链等待上述路线裁定。

### 路线裁定与落地：选项 1（第 27 棒，2026-10-14）

所有者裁定 `DEMO_IS_FIRST_ONBOARDED_COMPANY=true`：demo 用途下环境主公司**就是**第一个已接入的
业务公司，接入动作 = 退役技术载体标记，不做任何行归属改写（选项 1，0 行数据迁移）。上面「停在不写」
的待裁定状态由此关闭；选项 2（全量改归属 31,240 + 61 模型行）不再执行。

- 声明文件从 `config/tenant/database_strategy.v1.json` 迁到
  `addons/smart_core/data/tenant/database_strategy.v1.json`：`config/` 不在 Odoo 容器挂载内，
  声明必须随模块分发。三角色新增 `main_company_onboarding_purpose`（demo→`demo`、
  acceptance→`test`、customer→`null`）与不变量 `environment_main_company_onboarding_is_role_scoped`。
- `addons/smart_core/security/data_space_provisioning.py` 新增 `environment_role()` /
  `declare_environment_role()` / `main_company_onboarding_purpose()` /
  `onboard_environment_main_company()`；模块仍不 import odoo。
- `addons/smart_core/models/tenant_payload_import_batch.py` 新增唯一允许注册 bootstrap 公司的入口
  `_adopt_environment_main_company()`：拒绝 customer 生产角色、拒绝非本环境主公司、拒绝本库已有
  活动注册、拒绝该公司已有注册；先写 `is_platform_bootstrap_company=False` 再建注册行。
  内部错误码 `DATA_SPACE_CUSTOMER_ROLE_MAIN_COMPANY_IS_A_CARRIER` /
  `DATA_SPACE_ENVIRONMENT_MAIN_COMPANY_REQUIRED` / `DATA_SPACE_COMPANY_ALREADY_REGISTERED` /
  `DATA_SPACE_DATABASE_ALREADY_OWNS_A_REGISTRATION`。既有 `_register_non_customer_space` /
  `_open_non_customer_registration` 保留不动。
- `demo_addons/smart_construction_demo/hooks.py`：`ENVIRONMENT_ROLE="platform_internal_demo"`、
  `DEMO_TENANT_KEY="sc-demo-main"`，`onboard_platform_data_space(env)` 幂等入驻，
  `guard_demo_data_space(env)` 在 `pre_init_hook` 与 `apply_demo_user_passwords` 前置；
  demo 只在标记退役后播种，且**从不自己制造注册行**。
- 受管写入入口 `make local.dev.data_space.onboard`（默认只读，`SC_CONFIRM_DATA_SPACE_ONBOARDING=onboard`
  才写）；删除 `local.dev.demo.data_space.migrate` 与 `scripts/verify/local_dev_demo_data_space_migration.py`。
- 验证回执：`make verify.database.strategy.guard` rc=0（PASS + 11 tests）；
  `make verify.data_space.provisioning.guard` rc=0（PASS + 28 tests，invariants=6）；
  `make local.dev.test MODULE=smart_core TEST_TAGS=data_space_boundary` rc=0（37 tests，0 failed/0 error）。
- 环境事实（干净重建库）：`pre_init` 自动入驻端到端成立 —— `environment_role=platform_internal_demo`、
  `registration_rows=1`、`registered_company_ids=[1]`、`bootstrap_company_ids=[]`、
  `onboarded_demo_company_ids=[1]`。
- 状态边界：仍只支撑**批次验收完成**（源码 + 守卫 + 定向测试 + 只读/受管回读）；
  主线集成、版本发布、产品交付未发生。

### 遗留缺陷：demo 场景种子滞后产品守卫（main 既有，非本棒引入）

`make local.dev.rebuild_demo` 在 scenario 阶段失败。事实：

- 守卫 `create()` 拒绝直接写入非 `draft` 状态，由 **2026-10-01 #525
  `feat(web): adopt official template rendering...`（2d164a1f）** 引入；demo 场景种子最后更新是
  **2026-09-05 #435**，其后未随守卫同步。即“demo 滞后产品”，属于 main 上的既有缺陷。
- 一次性记录级诊断（savepoint 回滚、不提交）得到 **62 条**记录级失败，其中约 **30 条为根因**，
  其余为父记录失败后的级联（External ID not found）。
- 根因按模型/场景分布（节选）：`sc.payment.execution`、`sc.treasury.reconciliation`、
  `sc.construction.diary`、`sc.invoice.registration`(×2)、`sc.project.document`(×2)、
  `sc.material.purchase.request`、`sc.plan`/`sc.plan.line`、`sc.safety.plan`(×2)、
  `sc.labor.plan`/`sc.labor.request`/`sc.attendance.checkin`/`sc.labor.settlement`、
  `sc.equipment.plan`/`sc.equipment.request`/`sc.equipment.usage`/`sc.equipment.settlement`、
  `sc.subcontract.plan`/`sc.subcontract.register`/`sc.subcontract.settlement`、
  `sc.material.rental.plan`/`order`/`settlement`、`tender.doc.purchase`、`sc.contract.event`(×2)、
  `sc.financing.loan`、`sc.hr.payroll.document`、`sc.settlement.adjustment`、`sc.output.invoice.adjustment`
  （缺 `original_ledger_id`，非状态问题）。
- 修复方向（与仓库既有约定一致）：XML 落 `draft`，再由 `scenario_loader` 的
  `_ensure_*(env)` 步骤走正式动作达成终态（既有 `_ensure_s85_payroll_lifecycle` /
  `_ensure_s80_material_lifecycle` / `_ensure_s69_*` 即此模式）。属独立、可单独验收的
  产品结果，规模较大（约 15 个模型 / 10 个场景，部分需审批流），不并入本棒平台初始化批次。

## 一步式办理收口：终态动作不再强制先提交（2026-10-14，所有者裁定）

所有者裁定：

> 对用户来说就是一个动作，不需要先提交再确认 —— 这是系统该完善的内容。

### 问题事实

终态业务动作（`action_confirm` / `action_accept` / `action_activate` / `action_done` /
`action_archive` / `action_select` / `action_receive` / `action_issue` 及各类结算确认）在**没有审批
规则**时仍要求先 `action_submit()`，用户被迫两步：先「提交」再「确认」。同一事实被误用的表现是
demo 场景种子直接写终态、被 2026-10-01 create() 守卫拒绝（见上一节）。即：不是审批流拦人，而是办理
闸门把「无审批」当成了「未审批」。

### 机制（P0 平台内核，唯一闸门）

新增 `sc.approval.policy.ensure_handling_ready(record, approved_states, submit_states=("draft",))`
（`addons/smart_construction_core/models/support/approval_policy.py:419`）：

- `record.review_ids` 为空且状态 ∈ `submit_states` → 查 `is_approval_required()`：
  - 无审批规则：内联 `action_submit()` + `invalidate_recordset()`，调用方的**一个动作**直达终态；
  - 有审批规则：`UserError`（fail-closed），单据保持 `draft`。
- 仍委托 `_assert_submission_approved()`：审批实例未通过、状态不在 `approved_states` 一律拒绝。
- 没有 `action_submit` 的模型：保持原行为与原有报错。

**裁定：`submit_states` 只保留 `("draft",)`。** 曾试 `("draft","rejected")`，会让驳回态也能一步到
终态，属状态机放宽回归（p0_state 3 条块级用例由 PASS 变 FAIL），故收紧为仅 `draft`；「驳回后重新
提交」仍走原两步语义。

### 调用点与投影声明

- 18 个终态动作调用点（10 个模型文件）由 `_assert_submission_approved` 改为 `ensure_handling_ready`：
  material_acceptance 6、labor_management 3、material_rental 2、equipment_management 2、
  subcontract_management 1、output_invoice_adjustment 1、contract_event 1、document_center 1、tender 1。
- 投影层 `workflow_contract_service` 新增 `_handles_without_approval()`（:1346），并在
  `_available_actions()`（:1362）加入 direct handling 分支：**无审批规则**时用 `direct_handling`
  声明的动作取代 `submit`；**有审批规则**时立即恢复 `submit` 并隐藏 direct handling。17 个 profile
  声明 `direct_handling`：12 个 `{"draft": ["complete"]}`；`sc.material.acceptance` →
  `["accept_result","reject_result"]`；`sc.material.rental.order` → `["activate"]`；
  `sc.material.rental.settlement` / `sc.subcontract.settlement` → `["confirm_settlement"]`。
- **不可回退**：`material_acceptance` 的 `_sc_require_state({"draft","approved"})` 放宽必须保留。覆盖
  守卫以**模型源码的方法守卫**推导期望投影（投影 ⊆ 方法守卫），回退成 `{"approved"}` 会让守卫新增
  2 个失败。

### 验证回执（本棒）

| 入口 | 结果 |
|---|---|
| `make verify.native_view.workflow_action_coverage` | rc=0（59 tests） |
| `make verify.workflow_state_phase_coverage` | rc=0（17 tests） |
| `make verify.workflow_action_semantics.guard` | rc=0（15 tests） |
| `make local.dev.test MODULE=smart_construction_core TEST_TAGS=…`（6 条定向：p0_state ×4 + 门禁 ×2） | rc=0，0 failed / 0 error of 6（sc_dev_demo） |
| `python3 scripts/verify/test_payment_approval_state_machine.py` | 3 error，与 stash 基线逐字一致（既有漂移） |
| `python3 addons/smart_core/tests/test_workflow_contract_profile_registry.py` | rc=0（9 tests） |
| `make verify.agent.ledger.unit` | rc=0（15 tests + PASS） |

新增/改写用例：`test_handling_gate_finishes_one_step_without_approval_rule`、
`test_handling_gate_keeps_submission_when_approval_rule_configured`、
`test_direct_handling_refuses_when_approval_rule_configured`、
`test_direct_handling_replaces_submission_only_without_approval`。日志：
`.runtime/evidence-logs/onestep_targeted_*.log`。

### 与 demo 场景漂移的关系

一步式闸门消掉了对齐工作的一半前提：种子只需落 `draft`，**一个**受治动作即可到终态，不再需要显式
`action_submit()`。剩余工作（约 30 条根因记录 / 约 15 个模型 / 10 个场景，改写 `scenario_loader` 的
`_ensure_*` 钩子）仍属独立可验收结果 `DEMO-SCENARIO-PRODUCT-DRIFT-01`，**禁止**以放宽 2026-10-01
create() 守卫的方式绕过。

### 边界

- 状态：**批次验收完成**（源码 + 守卫 + 定向 ORM 用例）；主线集成、版本发布、产品交付均未发生。
- 既有失败（本棒不处理，已在 run 登记）：`verify.workflow_contract.backend` 红泳道（不在
  `ci.local.quick.run` 前置清单内）、uc4 native-lowcode 视图漂移、`TestApprovalPolicyToggleBackend`
  AccessError 漂移、p0_state 8 个既有 ERROR、`verify.contract.lint` 49 项、`res.users` 断言漂移、
  L3/L4 container。
- 未做：新页面、新组件、状态机 DSL、批量重构 `extractListProfile`。
