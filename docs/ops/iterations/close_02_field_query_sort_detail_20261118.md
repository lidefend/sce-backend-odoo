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

Status: active.

Acceptance:

- Effective Search-view field identity, input type, constraints and executable semantics are explicit in V2.
- Native field occurrences stay distinct; `domain`, `filter_domain` and `context` retain their native purposes.
- Self-bound expressions are evaluated only if the real entry contracts require them.
- Effective collection order is the same for first-page and later primary dataSource requests.
- Raw samples for both entries cover the effective identities, hits, valid zero results, a second page, total and scope preservation.

## FE-CLOSE-02

Status: planned; begins after the backend candidate and raw samples are frozen.

Acceptance:

- Root native search fields feed the existing field/operator/value control chain.
- Route state stores stable native field occurrence identity and typed values, including `false` and `0`.
- Detail return and page reconstruction restore the same confirmed query context.
- Any changed condition resets request offset, in-memory page and URL page together.

## Results

Initial run registration complete. No product validation has run yet.
