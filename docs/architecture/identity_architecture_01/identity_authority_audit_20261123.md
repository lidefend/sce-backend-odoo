# Identity Architecture 01 · Authority and Reference Audit

## 1. Decision

The repository already has a viable identity system. The defect is not missing
identity formats; it is the lack of a single governance document describing
which layer owns each identity and which cross-layer references are legal.

The architecture baseline is:

> Domain-specific authority identities + uniform cross-layer reference rules +
> fail-closed consistency validation.

A global Identity Registry is rejected. It would become a second authority for
Odoo records, menus, actions, contracts, scenes or attachments.

Authoritative machine-readable matrix:
`identity_authority_matrix.json`.

Relationship graph:
`identity_relationship_graph.mmd`.

## 2. Baseline and evidence boundary

- Mainline baseline: `8b46984d2b896eb104c26348788883993d260beb`.
- This audit changes no Odoo model, ORM identity, menu/action identity, ACL,
  Record Rule, workflow, database or product runtime source.
- P0-C-FIX-01 is recorded as a separate remediation candidate for the Action ID
  gap. Its future merge does not transfer Odoo or Contract V2 ownership.
- P0-B attachment-fact implementation remains a separate work package.

## 3. Identity layers

| Layer | Identity role | Examples |
| --- | --- | --- |
| Odoo authority | Persistent business and native technical identity | `model`, `record_id`, XMLID, `menu_id`, `action_id`, `attachment_id` |
| Product organization | Published navigation and scene composition | `(menu_id, action_id)`, `scene_key` |
| Contract definition | Page, field, occurrence and action declarations | `fieldCode`, `widgetId`, `occurrenceKey`, `actionId`, `backendIdentity` |
| Runtime instance | Current data row, record context and draft identity | `rowKey`, persisted `recordId`, local presentation keys |
| Security authority | Actor and server-resolved authorization subject | `user_id`, groups, company scope, internal authorization subject |
| Execution correlation | Request and feedback tracing | `requestId`, `traceId`, `reasonCode` |

Canonical matrix identities:

| Matrix ID | Identity |
| --- | --- |
| `odoo.model` | Odoo model |
| `odoo.record` | Odoo record |
| `odoo.xmlid` | Odoo External ID |
| `odoo.menu` | Odoo menu |
| `odoo.action` | Odoo action |
| `navigation.entry` | Published navigation entry |
| `product.scene` | Product scene |
| `contract.field` | ContractV2FieldDescriptor |
| `contract.widget_occurrence` | Contract widget/native occurrence |
| `contract.action_rule` | ContractV2ActionRule |
| `runtime.collection_row` | Collection row/draft row |
| `attachment.record` | Odoo attachment |
| `security.principal` | Authenticated principal |
| `security.authorization_subject` | Server authorization subject |
| `transport.request` | Intent request identity |
| `observability.trace` | Execution trace identity |

## 4. Frozen identity rules

### 4.1 Odoo identity remains authoritative

- A persisted business object is `model + record_id`; neither part is sufficient
  alone as a cross-domain reference.
- XMLID is an external identifier, never a display label or authorization input.
- Menu and action IDs are Odoo record identities. They are not scene keys.
- Attachment ID remains `ir.attachment.id`; URL is a locator and not attachment
  identity.

### 4.2 Navigation entry identity

The canonical entry reference is the published `(menu_id, action_id)` pair plus
its route kind/context. A single action may be carried by multiple menus. An
action-only reference is legal only when Route Authority has one exact
action-scoped/contextual destination.

`scene_key` is a product organization identity. It may be referenced by a
navigation entry, but it does not replace the menu/action pair and is not a route
authority by itself.

The frontend already enforces this in
`frontend/apps/web/src/app/canonicalNavigation.ts`; the server validates the
same route identity in
`addons/smart_core/handlers/route_authority_validate.py`.

### 4.3 Contract field and occurrence identity

- `fieldCode` identifies the business field.
- `widgetId`/`occurrenceKey` identifies a declared occurrence of a field,
  widget or action in a page contract.
- A field may occur more than once; field name alone cannot merge occurrences.
- DOM selectors and visible positions never become contract occurrence
  identities.

`ContractV2FieldDescriptor` remains the only field semantic authority.
`nativeLocator + occurrence_index` supplies stable occurrence evidence, and the
assembler rejects duplicate `occurrenceKey` values.

### 4.4 Action identity

The sole action authority is `ContractV2ActionRule`.

```text
actionId          canonical contract action identity
actionKey         stable business action key in its contract scope
backendIdentity   executable backend identity bound to the rule
sourceWidgetId    contract occurrence that originated the action
target            complete existing Action Target Schema value
```

These are related fields, not interchangeable aliases.

The real request path must preserve the full identity:

