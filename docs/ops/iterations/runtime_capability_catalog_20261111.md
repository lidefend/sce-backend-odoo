# Runtime capability catalog (2026-11-11)

## Boundary

This batch introduces one read-only projection over installed Odoo capability
facts:

- `ir.ui.menu`;
- `ir.actions.*`;
- `res.groups`;
- `ir.model.data`.

The projection produces candidate capability identities and native metadata.
It does not publish, enable, grant, route or compose anything.

The existing `ProductPolicyCatalogSyncService` will consume this projection so
module installation exposes candidates through one scanner rather than a
second menu traversal in each product layer.

## Exclusions

- No product publication or release state change.
- No tenant composition or role grant.
- No route field.
- No frontend or scenario composition change.
- No runtime write, migration, deployment, PR or remote mutation.

## Projection

`RuntimeCapabilityCatalogService` produces one row per active action-bearing
native menu leaf:

- stable entry identity: `native.entry.<menu_xmlid>.<action_xmlid>`;
- native menu/action IDs as runtime handles;
- owner module, menu path and sequence;
- action model, `res_model` and view modes;
- native menu/action group XMLIDs;
- optional labels from native records.

It contains no route, release state, tenant state or user access verdict.

`ProductPolicyCatalogSyncService` now delegates menu/action discovery to this
projection. Product publication remains a separate later selection step; every
installed candidate is not automatically published.

## Validation

- `make verify.runtime_capability_catalog.unit`: 5 tests passed.
- `make verify.backend.navigation_delivery.unit`: 73 tests passed.
- `make verify.capability.identity_boundary.unit`: 6 tests passed.
- `make verify.product_menu_release_gate.contract.unit`: 9 tests passed.
- `make verify.frontend.dev.incremental.unit`: 115 tests passed.

## Runtime observation

The local persistent database produced a 274-entry candidate capability
catalog across 11 native groups with four scene-bound candidates. The same
result was returned for the standard and preview catalog queries:

- artifact:
  `artifacts/backend/platform_release_policy_runtime_probe_after_catalog.json`
- artifact SHA-256:
  `f2975572443af8d1c8aab79ae305edf60eda7894aec44315a5feb7c9616d5b75`

The aggregate runtime probe still reports four failures in its
`no_native_delivery` and `native_subset_delivery` assertions. Those calls
provide an empty native tree together with `exposure_policy_declared=true`, so
`MenuService` intentionally authorizes from the request user's ACL-visible
facts instead of the empty input tree. The probe assertion therefore does not
exercise the path its name claims. That delivery path does not use this batch's
capability-catalog projection; classify it as an existing validation/baseline
issue and do not count the aggregate probe as passed.
