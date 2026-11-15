# Odoo-Native Capability Explorer Read-Only API Contract v1

Status: design validation complete; no product runtime implementation

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

Proposed read-only Intents:

- `platform.capability.explorer.list`
- `platform.capability.explorer.detail`
- `platform.capability.explorer.diagnose`

## Contract boundaries

List supports server-side query, explicit filters, offset pagination up to 100,
stable sort with `menu_xmlid` tie-breaker, center/domain facets and a
request-time `catalog_token`.

Detail uses the stable `(menu_xmlid, action_xmlid)` identity and returns native
facts, classification evidence, scene usage, release state and separate product
qualification status.

Diagnose returns distinct flags for native validity, draft selectability, scene
assignability, entry publication and Preview/Standard qualification. These
states may not be collapsed.

The backend must authorize the query. `draft_selectable` is not product maturity,
ACL row existence is not effective record access, and entry publication does not
establish capability qualification.

The full field-level contract is maintained in the Chinese source document.
No capability table, write endpoint, browser UI or scene editor is implemented.
