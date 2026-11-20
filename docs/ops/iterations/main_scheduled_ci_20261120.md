# Mainline and scheduled CI recovery

Current base: f2f7fd02f0f28f84e6190102f3bf559db0c28457. Original base: d2fb27530f5c1bf56719660af64199c6b343d8ff. Branch: fix/main-scheduled-ci-20261120.

## Current scope and gate responsibilities

Formal Product Layers: **P0 / P1 / P4**. P0 `smart_core` owns native executable authority and role action identity admission, including multi-XMLID record identity. P1 `smart_construction_core` owns industry workflow declarations and scenario navigation composition. P4 owns real publication fixtures, verification probes/guards, test type imports and evidence. These are platform mechanisms, industry standards and verification prerequisites respectively; no P2/P3 customer configuration or frontend product-semantic change is included. All edits are confined to this recovery worktree. The owner explicitly confirmed that the full mainline/scheduled-equivalent candidate chain is the intended recovery scope.

| Gate | Responsibility | Current evidence / remaining requirement |
|---|---|---|
| Identity and independent review | required for each published candidate | Clean full SHA, exact base, scoped independent review; keep #950 Draft |
| P0 identity/route contracts | required | Multi-XMLID, metadata failure, unresolved policy, model-scoped identity, lawful no-XMLID action, and discovery/fallback real-method regressions |
| P1 owning families | required, reusable only for unchanged inputs | Workflow/scenario changes and dependency-selected ORM; original assertions retained |
| Main acceptance fixture | required | 49/49 passed at 7ee; P0 identity change requires new affected runtime evidence |
| Module / affected ORM coverage | required | Scoped owning 609 passed at 7ee; exact receipt scope retained; broad platform diagnostics remain failed, not presented as a green baseline |
| Coverage registry and execution reconciliation | required | Registry guard plus final remote managed-ORM producer/receipt reconciliation |
| Frontend lint, strict typecheck, build and browser | required | Test import fix passed full lint and strict typecheck; full candidate lane owns build and actual browser validation |
| Local iteration and publication | required | Governed `ci.local.iteration`, public scope, generated evidence and fast-forward checks |
| Four remote required gates | required on final exact HEAD/base | Full `ci:candidate` is intentional for this recovery; partial shards or old HEAD success cannot substitute |
| Production deployment / customer data changes | excluded | No deployment, merge or customer data mutation authorized by this batch |

The sections below retain the chronology of investigation and earlier attempts. Their old statuses and scope statements describe those historical stages; this table and the current run/PR evidence index define the current candidate.

Failures: main 44659427467 managed ORM 12 failures/1 error; scheduled 44643045425 missing admin_close_01, scene ORM 2 failures, core ORM 3 errors; scheduled 44645213929 missing released payment navigation. Downstream merge/release gates correctly reject failures.

The primary worktree run is superseded; two other worktrees are clean detached archives. The product worktree remains active; this independent CI recovery is the second active writer.

## Historical initial expansion into P0

P0 smart_core DeliveryEngine: native route discovery lost primary actions because build_route_authority received no navigation. Supply the native ACL/action-group and role-filtered tree, preserving product metadata separately. No industry/menu special case. At that initial stage P0 baseline and affected scene/acceptance consumers were required; later P1 workflow/scenario changes are included in the current scope above.

Industry CI selection sc_smoke,sc_gate passed 566 tests (baseline HEAD plus recorded dirty source; affected ProductPolicyFactAuthority 23 and ScenarioDirectInitialization 13 cases were collected); initial focused family passed 23; publication unit passed 41; coverage registry passed. Source inputs unchanged since industry baseline except this result metadata. Acceptance attempt failed on missing schema column, not a valid candidate result. Upgrade required before retry.

Acceptance target: registered local profile, sc-fe-r2-p1-01, sc_frontend_acceptance, exact filter ^sc_frontend_acceptance$, filestore sc_fe_r2_p1_01_odoo; isolated synthetic acceptance tenant, not customer production/control/catalog. Use governed writer leases and restoration. No other database authorized.

Scene baseline passed 10 tests. Platform CI selectors sc_smoke/smart_core,sc_gate/smart_core passed 17 tests. Static consumer checks passed 501 tests. Additional affected ORM targets passed; original logs are under .runtime/ci-recovery/affected-orm.log.

The additional exhaustive standalone smart_core diagnostic failed (29 failures, 75 errors of 460): observed causes include missing industry models/namespace, maintenance requester identity, signed capability, native form envelope prerequisites, and other contract assertions. Causes were not all classified. It is not claimed as a passed baseline. This is separate from the actual CI-selector result above; no assertion or gate was removed.

