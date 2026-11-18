# CLOSE-02：字段查询、排序与详情返回闭环

## 运行身份

- Goal: `CLOSE-02-FIELD-QUERY-SORT-DETAIL-20261118`
- Branch: `feature/close-02-field-query-sort-detail-20261118`
- Baseline: `7fe5dd7652204b3f0b678c07d51ae98d6e25b848`
- Worktree: `/home/lidefend/workspace/sce-backend-odoo-acceptance-scope-20261109`
- Writer: one writer; BE and FE are serial stages on one candidate and one PR.

## 边界声明

- Formal Product Layer: P0 platform mechanism.
- Layer Target: Unified Page Contract V2 Search projection, API.list field-domain/order execution, and shared ActionView query-state runtime.
- Module: `addons/smart_core`, `frontend/apps/web`, focused verification tools and this run record.
- Standard vs User-Specific: platform mechanism exercised by two existing construction-product entries.
- Why Here: native Search semantics, generic query execution and route-backed query state are platform concerns.
- Why Not Elsewhere: neither entry may receive model/action-specific frontend branches; P2/P3 configuration is not a repair carrier.
- Blast Radius: the project ledger and payment request list surfaces, field query execution, default order, route context and list pagination.
- Exclusions: `search_panel` unless present in the real contracts; autosave, renderer work, full-entry acceptance, deployment and product-delivery claims.

## 稳定基线门禁责任表

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| exact base/head identity | required | `make agent.run.resume` | always |
| owning module baseline coverage | required | registered `smart_core` ORM baseline/full affected family set | P0 query and contract behavior changes |
| existing affected test families | required | native search, V2 contract, API list, ActionView route/runtime targets selected after symbol mapping | changed behavior owns existing contracts |
| focused changed tests | required | new/updated non-zero tests | distinguish correct from pre-fix behavior |
| contract/schema/consumer | required | V2 schema/assembler/runtime and frontend contract guards | producer and consumer both change |
| frontend lint/type/build | required | registered frontend Make targets | TypeScript/Vue source changes |
| runtime/browser journey | required | governed two-entry browser entries | user-visible query and navigation behavior |
| remote required gates | required | exact-head PR checks | publication and merge |

## BE-CLOSE-02

Status: implementation and live samples complete; frontend handoff ready.

Acceptance:

- Effective Search-view field identity, input type, constraints and executable semantics are explicit in V2.
- Native field occurrences stay distinct; `domain`, `filter_domain` and `context` retain their native purposes.
- Self-bound expressions are evaluated only if the real entry contracts require them.
- Effective collection order is the same for first-page and later primary dataSource requests.
- Raw samples for both entries cover the effective identities, hits, valid zero results, a second page, total and scope preservation.

### BE handoff

- Product implementation commit: `cfb6829c76e9476d61b2abd329809da260ddfb31`
- Later unchanged product plus fixture/test carrier commits form the exact handoff HEAD recorded in `run.json`.
- Runtime: `sc-fe-r2-p1-01` / database `sc_frontend_acceptance` / served source `cfb6829c76e9476d61b2abd329809da260ddfb31`
- Actor: `fixture_role_config_admin`, `FE Company A` (`company_id=2`)
- Raw evidence: `.runtime/agent-runs/CLOSE-02-FIELD-QUERY-SORT-DETAIL-20261118/search_contract_samples/`
- Summary SHA-256: `a255046a5c29c538f81d959d51e2ff6c12239bfd7111c093f8b7ca452b1abf60`
- Validation SHA-256: `a947bc7fb766dbe9b60ea38cf0a14f1463b2aeae06582e46d00eb1dd65b89be6`

Project ledger:

- Menu/action/model: `smart_construction_core.menu_sc_project_project` / `action_sc_project_list` / `project.project`
- Runtime IDs: menu `382`, action `590`
- Effective Search view: `smart_construction_core.view_project_project_search_sc_business` (`viewId=1508`, `action_search_view`)
- Collection order: `write_date desc, id desc`
- Native field rows: 10. Text query `name ilike F` total `28`, page size `20`, second page `8`.
- Relation query `partner_id = 22` total `27`.
- Existing filter `filter_operation_direct` total `28`.
- Valid zero result total `0`; all returned query IDs remained inside the authoritative base population.

