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
- Summary SHA-256: `ae938d7ff2b79c35dc593de6d01d0fef1bbde58ad4876f31fc4de4486363c6ca`
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

Full `/smart_core` tag attempt:

- Result: `failed`, classified `validation_tool_defect` / prerequisite gap.
- The disposable runner installed only `smart_core`; 460 discovered tests included families requiring `smart_construction_core` XMLIDs and the isolated HTTP entry namespace.
- Observed failures were `External ID not found` for business capability groups and `NS_NAMESPACE_REQUIRED`, unrelated to the changed search/order symbols.
- Raw log: `.runtime/test-baseline/1795020194939088804/odoo.log`.

## FE-CLOSE-02

Status: active; backend handoff accepted on the same delivery branch.

Acceptance:

- Root native search fields feed the existing field/operator/value control chain.
- Route state stores stable native field occurrence identity and typed values, including `false` and `0`.
- Detail return and page reconstruction restore the same confirmed query context.
- Any changed condition resets request offset, in-memory page and URL page together.

## Results

Initial run registration complete. BE-CLOSE-02 closed its implementation and live-sample stage. FE-CLOSE-02 has started; joint browser acceptance remains pending.