The acceptance module upgrade consumes sealed artifact 0572684a5b732f6cce3e4748161212547c066894. Subsequent changes only relocate a test helper and correct task metadata, with no database/schema or runtime-code changes. Rebuild the acceptance service artifact at the resulting clean HEAD before the fixture rerun.

## Owner-confirmed scope and current validation

The owner reaffirmed that contract production and consumption are the validation core. The contract_only PR policy was intentionally introduced by the owner and remains unchanged. This recovery does not change its classifier, scopes, exclusions or workflow strategy. Add a regression on the navigation-to-execution-authority contract and establish actual published snapshot prerequisites.

Complete ci.local.iteration passed at 998ffcc6b8d9fd7f57718a57f749f80cd129264c, including all mapped non-zero ORM targets. Original log: .runtime/ci-recovery/iteration-2.log. A separate /smart_core diagnostic using the bundle template ran 638 tests, with 56 failures and 88 errors (.runtime/test-baseline/1795146387016971210/receipt.json). This is not claimed as a passed module baseline or merge qualification. Its broad authentication, maintenance and installed-industry interactions remain outside automatic expansion of this repair; independent review and merge status must retain the limitation.

Independent review found no confirmed runtime permission expansion or assertion weakening. It requested correction of coverage-tool dependency registration (now corrected), and retained a merge-readiness finding on module-baseline and pending acceptance/remote evidence. Draft publication is review-only; no merge or deployment claim.

## Acceptance prerequisite correction

The old synthetic carrier schema upgrade completed and the ce1da712 registry restarted successfully. Its 49-test run exposed a historical preview snapshot in the two-edition catalog and an undeclared positive setup-entry publication. The test helper now isolates historical standard/preview snapshots within TransactionCase and asserts its real replacement is active/released. Navigation tests explicitly select the setup entry from the real catalog before publication; allowed and denied roles consume the same published fixture. Original consumer/permission assertions remain intact. No runtime publication bypass or contract_only policy change.

## Review S2: complete action identity at admission

The ce1da712 review reproduced a finance-blocked action through another authorized menu. Native facts omit action XMLID; discovery resolves it after the first role filter. Reapply the same role predicate after complete identity resolution, including the released-policy fallback, before admitting executable primary authority. No ACL or publication exception is introduced.

The regression executes actual MenuService authorization, role projection and discovery, the actual finance policy, enabled-scene filtering and route validation; only ORM facts and publication inputs are bounded doubles. Both menus are publication-eligible, so publication cannot hide an erroneous role grant. Before the fix the blocked alias was accepted with batch and singleton XMLID resolution (two failing subtests); after the fix all 24 entry tests passed, including the unblocked action positive. Focused publication, metadata batch, navigation and fixture unit targets passed 266 tests (.runtime/ci-recovery/s2-focused.log).

The 07310b fixture run was interrupted, not passed: repeated full catalog construction was moved to class setup as a plain immutable declaration. Every test still creates its own maintained policy and released snapshot, then consumes as the real user. No runtime authority or ORM recordset is cached across tests. New sealed-candidate 49-test execution remains required.

## Candidate consumer follow-up

At c7fd87f189d0c6c18b18a5756a0880e9e95f2432 the independent read-only check accepted the complete-identity role admission direction and requested direct released-policy fallback coverage. That extra positive/negative test now passes (25 entry tests total). Its ORM inputs are controlled; it is not represented as a full system.init ORM baseline.

The ce1 candidate frontend run 44671232127 passed the formerly missing payment target and then failed the retained payment detail zero-contract-reload assertion. The probe waited only for a visible content card, which can render between contract and record completion. Its warmup and measured detail selector now require the exact model/record/action/menu and data-state=ok. The zero repeated primary contract assertion and all budgets remain unchanged. Real Chromium DOM confirms a visible loading card is excluded, completed exact identity is accepted and a different record is excluded; 56 related unit tests and the static guard passed. Full application behavior remains pending on the new candidate. This is a P4 probe precondition correction, not a frontend product-semantic change.

Coverage job 136076442403 in run 44671232177 passed shard coverage processing, then rejected the failed frontend producer while discovering managed ORM receipts. Its missing JSON upload is secondary. Do not weaken producer success or claim shard success closes overall reconciliation.

## Main advance and remaining fixture diagnostic

ci.local.iteration completed at 412ff2f6d736fcd8bbea18981c80626bdff1c34e; push was stopped before remote mutation because PR949 advanced main to f2f7fd02f0f28f84e6190102f3bf559db0c28457 and two generated reports conflicted. The governed published-GitHub sync appends that exact main without rewriting candidate history. Regenerate reports and bind subsequent validation to the new base.

