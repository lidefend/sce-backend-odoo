# FE-EXPRESSION-03B P1-A / P1-B

- Baseline: `a408177cde91a6435d5e57a63c50dc35c2e5ce14`
- Branch: `feature/fe-expression-03b-p1a-p1b-20261122`
- Stage identity: HEAD plus the explicit dirty scope recorded in
  `.agent/runs/FE-EXPRESSION-03B-P1A-P1B-20261122/run.json`
- Status: active

## Purpose

P1-A preserves the distinction between an absent payment-settlement amount and
a legitimate zero in the payment request settlement introduction dialog. P1-B
is a read-only diagnosis of whether list aggregates carry authoritative
currency identity for their actual aggregate scope.

## Responsibility

- Formal Product Layer: P0
- Layer Target: generic frontend monetary-value presentation
- Module: `frontend/apps/web`
- Standard vs User-Specific: platform generic frontend runtime
- Why here: the dialog is consuming already declared amount and currency
  semantics, but currently rewrites absent values and replaces a zero historical
  applied amount with a different field.
- Why not elsewhere: there is no missing backend rule; contract, ACL, workflow
  and ORM behavior are excluded.
- Blast radius: the read-only settlement history/search presentation and one
  focused component test. Confirmation payloads and writes remain unchanged.

## Gate responsibility

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| exact base/head identity | required | Git preflight | Always |
| owning module baseline | excluded | none | No Odoo module behavior changes |
| existing affected tests | required | `verify.frontend.professional_detail_collection.unit` | Owns settlement dialog consumer |
| focused changed tests | required | `verify.frontend.payment_settlement_introduce.amount.unit` | Zero, absent, positive and negative amounts |
| contract/schema consumer | required | `verify.frontend.contract_basis.enforce` | Frontend contract consumption |
| frontend lint/type/build | required | registered frontend targets | Vue/TypeScript source changed |
| runtime/browser journey | required | affected dialog component and payment-request page | User-visible behavior |
| remote required gates | required after publication | exact-head PR checks | Integration acceptance |

## Results

P1-A implementation is present in the working candidate. The focused real-Vue
component test first failed against the pre-fix source because the legal zero
settlement amount was absent from the DOM; after the fix it passes at both 1440
and 390 with zero, absent, positive and negative values, and zero introduction
write requests.

The focused result is `12` cases, browser `147.0.7727.15`, `0` console errors.
The original failure log is retained at
`.runtime/agent-runs/FE-EXPRESSION-03B-P1A-P1B-20261122/logs/payment-settlement-amount-product-prefix-failure.log`.

Local validation on the unfrozen candidate:

| Check | Result |
| --- | --- |
| Focused real Vue component | PASS, 12 cases, 1440 and 390 |
| Affected professional detail family | PASS |
| Contract basis | PASS, `open_defects=0` |
| Frontend lint | PASS, 0 errors |
| Strict typecheck | PASS |
| Acceptance release build | PASS, temporary Vite chunk-size warnings only |
| `ci.local.iteration` | PASS |
| `ci.delivery.freeze.prepare` | PASS |

The first dirty-candidate release build produced
`frontend_build_sha256=9a22f3468cadd939e849cb4cf526c41d48461776518deb63d77d63cb9365f940`.
Its `build-info.json` reported parent `a408177c`, so it is retained only as a
pre-freeze build check and is not cited as exact-HEAD evidence.

## P1-B diagnosis

P1-B is complete as a read-only source diagnosis. No product source was changed.

### Aggregate scope and currency authority

The backend is more complete than the audit report assumed:

- `addons/smart_core/handlers/api_data.py:835` builds semantic aggregates for
  the complete filtered `domain`.
- `sum` is computed with the unpaged domain; `page_sum` is computed by adding
  the page record ids to that same domain.
- For monetary semantics, the backend groups the complete filtered domain by
  the declared `currency_field`. It returns `aggregate: none` with a stable
  reason code when the currency field is missing, unreadable, unverifiable, or
  when the complete scope contains more than one currency.
- A valid same-currency response includes `currency_field` and the authoritative
  `currency_id`; the declared precision is also carried.
- Grouped aggregates use the same mechanism over each group's complete domain.

Existing source tests prove an unpaged `sum`, page-scoped `page_sum`, returned
`currency_id`, and fail-closed mixed-currency behavior in
`addons/smart_core/tests/test_api_data_list_param_boundaries.py`. The file's
pure unit run passed `38/38`; it uses stubs and does not write a database.

### Frontend consumption gap

`frontend/apps/web/src/pages/ListPage.vue:1999` still selects the first page row
that has a currency value and applies that label to the server aggregate. This
does not prove the aggregate currency identity and ignores the returned
`currency_id`.

The current result is therefore:

| Question | Finding |
| --- | --- |
| Is `sum` page-scoped? | No. It covers the complete filtered domain. |
| Is `page_sum` page-scoped? | Yes. It is the current page subset. |
| Are records only a page? | Yes. The list query has the declared limit and offset. |
| Does the backend provide currency identity? | Yes: validated `currency_field` plus `currency_id`. |
| Does it fail closed on mixed currencies? | Yes, for the complete aggregate domain. |
| Does it group totals by currency? | No. Mixed-currency totals become unavailable. |
| Is a P0 contract change required for correctness? | No source gap is proven. |
| What remains broken? | The frontend does not consume the backend currency identity. |

### Next minimum candidate

A later frontend P1-B implementation should:

1. Require `aggregate === "sum"` for a monetary aggregate.
2. Require a valid `currency_id` returned with the aggregate.
3. Resolve the currency relation label only from a page/group row carrying that
   same id; otherwise hide the aggregate.
4. Never use the first row or infer full-scope currency equality from the page.
5. Test same-currency, mixed-currency, missing `currency_id`, and page/outside-page
   currency differences.

A P0 enhancement to include the currency relation name in the aggregate payload
would make label resolution independent of page rows, but it is not required to
close the correctness defect. A mixed-currency total must remain unavailable.

## Delivery boundary

This batch implements P1-A only. P1-B remains a read-only diagnosis and its
recommended frontend consumption change belongs to a later independently
reviewable candidate.
