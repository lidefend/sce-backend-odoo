# Frontend Form Information Architecture Improvement V1

## Result

This topic replaces full-record rendering with a handler-oriented business-document projection. The platform fails closed, the product layer owns document recipes, and customer variation no longer requires copied pages.

## Platform rules

- Ordinary forms hide audit, migration, carrier, provenance, and system-maintenance fields by default.
- Provenance, system-processing, and history-check sections remain audit metadata and are excluded from ordinary surfaces.
- A field renders once even when native layout and structure contracts overlap.
- Readonly pages render a six-fact business summary followed by non-empty business sections.
- Optional empty values and empty sections collapse; boolean `false` and numeric `0` remain meaningful facts.
- Narrative and evidence have separate presentation roles.
- The designer can still configure internal fields; fail-closed behavior applies to the ordinary runtime surface.

## Product recipes

- Construction contract: overview, project/counterparty, amount/dates, narrative, evidence.
- Payment request: overview, project/contract, amount, payment accounts, narrative, evidence.
- Settlement: overview, project/contract, category/period, amount/details, narrative, evidence.
- Payment-request payee and payer sections are combined as one payment-account section.

## Acceptance

Isolated database: `sc_frontend_acceptance`.

| Form | Viewports | Sections | Fields | Internal sections | Duplicate fields | Overflow |
|---|---:|---:|---:|---:|---:|---:|
| Construction contract | 1440 / 390 | 3 | 9 | 0 | 0 | 0 |
| Settlement | 1440 / 390 | 3 | 9 | 0 | 0 | 0 |
| Payment request | 1440 / 390 | 6 | 12 | 0 | 0 | 0 |

Five missing-value indicators remain on the contract because they represent required or key facts. Ordinary optional empty values collapse.

Evidence: `artifacts/frontend-form-information-architecture/browser-final`.

## Boundary

No permission, approval, route, business fact, or save API was changed. Internal audit facts remain available under the backend `internalAudit` contract for auditors and administrators.