The c7 artifact fixture run completed 49 tests: 0 failures, 1 error (420.78s). The sole remaining error is missing scenario_surface for the test-created business_full principal; all earlier publication/setup assertions now pass. The projection provider suppresses internal exceptions. A test-only failure diagnostic replays it with the same principal and same navigation/authority to reveal the original exception; it never substitutes the result, grants groups or changes production behavior. Full fixture and candidate success are still pending.

## Required workflow gate: declaration regression and test drift

The completed ce1 professional_quality_checks job independently failed verify.native_view.workflow_action_coverage (59 tests, 3 failures and 2 errors). Two errors were missing real helper dependencies; project disabled-action and rental success-code expectations lagged current declared contracts. The helper now executes actual _gate and _handles_without_approval with bounded approval-policy facts. Tests retain the executable action set and add precise disabled semantics/reasons; rental checks both the actual execution blocker and external success code OK.

P1 workflow_contract_service: PR933 changed ten submitted-state profiles from submit to approve despite every actual action_submit allowing submitted-state resubmission. A no-review, non-reviewer document consequently exposed enabled validate_tier. Restore submitted=[submit,cancel] for subcontract plan/request, safety plan/disclosure, material purchase request, equipment plan/request, labor plan/request and material rental plan. Existing submit domain and pending-reviewer admission remain intact. The original failing resubmission assertions are preserved, with 60 parameterized cases over all ten profiles and native business-method state guards. The required gate now passes 3+8+60 tests (.runtime/ci-recovery/workflow-final.log). This is a confirmed declaration regression, not solely fixture drift; affected owning workflow ORM remains required.

## Scenario producer and owning-module closure

The same-principal diagnostic at ee215ae410a01270e006b36e125a1812797e78f5 identified canonical navigation duplicate identity (49 tests, 0 failures, 1 error), not missing configuration privileges. Real flatten + center composition + native node builders + canonical validator reproduce the mechanism: an actionless directory with /m/:id route and children was collected as a leaf, then reattached under a center using the same native menu ID. P1 flattening now keeps that node as a directory while still descending into its children. Actionless scene leaves and action-backed entries remain represented. Regression retains the strict duplicate validator, proves exact parent/leaf identities and verifies that an actual repeated leaf still fails.

The affected owning-module selection at 47a0e77de35e389027e5c707c1565848573485f4 ran 609 tests (sc_smoke,sc_gate,workflow_contract_backend,approval_contract_closure,be_close_01_workflow_contract): 1 failure, 0 errors. The sole failure was the existing shared-template/profile equality test; the ten concrete profiles were corrected but their reference helper still declared approve. Synchronize that helper, preserving the ORM equality assertion. This failed receipt is retained; final corrected 49/609 runs remain required.

The corrected owning-module selection passed all 609 tests at 89680de3f70f8f900e7b9ffc3fa805d0d135451f (.runtime/test-baseline/1795150211270439515/receipt.json). The 49-test acceptance rerun still has the same single business_full duplicate-identity error. The controlled routed-directory fix alone does not close that actual case; capture exact key/menu/parent identity before any further production fix. No fixture success claim.

## Statusbar guard alignment

Following the formerly failing workflow guard through the required professional contract suite exposed two stale architecture tokens: synthetic __workflow_phase and dictOrEmpty(workflow.statusbar). Current P1 produces the native state_field and its selection; current consumer validates field/current, readonly, source and current-state membership. Preserve those production/consumption checks and update only the P4 guard to require their actual declarations. Existing canonical presenter tests and architecture/stable-projection guards pass; five controlled mutations (synthetic field, removed native selection, removed readonly/source/membership validation) are rejected. No production statusbar behavior is changed.

### Native menu identity during scenario supplementation

The identity diagnostic at `147c8eb3dba8d162c8b66d94574fc32567af2bc8` completed 49 tests with one failure (the test converts the suppressed projection exception to a diagnostic assertion). Menu 698 already represented published action 946; the supplementation loop promoted contextual actions 870/785/876 on the same carrier into extra navigation leaves. This is distinct from the separately reproduced routed-directory defect.

P1 scenario projection now preserves each existing navigation menu identity, supplements only primary/home declarations, and resolves multiple authorized candidates against native menu action metadata. An unresolved ambiguity is explicitly reported and adds no leaf. Contextual/admin execution authority remains unchanged; explicitly published admin navigation is retained. P0 strict duplicate and exact-authority checks are unchanged. Real production-method regression fails on the prior producer and passes after the fix. The existing owning 609 receipt remains scoped to its recorded input; the changed projection and actual 49-test fixture require new runtime evidence. No assertion or CI classification is relaxed.