```text
ContractV2ActionRule
  -> Action View action projection
  -> runContractAction
  -> buildContractActionButtonRequest
  -> execute_button
  -> current unique rule revalidation
  -> canonical actionId + trace feedback
```

`ID-F-001` records the baseline gap. P0-C-FIX-01 is the separate remediation
candidate. The backend must never echo a client actionId without matching the
current unique rule.

### 4.5 Runtime row identity

| State | Identity |
| --- | --- |
| Persisted row | owner relation + `rowKey`, with `recordId` as record reference |
| Unsaved One2many draft | owner relation field + draft `rowKey` |
| Page Block row | producer-declared `rowKey` |
| Relation cell error | model + record/draft + relation field + `rowKey` + cell field |
| Local table/virtualization key | frontend-local only; never business identity |

`rowKey` is not equivalent to `recordId`. A persisted row can expose both.
Draft-to-persisted transitions must preserve or explicitly map the draft row
identity; reorder and pagination must not relocate business facts.

`ID-F-003` records the remaining positional fallback risk in Page Block data.
`ID-F-004` is an accepted local table key only while it is never used for
business effects.

### 4.6 Attachment identity

Attachment facts must keep four concepts separate:

| Concept | Meaning |
| --- | --- |
| `attachmentId` | `ir.attachment` record identity |
| `storageOwner` | actual Odoo storage association |
| `businessOwner` | business context represented by the page |
| authorization subject | server-resolved target used by the file service |

The authorization subject is internal and never public. The client never
chooses it. Existing `file.download`, upload and delete services remain the
authorization/execution authority.

`ID-F-005` is the explicit P0-B contract gap. URL/name/latest-record fallback is
not a complete attachment identity contract.

### 4.7 Principal and authorization subject

The authenticated principal comes from Odoo user/session and scoped credential
evidence. The authorization subject is a server-resolved execution-time fact.
Neither may be synthesized from a role label, company name, URL or client field.

### 4.8 Request and trace identity

- `requestId` names one intent request and may participate in idempotency where
  the operation declares it.
- `traceId` correlates all observations of one execution chain.
- Neither is a business-object identity.
- A content hash is not a trace. `ID-F-002` records the current content-hash
  fallback in Contract patch builders; the follow-up must use a real request
  trace or an explicitly typed unavailable state.

## 5. Cross-layer reference rules

1. Identity references name both the authority domain and the identity value.
2. A record reference always includes `model` and `record_id`.
3. Navigation references preserve the exact published menu/action pair when the
   client has a carrier menu.
4. `scene_key` is a target/composition reference, not menu/action identity.
5. `fieldCode` and widget occurrence identity are separate.
6. `actionId`, `actionKey`, `backendIdentity` and `sourceWidgetId` are not
   interchangeable aliases.
7. `rowKey` never substitutes for `record_id`.
8. Attachment URL/name/count are not attachment identity.
9. Authorization subject never enters a public carrier.
10. Trace/request IDs never become business, action, row or authorization IDs.
11. Missing required identity fails closed; only declared local presentation or
    draft identity may be generated in the frontend.

## 6. Findings and ownership

| ID | Severity | Finding | Owner | Status |
| --- | --- | --- | --- | --- |
| `ID-F-001` | P1 | Action View request omits full Action Rule identity | P0-C-FIX-01 | remediation candidate |
| `ID-F-002` | P1 | Content fingerprint used as trace fallback | identity trace follow-up | open |
| `ID-F-003` | P2 | Page Block positional `rowKey` fallback | identity row follow-up | open |
| `ID-F-004` | P3 | Index-based table display key | frontend presentation | accepted local only |
| `ID-F-005` | P1 | Attachment URL/name fallback lacks full fact identity | P0-B | scheduled |
| `ID-F-006` | P3 | Navigation identity is mature | identity baseline | frozen |
| `ID-F-007` | P2 | Authorization subject is server-only | identity baseline | frozen |
| `ID-F-008` | P2 | `actionId` name spans native numeric and contract string identities | P0-C-FIX-01 | remediation candidate |

## 7. Delivery order

1. Review/merge `P0-C-FIX-01` for `ID-F-001`.
2. Freeze this identity architecture after independent review.
3. P0-B implements `ID-F-005` using the existing file services.
4. `IDENTITY-TRACE-01` closes `ID-F-002` before trace evidence is treated as
   authoritative.
5. `IDENTITY-ROW-01` closes collection-row identity gaps in affected consumers.
6. FCF-02-2 consumes the frozen data/action/attachment facts.

## 8. Current status

- Identity matrix and graph: complete audit draft.
- Product source changes: none.
- Database/ACL/workflow changes: none.
- P0-B: blocked pending this baseline and P0-C-FIX-01 closure.
- FCF-02-2/02-3: still locked.
- Independent review: pending.
