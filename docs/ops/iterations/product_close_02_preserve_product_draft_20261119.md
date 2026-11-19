# PRODUCT-CLOSE-02 Preserve Product Draft Facts

Status: verification pending independent review

Base: `810632f57e736823eed3e555ad45e2c6f43e27b0`

Branch: `fix/product-close-02-preserve-product-draft`

## Product result

After an administrator selects capabilities, edits centers, sequence and
roles, synchronizing native product sources preserves those maintained draft
facts. Newly discovered catalog entries remain in the platform catalog until
explicitly admitted, and synchronization never publishes.

## Layer and scope

| Item | Declaration |
| --- | --- |
| Formal Product Layer | P0 platform kernel product |
| Layer Target | `smart_core` product-policy catalog synchronization and its generic frontend consumer |
| Standard vs User-Specific | Platform mechanism |
| Why Here | Sync merge behavior, release-operator actions and generic contract consumption are platform mechanisms |
| Why Not Elsewhere | Frontend cannot restore lost facts; P1 supplies source/default facts; sync cannot publish or execute catalog admission |
| Blast Radius | One submitted `sc.product.policy` draft and the release-operator sync action readback |

## Exclusions

- ORM, Odoo-native capability and module baselines.
- Module upgrade, environment rebuild, browser matrix and deployment.
- Automatic catalog admission, source migration or publication.
- SCENE-CLOSE-02 scenario-version convergence.

## Required validation responsibility

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| Exact base/head identity | required | `make agent.run.resume` | Always required |
| Owning-module ORM baseline | excluded | none | Owner direction limits this run to contract logic |
| Existing documented sync family | required | `verify.runtime_capability_catalog.unit` | Owns the current sync producer |
| Focused changed behavior | required | `verify.runtime_capability_catalog.unit` | Preserve/no-expand/fail-closed/idempotent cases |
| Capability and center contract families | required | identity and product-center unit targets | Adjacent producer invariants |
| Frontend contract/lint/type | required after handoff | existing frontend targets | Decoder and readback consumer change |
| Runtime/browser | excluded | none | No database or governed runtime invocation authorized |
| Remote required gates | required at publication | exact-head PR checks | Integration qualification |

## Current observation

Current `sync_policy()` rebuilds the catalog payload and preserves only
`enabled`, `release_state`, `access_level` and `policy_note`. It then replaces
the complete maintained menu groups, capabilities, scenes, bindings and role
codes. This is the defect under implementation.

## Backend implementation

`ProductPolicyCatalogSyncService` now starts an existing-policy sync from the
current draft. It validates every selected native menu/action identity before
returning write values, then overlays only native source fields on those
selected rows and matching capability aliases.

The merge:

- preserves active/archive state, center identity/name/sequence, entry
  placement/label/sequence including `0`, release/access control, notes,
  business intent, roles, scenes and version bindings;
- preserves entries from external native roots and independent same-page
  business capabilities;
- does not add catalog discoveries to the product selection;
- preserves explicit empty collections and false values;
- rejects missing, unreadable, conflicting or rebound native actions with
  `PRODUCT_SYNC_SOURCE_MISSING`, `PRODUCT_SYNC_SOURCE_READ_FAILED` or
  `PRODUCT_SYNC_ACTION_IDENTITY_CHANGED`;
- searches including archived policies and writes only the submitted product;
- does not publish or alter another product.

Production-shaped merge sample:

| Fact | Before | After |
| --- | --- | --- |
| Project center | `项目中心（管理员命名）`, sequence `0` | unchanged |
| Project entry | label `项目台账（管理员命名）`, sequence `0`, `hidden` | unchanged except native `res_model`/path refresh |
| External accounting entry | `日记账分录`, sequence `30`, `preview` | retained |
| Role/scene/binding facts | `project_manager`, `scene.project@v4` | retained |
| New catalog discovery | present in source catalog | not admitted to product |

Failure sample for a rebound action:

```json
{
  "reason_code": "PRODUCT_SYNC_ACTION_IDENTITY_CHANGED",
  "entry": "project.menu_ledger",
  "write_attempted": false
}
```