Payment request:

- Menu/action/model: `smart_construction_core.menu_sc_user_payment_apply` / `action_payment_request_user_payment_apply` / `payment.request`
- Runtime IDs: menu `560`, action `881`
- Effective Search view: `smart_construction_core.view_payment_request_search` (`viewId=1775`, `action_search_view`)
- Collection order: `created_time desc, name desc`
- Native field rows: 13. Text query `name ilike F` total `38`, page size `20`, second page `18`.
- Relation query `project_id = 1` total `37`.
- Fixed entry scope remains `business_category_id.code = finance.payment.apply.pay`; existing `type_pay` filter total `38`.
- Valid zero result total `0`; all returned query IDs remained inside the authoritative base population.

Contract findings:

- The two effective Search views contain ordinary native fields only; neither requires `self` in `filter_domain` or `context`, so the existing structured `api.data` domain path is sufficient.
- V2 now emits field identity/type/relation/enum, resolved default operator, available operators, occurrence identity/locator, parsed value domain/context, and explicit `query_mode`.
- V2 now canonicalizes the Search native identity to the schema's `actionId/viewId/viewXmlId` fields.
- Primary dataSource order prefers the effective collection view before the model Search default. `searchContract.defaults.order` and compatible top-level order fields are aligned to it.

Validation:

- `verify.smart_core.search_contract.close_02.unit`: 5 passed.
- `verify.native_action.search_view.unit`: 5 passed.
- `verify.native_action.contract.unit`: 10 passed.
- `verify.unified_page_contract.v2.runtime`: 23 + 147 passed.
- `verify.unified_page_contract.v2.schema`: 7 passed.
- Registered `smart_core` smoke/gate baseline receipt: 17 passed.
- `verify.native_action.search_view.orm`: 8 passed.
- `verify.native_action.contract.orm`: 6 passed.
- `acceptance.frontend.fixture_orm`: 49 passed.
- Live two-entry sample target: 52 assertions plus schema validation passed.
- `make ci.local.iteration`: passed with 34 required targets, 15 executed and 19 input-verified reuse; `notRunTargets=[]` and `registrationMissingTargets=[]`.
- Final incremental receipt: `.runtime/frontend-dev-validation/executions/20261118T174957Z-3125398-675281340/receipt.json` (`sha256=cadc44e0cb23088bc3a8af1f92b1f9b0d7c07a768168241af0e2fa921b43cfe1`).
- Final aggregate log: `.runtime/agent-runs/CLOSE-02-FIELD-QUERY-SORT-DETAIL-20261118/ci.local.iteration.final2.log` (`sha256=0ea81a4549e0027ae90a1e2eb3848018a558d683068e868dc5c00ac31029ca58`).

Sample identity recovery:

- A later current-HEAD replay attempt was correctly stopped by the governed acceptance health check because the running backend still reports source `71692e475e3123263ec67f967cc24412d2a0353f`, not the current verification-only HEAD.
- The collector initializes its output directory before login, so that stopped attempt cleared the untracked sample directory. The same collector was rerun with the HTTP transport and the recorded served SHA against the unchanged `sc_frontend_acceptance` runtime to restore the complete 29-file evidence set.
- The restored summary still reports 52 passed assertions, two schema-valid V2 contracts, the same two entry identities, totals, orders and second-page IDs. Its generated timestamp changed, so the summary hash is now `a255046a5c29c538f81d959d51e2ff6c12239bfd7111c093f8b7ca452b1abf60`; validation output remains byte-identical.
- `7e96761494697e8c5cdbba9fa93d6740cb050e26` differs from served `71692e475` only in the P4 statusbar guard and generated planning documents. Product inputs and assertions are unchanged, so the governed runtime evidence is carried forward with that explicit identity boundary.

Full `/smart_core` tag attempt:

- Result: `failed`, classified `validation_tool_defect` / prerequisite gap.
- The disposable runner installed only `smart_core`; 460 discovered tests included families requiring `smart_construction_core` XMLIDs and the isolated HTTP entry namespace.
- Observed failures were `External ID not found` for business capability groups and `NS_NAMESPACE_REQUIRED`, unrelated to the changed search/order symbols.
- Raw log: `.runtime/test-baseline/1795020194939088804/odoo.log`.

## FE-CLOSE-02

