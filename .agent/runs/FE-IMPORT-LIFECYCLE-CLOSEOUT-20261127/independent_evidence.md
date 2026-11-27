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

## Clean exact-head result

Commit `f8fcce8616c30780e07b87a8815fa4a19fd91356` passed:

- clean exact-head `make ci.local.iteration`: 7 executed targets, 2 reused,
  42 non-zero tests, 5 static checks, no unmapped/not-run/blocked target;
- production build from the same source revision, fingerprint
  `cd2a673e7e21a7ee3ab6b3555fc76c15c190cd925916725d415dabc4c67f8a74`;
- no remote source-branch mutation and no browser journey in this independent slice.

## r4 direct stack

PR #1019 advanced to `e4a4df12cf65137c298863f576390ca3684076c6`. A fresh r4
branch was created directly from that full head and the import-only patch was
replayed on top. This avoids rewriting source history and makes the eventual
stack PR fast-forward-compatible once the import slice is validated.

The direct r4 import commit `0de4566d293796e6589d6e36eccb58e35097ba59` passed
exact-head local iteration (6 executed, 3 reused, 24 non-zero tests, 5 static
checks) and production build fingerprint
`80828eab2f196b83053f1655b19cb18489825a4db2090e6c294f2b9e02ba3219`.
