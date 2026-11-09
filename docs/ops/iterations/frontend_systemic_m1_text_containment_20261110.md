# FE-SYSTEMIC-CONVERGENCE M1：信息截断规则

## Boundary

- Formal Product Layer: P0 platform kernel product
- Layer Target: generic frontend information containment and title fallback
- Module: shared shell, work, list, form, relation and configuration surfaces
- Baseline: `71e9c70f43e16b85ec7f925c9a261894f4be4e50`
- Contract V2, ACL, backend business logic, database and deployment are excluded

## Confirmed Baseline

- 794 `.vue/.ts` files
- 46 files containing `white-space: nowrap`
- 131 `nowrap` declarations
- 27 files containing both `nowrap` and `ellipsis`

## Rule

- Record identity and money are never ellipsized.
- Business titles use no more than two lines.
- Record identity may exceed two lines until CD-20261110-01 supplies structured identity.
- Retained information-bearing ellipsis must have `title` or an accessible full-value fallback.
- Structural nowrap remains limited to hidden text, single-line controls, tabs, tags, toolbar
  totals, pagination and numeric alignment.

## Validation

- Raw nowrap files: 46 → 38.
- Raw nowrap declarations: 131 → 94.
- Files containing both nowrap and ellipsis: 27 → 12.
- After classifying the two structural configuration/toolbar files, information-bearing overlap
  files are 10, matching the M1 ceiling.
- Record identity/money protection: implemented in the affected list, home, relation, form and
  analysis surfaces; retained single-line identity/navigation labels have title or aria fallbacks.
