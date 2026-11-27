# FE-S06 / FE-S07 independent import lifecycle evidence

Candidate base: PR #1019 source head
`ca2e773dfebe0d9e60d366ed3a1bc8f240bf9cca`.

This branch is independent. It must not modify the product writer's source worktree
or claim FC-06 complete before FC-05 handling-chain closure.

## Required discriminating scenarios

- close during inspect/validate aborts the request and resolves the caller with no import;
- component unmount aborts outstanding requests and ignores late callbacks;
- company/context epoch change aborts and clears draft, mapping, result and busy state;
- execute remains non-dismissible while the write is in flight, then restores busy state;
- a late inspect/validate/execute result from an invalidated session cannot change the UI;
- the abandoned `pickImportFile` and direct preview-confirm executor have no production consumers before removal.

## Pending-candidate result

- `make ci.local.iteration`: 8 targets, 323 non-zero tests, 5 static checks,
  `unmapped=0`, `not_run=0`, `blocked=0`;
- `make verify.frontend.build ENV=dev ENV_FILE=/home/lidefend/workspace/sce-backend-odoo/.env.dev`:
  passed with fingerprint
  `b44677c3a7d062d914c24e04e4a6380f54f19c2705c6573bf256b8fac1cc53b9`;
- repository-wide reference search found no consumers of `pickImportFile`,
  `executeActionViewCollectionImport` or `CollectionImportSummary`; the obsolete
  exports are removed and a regression guard prevents restoring them in the
  capability runtime.

Browser role/company journeys are still `not_run`. This slice does not prove
FC-06 or the 143-entry matrix complete; FC-05 handling-chain closure remains a
separate prerequisite before FC-06 closure.
