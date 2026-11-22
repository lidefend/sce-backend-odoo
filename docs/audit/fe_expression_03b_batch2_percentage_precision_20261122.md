# FE-EXPRESSION-03B Batch 2: Percentage and Numeric Precision

## Identity and boundary

- Baseline: `328ba916ee62215c6234c8b03757cffde18787c0`
- Branch: `feature/fe-expression-03b-batch2-percentage-precision-20261122`
- Formal Product Layer: P0 generic contract projection and frontend consumption
- Backend business model, ACL, workflow, database and persisted data modified: no
- New Renderer, Registry, Bundle, page engine or value runtime: no

## Objective

Preserve the already-declared percentage component identity and project declared
Float/Quantity `digits` into the normalized frontend contract. Use those facts for
read-only numeric presentation while retaining authoritative ORM values unchanged.

## Gate responsibility

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| exact base/head identity | required | git preflight | Always |
| owning Odoo module baseline | excluded | n/a | No model, service, permission, workflow or persisted behavior changes |
| native parser/contract tests | required | `verify.frontend.collection_view_semantics.unit` and contract-shape tests | Producer projection changes |
| focused frontend tests | required | business semantics, professional value, detail collection and row-cell targets | Consumer behavior changes |
| contract basis | required | `verify.frontend.contract_basis.enforce` | Declared semantics must have registered consumers |
| lint/type/build | required | registered frontend targets | TypeScript/Vue source changes |
| browser journey | required | affected component fixtures | User-visible formatting changes |
| remote required gates | required after publication | exact-head PR checks | Integration eligibility |

## Source findings

- `sc.value.percentage` is already declared, but collection projection currently
  retains only `sc.value.duration`.
- Native descriptors and tree-column occurrences currently expose `digits` only
  for monetary fields.
- Form, List and One2many metadata consume `digits` only for monetary fields.
- Generic non-integer formatting uses a fixed two decimal places.
- One2many has no component identity carrier for percentage fields and sends
  generic integer/float values through the fixed numeric formatter before the
  shared presenter.

## Acceptance

- A declared percentage renders as a percentage in Form, List, Kanban and
  One2many.
- Declared Float/Quantity scales are preserved across those read-only surfaces.
- Missing or invalid precision does not create a new business rule or mutate the
  stored/input value.
- Field names and labels never select percentage or precision semantics.
- Existing money, duration, status, relation, date and attachment behavior is
  unchanged.

## Implementation

- Float native descriptors and tree occurrences now preserve declared `digits`.
- Percentage occurrences resolve `sc.value.percentage` through
  `semantic_resolver`; no private widget-to-component mapping was added to the
  frontend.
- Contract V2 collection projection preserves percentage identity and declared
  digits.
- List, Kanban and One2many consume the shared declared-value presentation.
- One2many column identity does not leak widget semantics between occurrences of
  the same field.
- The professional percentage control and generic readonly numeric formatter
  consume the declared scale.
- Editable inputs and ORM write commands keep their existing value shape.
- The assembled page contract cache is invalidated deliberately: version `v100`
  and input digest `01581b30d785e2679b134f2a96d6074f97488cdea7fdeab65c7ac4b81aaa836c`.

## Validation

- `ci.local.iteration`: PASS with 17 affected targets.
- `verify.frontend.collection_view_semantics.unit`: PASS.
- `verify.frontend.contract_shape_projection.unit`: 16 cases PASS.
- `verify.frontend.business_semantics.unit`: PASS.
- `verify.frontend.professional_business_value.unit`: PASS; actual component
  browser output covers percentage and Float precision across Form/List/Kanban.
- `verify.frontend.professional_detail_collection.unit`: PASS.
- `verify.frontend.collection_row_cell.unit`: PASS.
- `verify.frontend.canonical_form_presenter.unit`: PASS.
- `verify.semantic.registry.lint`: PASS.
- `verify.unified_page_contract.v2.assembler`: PASS.
- `verify.frontend.contract_basis.enforce`: PASS, 0 open defects.
- Lint and strict TypeScript: PASS.
- `verify.frontend.build`: PASS, 5419 modules.
- `ci.delivery.freeze.prepare`: PASS.

Artifact SHA256:
`46e8263915421ea4ca96c5eccedc9516d5e9fc301576817fdf07ce04e593ce30`.
This is dirty-worktree build evidence until a clean candidate is committed.

## Rollback

Revert this batch's metadata, metadata projection, frontend consumers and focused
tests. No database, service or persisted value requires rollback.
