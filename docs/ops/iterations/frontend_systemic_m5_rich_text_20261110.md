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

Pending.

## Result

Planned.