Read-only independent review found no new blocker; cross-primary/home candidate exchange is additionally covered. Full professional backend contract suite passed at `0ba4a7c3a71aafca0bb45d0cecd397244d4c9aa7`; full platform diagnostics remain failed as previously disclosed. Remote results still belong to the old ce1 candidate.

### Local original failure-chain closure

Clean source `7ee8bdadda4b4c8cf6869e77c98484044bf8abad` passed the registered acceptance fixture: **49 tests, 0 failures, 0 errors**, including the previously failing business_full scenario projection. Sealed artifact digest: `9e949a36cfdaf5cd1a2e1e5da3b387c22910e334306d1e3d8202f7b169b7fc52`; log `.runtime/ci-recovery/fixture-orm-7ee.log`. The selected owning ORM baseline also passed **609 tests**, receipt `.runtime/test-baseline/1795151533435929834/receipt.json`, with source/profile/image unchanged. These are local results, not remote gate success or a full-platform baseline.

This evidence-only follow-up changes no runtime/test inputs. Exact-head publication preflight and new full candidate CI remain required. Keep #950 Draft; the PR checks/body are the live post-freeze remote-result index, and failed broad platform diagnostics remain disclosed. The owner's independent re-review is still pending.

### Full candidate 70f: inherited test-only lint regression

The exact-head publication preflight and public guard passed. Full frontend run `44681625331` stopped in full ESLint before browser/managed ORM: `workspace_scenario_lifecycle_test.ts:1078` imported `requireReadiness` as a value used only by `Parameters<typeof requireReadiness>`. Blame identifies the synchronized base PR949 (`f2f7fd02`). P4 correction makes this a type-only import; the dynamically initialized composable, exact parameter type and all behavioral assertions are unchanged. Required validation: actual lifecycle test, full frontend lint and strict typecheck. Backend runtime and ORM test inputs are unchanged, so existing scoped 7ee 49/609 receipts are retained, not rewritten. Remote frontend/full coverage remain failed/pending and require a new exact-head candidate. No workflow exemption or lint-rule suppression.

The type-only correction passed the actual lifecycle target, full lint (zero errors) and strict typecheck (`.runtime/ci-recovery/readiness-type-import.log`). Independent read-only review confirmed type erasure preserves initialization order and assertions. All four 70f backend shards passed; logs explicitly collect CompanyRouteScopeCache 6, ProductPolicyFactAuthority 23 and ScenarioDirectInitialization 13. Coverage reconciliation correctly rejected the failed frontend producer (`.runtime/ci-recovery/remote-coverage-70f.log`). No coverage exemption is needed; a successful new frontend run is required.

### Review follow-up: stable action record identity (S2) and current scope (S3)

The af7 review showed that an action with multiple XMLIDs can return a different name from `get_external_id()`, bypassing string-only role action exclusions. The P0 authority producer now records the actual action model in both native and policy entries and closes all four executable buckets against policy references resolved to `(model, id)`. Display XMLID lookup does not decide authorization. Policy references that cannot resolve to an existing supported action produce explicit `ROLE_ACTION_POLICY_UNRESOLVED` denial; missing candidate model identity produces `ROLE_ACTION_IDENTITY_UNRESOLVED`. No-blocklist roles and genuine actionless scene declarations keep their existing behavior. A valid action without an XMLID remains allowed when its record is not blocked and existing ACL/group checks pass.

The true-method regression failed on af7 with 15 assertion failures and no runtime errors, then passed after the identity fix. It covers both discovery and published-policy admission, alternate XMLID choice, batch/singleton metadata failures, missing/invalid policy references, legal no-XMLID discovery and same-ID/different-model identity. Existing canonical cases remain. The top-level scope and gate table now reflect P0/P1/P4 and required frontend checks, closing the stale P4-only summary. This is a further P0 correction; existing af7 remote results remain af7 evidence, not success for the new candidate.

Before publishing the identity correction, af7 completed **all four required checks plus release_candidate_gate successfully**. Its complete browser release audit passed and the same remote fixture producer executed **49 tests, zero failures/errors**; coverage reconciliation passed. Logs: `.runtime/ci-recovery/remote-frontend-af7.log`, `.runtime/ci-recovery/remote-quality-af7.log`. This proves recovery of the original long CI chain at af7, while the independent S2 still requires this new correction and new candidate validation. The identity correction passes 30 publication tests plus 15/4 companion tests and 462 related navigation/metadata/consumer tests. The four bucket cases now also run the actual build→enabled-scene filter→route validator chain with bounded ORM facts; these remain pure contract tests, not real ORM evidence.