## Backend validation

| Check | Result |
| --- | --- |
| `verify.runtime_capability_catalog.unit` | passed, 22 tests |
| `verify.capability.identity_boundary.unit` | passed, 8 tests |
| `verify.product_center.policy.unit` | passed, 15 tests |
| `verify.admin_close_01.backend.unit` | passed, 141 aggregate tests |
| `verify.agent.resume.unit` | passed, 67 tests |
| `verify.agent.ledger.unit` | passed, 18 tests |
| `make ci.local.iteration` | passed, exit 0, contract-only scope |

ORM, module baselines, module upgrade, browser matrix and environment rebuild
remain `not_run` by owner direction. The frontend consumer checks remain for
the handoff stage.

## Frontend implementation

The frontend keeps the existing unified configured-action path:

`sync action -> buildConfiguredOperatorParams -> request -> decodeConfiguredActionResult -> decodeReleaseOperatorSurface`.

It does not reconstruct data lost by the backend.

- A production-shaped sync result preserves the maintained center label and
  sequence `0`, entry label/sequence/intent, role restrictions and scene
  bindings.
- The returned management surface updates the current draft expression while
  the active released snapshot remains `v30`; sync is not represented as a
  publication.
- A sync readback for the wrong product is rejected before replacing the
  effective surface.
- `published_snapshot_id` now uses the strict integer decoder. Integer `0`
  passes; `null`, `false`, numeric strings and non-integers fail closed.
- The release-operator view no longer coerces the snapshot identity through
  `Number(...)`.

## Frontend validation

| Check | Result |
| --- | --- |
| `verify.frontend.platform_capability_explorer.unit` | passed, 84 contract cases |
| `verify.frontend.contract_basis.unit` | passed, 15 tests, open defects 0 |
| `verify.frontend.lint.src` | passed, 0 errors, 4 pre-existing warnings |
| `verify.frontend.typecheck.strict` | passed, exit 0 |
| `make ci.local.iteration` | passed, exit 0, contract-only scope |

The local run receipts now report all ten registered checks as reusable.
ORM, module baselines, module upgrade, browser matrix and environment rebuild
remain `not_run` by owner direction.

## R1 source-resolution remediation

Owner and independent review found that the first candidate could still treat
the maintained policy as proof of native source existence, could leak
source-database numeric IDs across databases, and could leave inconsistent
source model fields.

The R1 implementation now:

- resolves every selected native menu from the actual execution database by
  stable menu XMLID before any write, for both catalog-backed and non-catalog
  products;
- treats source-database IDs as discovery metadata only and writes execution
  database menu/action IDs;
- rejects same-XMLID action type or model rebinding with
  `PRODUCT_SYNC_ACTION_IDENTITY_CHANGED`;
- refreshes `model` and `res_model` consistently;
- skips native alias overlays for independent business capabilities;
- maps current-database catalog extraction failures to
  `PRODUCT_SYNC_SOURCE_READ_FAILED`;
- applies the same execution-database XMLID resolution before first creation;
- refreshes compatibility alias `model` and `res_model` together;
- reuses the catalog producer's complete action-model resolver
  (`res_model -> model_name -> model_id.model -> binding_model_id.model`);
- resolves initial catalog-derived scene source IDs from the execution database;
- keeps the all-validate-before-write, no-expansion, no-publication and
  product-isolation behavior.

Focused R1 results:

| Check | Result |
| --- | --- |
| `verify.runtime_capability_catalog.unit` | passed, 27 tests |
| `verify.capability.identity_boundary.unit` | passed, 8 tests |
| `verify.product_center.policy.unit` | passed, 15 tests |
| `verify.admin_close_01.backend.unit` | passed, 141 aggregate tests |
| `verify.frontend.platform_capability_explorer.unit` | passed, 84 contract cases; frontend inputs unchanged |
| `make ci.local.iteration` | passed, exit 0, contract-only scope |

ORM, module baselines, module upgrade and browser matrix remain `not_run` by
owner direction.

## Next exact step

Run delivery freeze preparation, commit and push the R3 candidate, then repeat
exact-head owner review.
