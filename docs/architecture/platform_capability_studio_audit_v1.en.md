# Platform Capability Catalog and Scene Governance Audit v1

Status: first read-only audit complete

Baseline: `main@2571346afc8c69cea20e32fcba36082c949cf825`

Runtime: `demo / sc_demo / daily-dev-demo`

## Result

There is no single authoritative catalog that joins business capability identity,
provider execution, maturity evidence, entry publication, scene composition,
product release and enterprise enablement.

The checked-in CAP-01 data resolves to 63 historical identities:
13 keep, 26 defer and 24 exclude, producing a 39-item candidate catalog. The
current 63-item startup UI registry is not a successor of that candidate catalog:
it overlaps on 38 items, omits canonical `project.initiation.create`, retains
`project.initiation.enter`, and re-includes 24 identities previously excluded as
page/navigation entries.

## Separated facts

| Fact source | Count | Meaning |
|---|---:|---|
| Installed modules | 77 | installation scope |
| Models | 758 | model facts |
| Native action menus | 498 | executable entry facts |
| Business native action menus | 282 | business-root entry discovery pool |
| Current startup UI registry | 63 | UI capability projection |
| Runtime `sc.capability` | 6 | legacy scene-tile capability records |
| Released entry aliases | 274 per edition | menu-page compatibility identities |
| Product configuration UI catalog | 25 | configuration UI features |

None of these numeric sets can be used as the business capability count.

## Maturity and publication

- Eight capability acceptance contracts exist.
- Seven of eight exist in the current registry; `project.initiation.create` does not.
- None of the eight exists in runtime `sc.capability`.
- No `capability.maturity.evidence.v2` bundle is present in the checkout.
- Evidence-backed Preview and Standard qualifications are therefore both zero.
- The formal menu policy contributes 92 unique `RELEASED_FOUNDATION` and 40 unique
  `PREVIEW_FOUNDATION` entries.
- Released snapshots expose 274 aliases per edition as `released`, omit
  `capability_maturity`, and contain four `policy_only` scene projections with
  `BINDING_MISSING`.

Capability maturity and entry publication must remain independent.

## Scene and enterprise state

There are 17 maintained business scenarios, 78 menu references and eight centers.
All 17 are considered product-released and are enabled for company 1. The current
scene predicate only needs one released member menu; it does not require capability
maturity or full-scene evidence.

The legacy scene catalog has 60 records, but only two contain tiles and 58 are empty.
It is compatibility data, not the capability usage catalog.

There are 201 released business entry menus without a product-scenario binding and
75 scene-bound menus. That is an entry discovery pool, not an unsceneized business
capability list.

## Authorization

Capability, legacy scene and product-release editing are still restricted to the
platform/core administrator group. Business configuration administrators can edit
`sc.product.scenario` and company enablement. Dedicated capability operator, scene
operator and product release reviewer authorities are not implemented.

## Reuse and next design

Reuse `RuntimeCapabilityCatalogService`, the maturity evaluator and evidence
verifier, scenario composition models, product policy/release snapshots and company
enablement. Do not create a second editable capability registry.

Introduce a read-only `PlatformCapabilityCatalogService` that joins:

- capability identity, provider and dependency
- Preview/Standard maturity and evidence
- entry aliases and release state
- scene references
- product-version references
- enterprise enablement
- blockers and verification time

The capability center and scene editor must consume this backend projection. The
editor may select only backend-qualified capabilities and must render blocker
reasons instead of inferring eligibility in the frontend.

The complete cross-source inventory is
[`platform_capability_studio_inventory_v1.json`](platform_capability_studio_inventory_v1.json).
No product runtime change was made in this audit.
