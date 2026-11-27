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

## Restack rebind

PR #1019 advanced to `bd7a2c79435e36f9d752570db170cba8e5ee7cc0` after the
first import validation. The import changes were replayed onto that full HEAD in
the same independent worktree. The only replay conflict was the generated
component-driver inventory, which was regenerated through its governed target.
The restacked candidate must be validated again before publication.

## r2 clean exact-head result

Commit `3e5c1b9153874bf1f6ff3d6f5dbacf5498a7034b` passed:

- `make ci.local.iteration`: 9 executed targets, 3 test targets, 341 non-zero
  tests, 5 static checks, no unmapped/not-run/blocked target;
- production build from the same source revision, fingerprint
  `49b2a04814cc1a98486ceef75a3b797c7b55691664dac7a3625ab3b04ed1cda5`.

## Independent review at source head bd7a2c79

PR #1019 at `bd7a2c79435e36f9d752570db170cba8e5ee7cc0` is blocked by
`public_guard`: blob `1582beb6a28d` for
`docs/audit/verify_system_closeout_01_r2a/actual_execution_facts.json` matches
`MOBILE_PHONE_PATTERN` because workflow/artifact numeric identifiers look like
phone numbers. The guard itself records `sensitive_values_recorded=false`.
`wait_for_fact_checks` and `merge_policy_gate` fail transitively. Classify this as
a P4 validation-tool false positive, not an import lifecycle product defect.

## Stable-base r3 restack

PR #1019 stabilized at `fb45f14a079e4f5373198402727ac25a943c9af0` with all
checks completed. The r2 import candidate was replayed onto that exact full HEAD.
Again, only the generated component-driver inventory conflicted and was
regenerated through its governed target. The r3 branch requires a final
exact-head validation before handoff.

## r3 clean exact-head result

Commit `50faa32bb171e7c1e87e2fc5ab39369840a4d4c7` passed:

- `make ci.local.iteration`: 9 executed targets, 3 test targets, 341 non-zero
  tests, 5 static checks, no unmapped/not-run/blocked target;
- production build from the same source revision, fingerprint
  `afac180ee125ec246d9af68ff7eb154dae412c836cfba8d6fbf8d5981771407e`.

This is ready for product-writer handoff once PR #1019's `public_guard`
false-positive blocker is resolved.

## Source sync e4a4df12

PR #1019 advanced to `e4a4df12cf65137c298863f576390ca3684076c6` with action
budget changes. None touch import files. The source delta was replayed onto the
existing r3 branch, and the generated inventory was regenerated. PR #1023 should
be updated in place after the synchronized tree passes exact-head validation.

The synchronized commit `823d2ebaaa280d268bb00773e9ad0687f9a54195` passed
16 executed local targets, 187 non-zero tests and 5 static checks, including the
backend/contract targets introduced by the source branch. Production build
fingerprint:
`394d4339882f7afd7bcc60248da662175014fb43c33b1d1808ed2e392c318bef`.