Status: implementation complete; lint, strict typecheck, focused runtime tests and production build passed. Browser journeys pending.

Acceptance:

- Root native search fields feed the existing field/operator/value control chain.
- Route state stores stable native field occurrence identity and typed values, including `false` and `0`.
- Detail return and page reconstruction restore the same confirmed query context.
- Any changed condition resets request offset, in-memory page and URL page together.

Implemented:

- Root `searchContract.fields` rows now feed the same field/operator/value controls as custom fields.
- Native occurrences retain their `occurrence_key`; duplicate native occurrences with the same field name stay distinct.
- Custom fields are merged after native fields and suppressed only when the same field already has a native declaration.
- Selection/boolean/integer/monetary/many2one input normalization preserves typed values, including legal `false` and `0`.
- A selected native declaration with a non-`domain` query mode fails closed as a contract gap instead of being evaluated in the frontend.
- The confirmed field condition is serialized in route query `field_filter` with stable occurrence identity, field, label, type, relation, operator and typed value.
- Route restoration rebuilds the active filter and its domain without relying on the component instance surviving.
- `field_filter` is carried through the existing activity runtime query used by detail return.
- `list_offset` is now part of the shared list-state patch and route-sync payload, so changing a query writes offset zero to the URL at the same time as memory and the next request.
- The URL page remains untouched when a detail return carries an unchanged confirmed query.

FE implementation validation:

- `verify.frontend.collection_view_semantics.unit`: passed, including typed `false`/`0`, invalid value, route serialization and current-page reset assertions.
- `verify.frontend.cross_model_action_navigation.unit`: passed; same-model actions retain `field_filter`, while cross-model entries clear it.
- `verify.frontend.typecheck.strict`: passed.
- `verify.frontend.lint.src`: passed with existing non-error warnings only.
- `verify.frontend.contract_basis.unit`: 15 passed, open defects `0`.
- `verify.frontend.build`: passed.

Browser journeys:

- Target: `verify.frontend.close_02.field_query.browser`
- Runtime: `sc-fe-r2-p1-01` / `sc_frontend_acceptance` / frontend `http://127.0.0.1:5175` / served source `71692e475e3123263ec67f967cc24412d2a0353f`
- Actor: `fixture_role_config_admin`, `FE Company A` (`company_id=2`)
- Summary: `.runtime/agent-runs/CLOSE-02-FIELD-QUERY-SORT-DETAIL-20261118/browser_journeys/summary.json`
- Summary SHA-256: `0fad6f81a82ff1d88f3d3cf2bcc7c778839f8e1c73957e9a7f9e563a2501d22c`
- Project ledger: text filter total `28`, existing filter total `28`, second page `8`; detail return and reload restored `field_filter`, order and `list_offset=20`; relation change and clear issued offset `0`.
- Payment request: text filter total `38`, existing filter total `38`, second page `18`; detail return and reload restored `field_filter`, order and `list_offset=20`; relation change and clear issued offset `0`, and the fixed finance entry scope remained active after clearing the user field condition.

## Results

BE-CLOSE-02 and FE-CLOSE-02 implementation, field semantics, route-state restoration, pagination reset and both bounded browser journeys are complete. Joint acceptance remains pending on clean candidate freeze, independent review, publication and exact-head required checks.

## Current-candidate CI diagnosis

PR #936 (`99afdff4b067a74ee73352d7fff41f6ba9e4d4ce`) reached the remote gates. `professional_quality_checks` failed before any CLOSE-02 product assertion because 13 blocked legacy ESM probes statically imported `playwright`; a clean quality runner intentionally has no frontend dependencies, so Node failed module linking before the first-import fail-closed guard could execute.

Classification: P4 `validation_tool_defect`.

Fix:

- The 13 blocked probes now load `playwright` with a dynamic import after the existing first-import `PROBE_TOOL_UNSUPPORTED` guard.
- The probe guard rejects any future external static import in a blocked ESM tool.
- `verify.local.dev.project_profile_write.unit`: 45 + 15 tests plus 11 static contract cases passed after the fix.
- The run registers `verify.frontend.delivery_hardening.guard` and the complete probe script/registry inputs selected by the incremental planner.

The failed `99afdff4` remote result remains recorded as superseded; no old-head success is carried to the replacement candidate.
