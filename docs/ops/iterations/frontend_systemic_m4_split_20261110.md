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

Pending audit of protocol syntax, declared contract parsing, technical path/query
parsing, display-format parsing, MIME/token parsing and record identity.

Known semantic-risk candidate:

- `app/presentation/productMyWorkPresentation.ts` splits a display identity on
  whitespace plus `/`. This must be closed as CD-20261110-01 unless the runtime
  contract already supplies structured identity.

## Validation

Pending.

## Result

Planned.
