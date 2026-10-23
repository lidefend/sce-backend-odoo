# Project Form Header Density (2026-10-23)

## Batch boundary

- Batch: P0 shared product-header presentation correction.
- Objective: remove unused header width and excess row bands from project forms
  on desktop and narrow viewports without changing product semantics.
- Formal product layer: P0 platform kernel product.
- Layer target: shared `ProductPageHeader` presentation and the contract-form
  header consumer.
- Standard vs user-specific: platform-generic presentation mechanism.
- Why here: the project form symptom is produced by a shared header component
  reserving an empty status column and stacking identity, status and actions.
- Why not elsewhere: the batch does not change project fields, model semantics,
  contracts, permissions, actions, route authority or low-code configuration.
- Blast radius: every direct consumer of the shared page header and the
  contract-form header's status/action placement.

## Baseline evidence

Runtime: `http://1.95.85.92:18081/t/demo`, database `sc_demo`, login
`demo_full`, project record `project.project/15`.

| Viewport | Header height | Header layout | Observed issue |
| --- | ---: | --- | --- |
| 1440x1100 | 53px | flex row | title, status and actions share a row, but the status track reserves 506px |
| 1280x800 | 85px | flex row with wrapped identity | title and status wrap because the status track consumes fixed flex basis |
| 768x1024 | 139px | flex column | identity, status and actions occupy three separate rows |
| 390x844 | 197px | flex column | identity, status and actions occupy three separate rows with visible unused space |

The live page had no console errors, failed HTTP responses or horizontal
overflow. Baseline screenshots and geometry are under
`.runtime/project-form-presentation/header-baseline/`.

## Root cause

`ProductPageHeader.vue` gives the status slot a fixed `22rem` desktop flex basis
and changes the whole header to a vertical stack at `860px`. In the
contract-form header, `record-header-status` and the native statusbar are grid
containers whose second column remains reserved when the edit selector is not
rendered in read-only mode. The empty status column therefore consumes width on
desktop and becomes a visible unused row on narrow screens.

The content-area top row was a separate shared-renderer defect. The project
form's effective contract declares a structural `header` container with two
columns; the only visible field, `sc_approval_state` (`立项审批`), retains its
declared `span=12`. `FormSection` renders sparse readonly facts through the
official TDesign descriptions composition. TDesign expands the final item in a
partial descriptions row to fill the table, so a single declared half-row fact
became a full-body-width label/value table and left a large unused band. This is
a rendering-consumption defect, not a missing field, permission or product
contract change.

## Implementation

- Replace the page-header flex/fixed-basis layout with a three-column grid on
  desktop and a two-column compact grid under `860px`: identity owns the first
  row; status and actions share the second row.
- Make the contract-form status/statusbar wrappers flex-wrap and give the edit
  selector an intrinsic `14rem` basis only when it is actually rendered.
- Mark structural `header` field batches as compact summaries. The official
  descriptions composition is content-sized within the header instead of
  stretching a sparse row across the complete form body.
- Preserve all declared fields, visibility, status, action settlement and
  project workflow semantics. No `project.project` special case is added.

## Verification

- `make verify.frontend.product_page_header.unit`: PASS, 75 Python tests plus
  28 model cases and the registered adapter/component checks.
- `make verify.frontend.page_pattern_reference_parity.unit`: PASS, 15 + 13
  tests, 17 surfaces and 67 ledger entries.
- `make verify.frontend.primitive_adapter.unit`: PASS, 41 tests and 46
  components.
- `make verify.frontend.style_system.guard`: PASS, zero hard-coded color refs.
- `make verify.frontend.build`: PASS.
- Live project-form geometry before/after verification remains pending.

## Rollback

Revert the topic commit. The change has no schema, data migration, ACL or
runtime-configuration rollback requirement.

## Next exact step

Commit the candidate, serve the exact candidate bundle on the governed daily
runtime, and compare header and content-summary geometry against the baseline.
