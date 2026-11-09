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

Canonical scan scope:

- root: `frontend/apps/web/src`
- extensions: `.vue`, `.ts`, `.css`
- excludes: `frontend/packages/ui`
- regex: `white-space\s*:\s*nowrap`

The reviewer count of 45 files / 130 declarations used the literal
`white-space: nowrap` spacing. The one-file/one-declaration delta is
`ScMoney.vue`, whose minified style uses `white-space:nowrap` without a space after
the colon.

## Rule

- Record identity and money are never ellipsized.
- Business titles use no more than two lines.
- Record identity may use up to four lines until CD-20261110-01 supplies structured identity.
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
- `make ci.local.iteration`: PASS, 12 required targets, receipt
  `.runtime/frontend-dev-validation/executions/20261109T185916Z-3665478-377874651/receipt.json`.
- Candidate build and browser carrier: product code `0217fb40035055e5e08cd30392af84a0116feb53`.
- Browser summary: `.runtime/m1-browser-0217fb400/summary.json`, SHA256
  `b13a578cc0916d86eb8196e77d2b84e3e38d53898a0b21df75cd487cdb040bce`.

### Golden Sample evidence

| Page | 1440 | 390 | SHA256 |
| --- | --- | --- | --- |
| WorkspaceHome | `desktop-workspace-home.png` | `mobile-workspace-home.png` | desktop `76d1e133…`, mobile `4a761572…` |
| My Work | `desktop-my-work.png` | `mobile-my-work.png` | desktop `0653edfa…`, mobile `6434d8d4…` |
| Payment Request form | `desktop-contract-form.png` | `mobile-contract-form.png` | desktop `49335fe0…`, mobile `bdfc1679…` |

Browser assertions for all six page/viewport combinations:

- visible truncated elements without title/aria fallback: `0`
- published app labels/topbar contexts without fallback: `0`
- clipped money values: `0`
- Console errors: `0`
- unexpected HTTP errors: `0`
- My Work card identity `scrollHeight <= clientHeight` for all rendered cards
