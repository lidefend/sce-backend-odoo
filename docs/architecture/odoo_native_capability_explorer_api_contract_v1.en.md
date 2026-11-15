# Odoo-Native Capability Explorer Read-Only API Contract v1

Status: read-only backend API implemented; no frontend page or write operation

## Classification result

The probe discovered 282 native business entries:

- 75 have an authoritative business domain from existing product-scenario
  bindings.
- 207 retain only a native center and remain `unclassified`.
- 0 have ambiguous multi-scenario bindings.
- 282 have a stable native primary-center XMLID.
- 282 are technically selectable for a scene draft.

Center is a browse hint, not a business domain. The historical 63-item UI
registry, Chinese labels and model prefixes are not classification evidence.

## Existing Intent review

The following existing Intents are not equivalent:

- `capability.describe` reads legacy `sc.capability`.
- `capability.visibility.report` reads legacy `sc.capability`.
- `product.configuration.capability.catalog` describes configuration workbench
  features, not the platform capability explorer.

Implemented read-only Intents:

- `platform.capability.explorer.list`
- `platform.capability.explorer.detail`
- `platform.capability.explorer.diagnose`

## Contract boundaries

List supports server-side query, explicit filters, offset pagination up to 100,
stable sort with native XMLID tie-breakers, center/domain facets and a
request-time `catalog_token`. List and Detail both accept
`expected_catalog_token`; a mismatch returns `409 CATALOG_STALE`.

Detail uses the stable `(menu_xmlid, action_xmlid)` identity and returns native
facts, classification evidence, scene usage, release state and separate product
qualification status.

Diagnose returns distinct flags for native validity, draft selectability, scene
assignability, entry publication and Preview/Standard qualification. These
states may not be collapsed or inferred from one another.

The main catalog contains only entries with a stable Menu + Action XMLID.
Diagnose additionally accepts `menu_xmlid` so current-registry menus with a
missing Action, unsupported Action type, missing Model, uninstalled module or
ambiguous XMLID can return an explicit blocker without entering the draftable
catalog.

The backend authorizes the query before any sudo metadata read. Current-instance
queries require tenant configuration administration or valid platform-control
administration. Explorer never opens another database Registry and never builds
a superuser environment for another database. If the active release database is
not the current database, release authority is `PLATFORM_RELEASE_DB_ISOLATED` and
entry publication remains unknown.

The token covers the current database and language, installed modules and
dependencies, Menu/Action identities and targets, native hierarchy and order,
models and fields, View associations, ACL, record rules, scene bindings,
publication state and centers, qualification facts, active release snapshot
identity, authority availability, provider results, root/fallback diagnostics,
XMLID ambiguity and release-center conflicts.

The native catalog and all metadata joins are batch-loaded. List rows stay
lightweight; Detail expands technical summaries; Diagnose reuses the same
projection. SQL count, projection stages, contribution loading and serialization
timing are returned without cross-request caching.

Release centers carry their real P1 source. Conflicting center declarations are
not silently resolved to the first value; the center is omitted, the conflict is
returned in diagnostics and the token, and the affected release section carries a
blocker.

The full field-level contract is maintained in the Chinese source document.
No capability table, write endpoint, browser UI or scene editor is implemented.
