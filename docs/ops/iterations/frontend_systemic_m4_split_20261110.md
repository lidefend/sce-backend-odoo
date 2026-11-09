# FE-SYSTEMIC-CONVERGENCE M4：split 使用分类与语义收口

## Boundary

- Formal Product Layer: P0 platform kernel product
- Layer Target: generic frontend parsing and record-identity boundaries
- Module: contract consumers, route parsers, formatters and relationship display
- Contract V2, ACL, backend semantics, database and deployment are excluded

## Baseline

Canonical scan:

- Root: `frontend/apps/web/src`
- Extensions: `.vue`, `.ts`
- Pattern: `\.split\s*\(`
- Files: 39
- Occurrences: 61

## Classification

All 61 occurrences across 39 files are registered in
`docs/architecture/split_usage_allowlist.json`.

| Mechanism | Occurrences | Files |
| --- | ---: | ---: |
| Declared token list | 16 | 10 |
| Route protocol | 14 | 7 |
| Suggested-action payload | 4 | 1 |
| Contract sort/view tokens | 3 | 1 |
| Locale/label format | 3 | 1 |
| Path identifier | 3 | 3 |
| Contract error protocol | 2 | 2 |
| Declared class tokens | 2 | 1 |
| Route/cache identifier | 2 | 1 |
| Stable identifier normalization | 2 | 2 |
| Whitespace token list | 2 | 2 |
| Other single-purpose protocol formats | 9 | 9 |

The only business-semantic inference is
`app/presentation/productMyWorkPresentation.ts`, which removes a known amount
text from the backend display string. It remains as the single explicit
contract exception bound to `CD-20261110-01`; no additional record-identity
split is allowed.

## Validation

- `make verify.frontend.split_usage.guard`: PASS.
- Split guard unit tests: 6 passed.
- Registered set: 39 files / 61 occurrences / 19 mechanisms.
- `make verify.frontend.dev.incremental.unit`: 103 passed.
- `make ci.local.iteration`: PASS, 4 targets.
- Receipt:
  `.runtime/frontend-dev-validation/executions/20261109T200918Z-4078731-578951459/receipt.json`.

## Result

Completed as a P4/P0 ownership audit. No `frontend/apps/web/src` product source
changed, so the M3 1440/390 browser evidence remains valid by input comparison:
`.runtime/m3-browser-204baf9/summary.json`, SHA-256
`b111bb5c8dfd73d5481e5e037350c32d6ab730b3e2085ec78afdf79e3c0e34d5`.
