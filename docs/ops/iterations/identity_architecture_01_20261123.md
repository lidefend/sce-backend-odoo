# IDENTITY-ARCHITECTURE-01

## Batch identity

- Integrated baseline: `2a99f01c55af1c1cee01bc29d280fa5cc777b12f`
- Branch: `audit/identity-architecture-01-20261123`
- Result index: `.agent/runs/IDENTITY-ARCHITECTURE-01/run.json`

## Ownership

- Formal product layer: P0 cross-layer architecture governance.
- Layer target: identity authority, references, lifecycle and validation across
  Odoo, Contract V2, scene/navigation and frontend runtime.
- Modules reviewed: `smart_core`, `smart_construction_core`,
  `frontend/apps/web`.
- Standard vs user-specific: platform standard.

## Objective

Freeze the existing domain-specific identity authorities and their allowed
cross-layer references. The audit must not create a global identity registry or
replace existing Odoo, Contract V2, scene, attachment or authorization facts.

## Exclusions

- Product source changes.
- Odoo identity, ORM, ACL, Record Rule, workflow or database changes.
- Attachment implementation; P0-B remains separate.
- P0-C implementation; the known Action ID gap is recorded for the separate
  P0-C-FIX-01 candidate.
- FCF-02-2, FCF-02-3 and deployment.

## Deliverables

- Identity authority and relation audit.
- Machine-readable identity matrix and finding lifecycle.
- Identity relationship graph.
- Consistency guard and negative tests.

## Audit result

The audit freezes 16 identity domains, 23 relationships and 8 findings:

- `odoo.model`, `odoo.record`, `odoo.xmlid`, `odoo.menu`, `odoo.action`;
- `navigation.entry`, `product.scene`;
- `contract.field`, `contract.widget_occurrence`, `contract.action_rule`;
- `runtime.collection_row`, `attachment.record`;
- `security.principal`, `security.authorization_subject`;
- `transport.request`, `observability.trace`.

Architecture decisions:

- no global Identity Registry;
- Odoo remains authoritative for model/record/menu/action/attachment facts;
- Route Authority owns the exact published `(menu_id, action_id)` entry;
- `scene_key` remains a product organization identity and never substitutes for
  menu/action identity;
- ContractV2ActionRule remains the only action authority;
- `rowKey` never substitutes for persisted `record_id`;
- authorization subject remains server-only;
- request/trace identity never becomes business or authorization identity.

Findings:

| ID | Finding | Owner | Status |
| --- | --- | --- | --- |
| `ID-F-001` | Full Action Rule identity missing from historical baseline | P0-C-FIX-01 | fixed by PR #976 (`2a99f01c`) |
| `ID-F-002` | Content fingerprint used as trace fallback | IDENTITY-TRACE-01 proposal | open |
| `ID-F-003` | Positional Page Block rowKey fallback | IDENTITY-ROW-01 proposal | open |
| `ID-F-004` | Index-based local table key | frontend presentation | accepted local only |
| `ID-F-005` | Incomplete attachment fact / URL locator | P0-B | scheduled |
| `ID-F-006` | Navigation identity mature | identity baseline | frozen |
| `ID-F-007` | Authorization subject server-only | identity baseline | frozen |
| `ID-F-008` | `actionId` name overlap across native and contract identity | P0-C-FIX-01 | fixed by PR #976 (`2a99f01c`) |

## Validation

- `verify.identity.architecture.audit.unit`: PASS, 14 tests and matrix/graph
  validation for 16 domains, 23 edges and 8 findings.
- `verify.docs.contract_sync`: PASS and consumes the identity guard.
- `verify.docs.links`: PASS.
- `verify.guard.registry`: PASS.
- `verify.agent.ledger.unit`: PASS.
- `verify.frontend.dev.incremental.unit`: PASS.
- `make ci.local.iteration`: PASS.
- `make ci.delivery.freeze.prepare`: PASS.

`verify.docs.all` reaches a separate pre-existing
`verify.native_scene.inventory.unit` failure: five native scene inventory files
are stale on the integrated baseline. This audit changes no native model, menu,
action or view source. The failure is classified as
`baseline_evidence_defect` and remains outside this read-only identity scope.

No product source, database, ACL, workflow or runtime configuration was changed.
The identity baseline remains pending independent review.
