# PLATFORM-CAPABILITY-STUDIO-NAV-ORDER-20261115

## Candidate

- Baseline: `c6d8e7afd78f00c9937e56edbe84aca778aaa324`
- Branch: `audit/platform-capability-studio-01-20261115`
- Source fix: `fix/product-configuration-center-order-20261115@3ff05f82759f181323a8e0d6e7ccd43e7956a45e`
- Stage: implementation complete and verified

## Scope

- Integrate the reviewed navigation center ordering fix into the capability
  studio release branch as an independent product commit.
- Keep the capability catalog audit commit separate from navigation behavior.

## Exclusions

- No capability catalog or scene editor implementation.
- No permission, route, action, business-data or release change.
- No deployment or merge.

## Integration Method

Repository policy forbids raw merge and cherry-pick. The reviewed source patch was
therefore reapplied to the current governed branch and is validated again here.

## Verification

- `verify.scenario.center_projection.guard`: PASS, 8 tests.
- `verify.nav01.native_authority.unit`: PASS, 93 tests.
- `make ci.local.iteration`: PASS. The affected plan executed agent ledger,
  navigation publication consumers and scenario center projection targets.

## Release Composition

The release candidate branch now contains two independently reviewable outcomes:

1. Capability catalog and scene governance audit documentation.
2. Product configuration center ordering behavior.

The original navigation fix commit remains the source evidence:
`3ff05f82759f181323a8e0d6e7ccd43e7956a45e`.
