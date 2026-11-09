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
- `make verify.frontend.lint.src`: 0 errors (3 existing component warnings).
- `make verify.frontend.typecheck.strict`: PASS.
- `make verify.frontend.style_system.guard`: PASS.
- `make verify.frontend.page_pattern_reference_parity.unit`: 28 tests PASS.
- `make ci.local.iteration`: PASS, 11 required targets, receipt
  `.runtime/frontend-dev-validation/executions/20261109T185125Z-3625351-380095538/receipt.json`.
- Candidate build and browser carrier: product code `30ab6a8922bfab2757f0a871bf644adc443d8b8e`.
- Browser summary: `.runtime/m1-browser-30ab6a892/summary.json`, SHA256
  `87b215f1d3b2b97f8a84d78024520edb786b19dcf3131ea72d8952321aba3993`.

### Golden Sample evidence

| Page | 1440 | 390 | SHA256 |
| --- | --- | --- | --- |
| WorkspaceHome | `desktop-workspace-home.png` | `mobile-workspace-home.png` | desktop `49f02606…`, mobile `4a761572…` |
| My Work | `desktop-my-work.png` | `mobile-my-work.png` | desktop `afc174f6…`, mobile `d47b2b42…` |
| Payment Request form | `desktop-contract-form.png` | `mobile-contract-form.png` | desktop `b99003ca…`, mobile `bdfc1679…` |

Browser assertions for all six page/viewport combinations:

- visible truncated elements without title/aria fallback: `0`
- clipped money values: `0`
- Console errors: `0`
- unexpected HTTP errors: `0`
- My Work card identity `scrollHeight <= clientHeight` for all rendered cards
