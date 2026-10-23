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
official TDesign descriptions composition. The official component's table body
stays `width:100%`, so the sparse fact became a full-body-width label/value
table and left a large unused band. This is a rendering-consumption defect, not
a missing field, permission or product contract change.

## Implementation

- Replace the page-header flex/fixed-basis layout with a three-column grid on
  desktop and a two-column compact grid under `860px`: identity owns the first
  row; status and actions share the second row.
- Make the contract-form status/statusbar wrappers flex-wrap and give the edit
  selector an intrinsic `14rem` basis only when it is actually rendered.
- Mark structural `header` field batches as compact summaries. The official
  descriptions adapter exposes a compact mode that sizes its own root and table
  body by content instead of stretching a sparse row across the form body.
- Keep the compact summary and status containers out of `inline-size`
  containment while they are being content-sized.
- Keep vendor-specific table selectors inside the `ScDescriptions` adapter. No
  `:deep(.t-*)` coupling is added to `FormSection` or the page.
- Make `verify.frontend.playwright_vendor_coupling.guard` a prerequisite of the
  immediate `verify.frontend.product_page_header.unit` gate, so an impermissible
  browser probe is rejected before candidate deployment and Quick.
- Preserve all declared fields, visibility, status, action settlement and
  project workflow semantics. No `project.project` special case is added.

## Verification

- `make verify.frontend.product_page_header.unit`: PASS, 75 Python tests plus
  28 model cases and the registered adapter/component checks; its early vendor
  coupling prerequisite also passes.
- `make verify.frontend.page_pattern_reference_parity.unit`: PASS, 15 + 13
  tests, 17 surfaces and 67 ledger entries.
- `make verify.frontend.primitive_adapter.unit`: PASS, 41 tests and 46
  components.
- `make verify.frontend.style_system.guard`: PASS, zero hard-coded color refs.
- `make verify.frontend.build`: PASS.
- Governed `verify.frontend.product_page_header.browser` against the daily
  project record: PASS, one target, zero mutations, zero console/page/HTTP
  errors, zero horizontal overflow.

The same record (`project.project/15`, login `demo_full`) was measured before
and after:

| Viewport | Header before | Header after | Top summary before | Top summary after |
| --- | ---: | ---: | ---: | ---: |
| 1440x1100 | 53px, status track 506px | 53px, status track 288px | 1145px | 142px |
| 1280x800 | 85px | 53px | 1001px | 142px |
| 768x1024 | 139px | 93px | 681px | 142px |
| 390x844 | 197px | 123px | 303px | 142px |

At 390px the header now has two row bands rather than three; identity occupies
the first row and status/actions share the second. The content-top approval fact
no longer occupies the complete body width. Final screenshots and geometry are
under `.runtime/project-form-presentation/candidate-d11e1311/`; baseline
screenshots are under
`.runtime/project-form-presentation/content-header-descriptions/`.

`make verify.form_container_presentation.guard` remains blocked by two
pre-existing findings outside this batch: unconsumed
`alert/alert-*` vocabulary and a projection baseline leaf span of `12` where the
guard expects `24`. This batch does not modify that projection or vocabulary;
the finding is recorded rather than hidden or waived.

## Validation-order correction

The first candidate reached Quick before its browser probe was checked for
vendor-internal coupling, and Quick correctly rejected it. The ordering defect
was not waived by changing the baseline. Instead, the vendor guard is now a
dependency of the product-header unit gate, so the same class of defect is
reported immediately after a component/test change.

## Rollback

Revert the topic commit. The change has no schema, data migration, ACL or
runtime-configuration rollback requirement.

## Next exact step

Commit the verification-only delta with an impact note that product code is
unchanged from the measured candidate, then run the exact-head Quick and publish
the GitHub PR.
