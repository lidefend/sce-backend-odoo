# FE-SYSTEMIC-CONVERGENCE M5：富文本净化收敛

## Boundary

- Formal Product Layer: P0 platform kernel product
- Layer Target: generic safe rich-text rendering boundary
- Module: native form, professional fields, scene overview and form canvas
- Contract V2, ACL, backend semantics, database and deployment are excluded

## Baseline

Canonical scan:

- Root: `frontend/apps/web/src`
- Files containing `v-html`: 4
- Raw `v-html` occurrences: 4
- File/line occurrences including eslint comments: 15

Consumers:

- `components/professional-fields/ProfessionalBaseFieldControl.vue`
- `components/page/blocks/BlockRichTextOverview.vue`
- `components/template/FormSection.vue` (2 directives)
- `pages/contractForm/ContractFormNativeCanvas.vue`

## Plan

One semantic component will own the directive. It must expose distinct
`readonly` and `restricted` sanitization policies and preserve the existing
element identity and wrapping behavior of each consumer.

## Validation

- Raw `v-html` directives: 4 → 1, with the single retained directive in
  `components/content/ScRichText.vue`.
- Rich-text consumer wrappers: 5 calls across 4 former consumers.
- `make verify.frontend.rich_text.guard`: PASS, 4 tests.
- `make verify.frontend.rich_text.browser`: PASS, 10 checks; scripts, event
  attributes and `javascript:` links were removed, while safe HTTPS links and
  restricted tables were retained.
- `make verify.frontend.standard_form_composition.unit`: PASS, 124 cases.
- `make verify.frontend.overview_rich_text.unit`: PASS.
- `make ci.local.iteration`: PASS, 15 targets.
- Receipt:
  `.runtime/frontend-dev-validation/executions/20261109T202811Z-4184563-108146546/receipt.json`.

The two sanitizers now share one link-protocol helper. Absolute safe links are
validated before origin-dependent relative resolution, preventing valid HTTPS
links from being dropped in a host with no usable origin.

## Result

Pending commit, clean-HEAD iteration and affected 1440/390 page review.
