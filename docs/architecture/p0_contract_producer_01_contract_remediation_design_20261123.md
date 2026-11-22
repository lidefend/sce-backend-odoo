# P0-CONTRACT-PRODUCER-01

## Page Block, attachment and action/feedback contract remediation design

Status: design candidate; no product implementation authorized.

Review candidate: PR #973.

Baseline:

- PR #972 reviewed head:
  `5e3805932dbf04b251193bc5e6b4e65b8cc03271`
- Merge commit / design baseline:
  `dec7e985d3985e248c8b5c4903e8f77739bb807d`
- Contract-gap evidence:
  `docs/audit/fe_contract_fidelity_02_2/gap_probes.json`
- Machine-readable design:
  `docs/architecture/p0_contract_producer_01/remediation_design.json`
- Compatibility matrix:
  `docs/architecture/p0_contract_producer_01/compatibility_matrix.json`
- Strict descriptor schema:
  `docs/architecture/p0_contract_producer_01/contract_v2_field_descriptor.schema.json`
- Descriptor positive/negative fixtures:
  `docs/architecture/p0_contract_producer_01/descriptor_cases.json`

Formal product layer and scope:

- Layer: P0 generic contract-production mechanism.
- Target: `smart_core` carrier/schema/action projection, with
  `smart_construction_core` only mapping industry facts into that carrier.
- Standard vs user-specific: platform-generic runtime.
- Why here: these facts must exist before a renderer can preserve them.
- Why not elsewhere: a page-local format, frontend default or low-code special
  case would become a second business authority.
- Blast radius: Page Orchestration value data, attachment facts and Page Block
  action correlation. This document changes no product or persisted data.

Explicit exclusions:

- no Odoo model, ACL, workflow, ORM, database or migration change;
- no product or frontend implementation;
- no new Renderer, Registry, Bundle, page engine or Value Runtime;
- no new attachment authorization system;
- no FCF-02-2 or FCF-02-3 product work.

## 1. Decision

The three audited gaps require a producer-layer correction.

The smallest coherent solution is three additive carriers inside the existing
Contract V2/Page Orchestration delivery:

1. `page-block-data.v1` for business values;
2. `attachment-fact.v1` for attachment identity, ownership, role and action
   references;
3. `page-block-action.v1` for resolved action state and execution feedback.

The carriers share the existing field descriptor, action rule and standard
response-envelope models. No second protocol runtime is required.

## 2. Existing contract assets to reuse

The design reuses these existing declarations rather than inventing parallel
ones:

- `frontend/apps/web/src/app/contracts/v2/types.ts::ContractV2FieldDescriptor`
  already carries field identity, type, widget, component key, selection,
  relation, relation entry and widget options.
- `ContractV2ActionRule` already carries action identity, target, visibility,
  allowed/enabled/disabled state, reason code/message, entitlement evaluation,
  authorization result and business availability.
- `ContractV2StatusContract` already carries page, widget, button and container
  visibility/state declarations.
- `runtimeContract.collaboration.attachments` already carries partial upload,
  download, delete and UI-label declarations.
- `chatter_timeline.py` already emits stable attachment IDs and authorized
  download/delete projections.
- Existing `file.download`, `file.upload` and `chatter.attachment.delete`
  handlers remain execution and authorization authorities.
- `contract_version_compatibility.py` already provides additive/breaking delta
  classification and N-1/N/N+1 consumer drills.

The new design does not duplicate these values. It adds missing structure,
identity and contextual semantics around them.

## 3. Version and negotiation strategy

### Carrier versions

Each nested carrier starts at:

```text
page-block-data.v1      schemaVersion = 1.0.0
attachment-fact.v1      schemaVersion = 1.0.0
page-block-action.v1    schemaVersion = 1.0.0
```

Minor additions are optional and backward-compatible. Unknown minor versions
within major `1` may be retained but undeclared keys cannot become semantic
authority. Unknown major versions fail closed.

### Contract versions

The implementation candidate should publish:

- Page Orchestration `contract_version: "2.1.0"` for the additive block
  carriers;
- Contract V2 `pageInfo.contractVersion: "2.6.0"` for the assembled snapshot.

The current Page Orchestration consumer accepts only `2.0.0`, and the Contract
V2 decoder currently accepts through `2.5.x`. Those consumers must be updated
and tested before the producer emits the new versions.

### Negotiation and mixed-version safety

Current implementation facts:

- `frontend/apps/web/src/app/contracts/v2/client.ts` sends
  `accepted_contract_versions = 2.0.x ... 2.5.x`;
- `schema.ts` accepts only Contract V2 `2.0` through `2.5`;
- `app_config_engine/utils/payload.py` preserves
  `client_contract_capabilities` but does not preserve
  `accepted_contract_versions`;
- the `ui.contract.v2` dispatch chain currently resolves component
  capabilities, not an outer contract-version projection;
- `contract_version_compatibility.py` tolerates unknown payload keys by design,
  while the real frontend Decoder rejects unknown keys.

Therefore the current code sends a version list but does not yet provide real
version negotiation. That must be corrected before the new carriers are
emitted.

Required implementation:

1. Add `CONTRACT_V2_ACCEPTED_VERSIONS` as the single client declaration and
   extend it to include `2.6.x` only after the new decoder is implemented.
2. Preserve and type-check `accepted_contract_versions` in the server request
   normalizer.
3. Add the three protocol capabilities:
   `page_block_data.v1`, `attachment_fact.v1`, `page_block_action.v1`.
4. Select the highest common accepted outer version at the request boundary.
5. Emit the new carriers only when the selected version and all required
   capabilities are present.
6. If no accepted version is common, return an explicit unsupported-contract
   error; never send a newer payload to an older decoder.
7. If capability negotiation is absent or incomplete, return the complete
   `2.5.0` Contract V2 / `2.0.0` Page Orchestration projection with no new
   carrier keys.
8. If `accepted_contract_versions` is completely absent:
   - a recognized stable client type (`web_pc`, `wx_mini`, `harmony_h5`)
     receives the complete `2.5.0` / `2.0.0` legacy projection;
   - an unknown or absent client type receives the typed
     `CONTRACT_VERSION_UNSUPPORTED` error.

The absence fallback is a protocol-compatibility default, not a product
semantic. It is capped at version `2.5.0`, never carries the new carriers, and
must be removed or explicitly renewed after the legacy-client migration window.

The same client and server declaration must drive request construction,
response selection and tests. Sending a version array without server selection
is not negotiation evidence.

Real Decoder acceptance is mandatory:

| Case | Expected | Current evidence state |
| --- | --- | --- |
| Old/base Decoder + old `2.5.0` projection | PASS | executed against current decoder |
| Old/base Decoder + new `2.6.0` marker | REJECT | executed against current decoder |
| Old/base Decoder + undeclared carrier key | REJECT | executed against current decoder |
| New Decoder + old `2.5.0` projection | PASS | required after implementation |
| New Decoder + new `2.6.0` projection | PASS | required after implementation |
| Client accepts 2.6 but omits a carrier capability | complete old projection | required after implementation |
| Known stable client omits `accepted_contract_versions` | complete old projection | required after implementation |
| Unknown/missing client omits `accepted_contract_versions` | `CONTRACT_VERSION_UNSUPPORTED` | required after implementation |

The offline key-surface compatibility drill remains useful for declaration
delta analysis, but it does not replace these executable Decoder/negotiation
tests.

This is contract negotiation, not a second renderer or runtime. It prevents an
older strict decoder from receiving unknown keys merely because the backend has
been upgraded.

Rollout order:

1. consumer schema accepts the additive carriers without requiring them;
2. server negotiates and can project both versions;
3. selected producers emit the carriers for covered page types;
4. behavior is validated at the new exact contract identity;
5. unsupported/legacy projections fail closed where business semantics are
   required;
6. legacy `datasets` presentation keys are removed only after zero-consumer
   proof and a reviewed deprecation window.

No database migration is required.

## 4. P0-A · Page Block business data carrier

### Current chain

```text
scene_block_schema.build_contract / page_contracts_builder
  -> page_orchestration.datasets
  -> ZoneRenderer.resolveDataset
  -> BlockRenderer
  -> Page Block component
  -> String() / JSON.stringify()
```

The current carrier contains a display-shaped `value` and loses the field
descriptor before the final component.

### Target carrier

Add an optional Page Orchestration map:

```json
{
  "block_field_descriptors": {
    "<descriptor-id>": "<exact ContractV2FieldDescriptor>"
  },
  "block_data_contracts": {
    "<data-source-key>": {
      "schemaVersion": "1.0.0",
      "fieldRefs": {
        "<slot-key>": {
          "kind": "widget|descriptor",
          "widgetId": "<required only for kind=widget>",
          "descriptorId": "<required only for kind=descriptor>",
          "rawValuePath": "<path under row.values>"
        }
      },
      "rows": [
        {
          "rowKey": "<stable-row-key>",
          "values": {
            "<slot-key>": "<raw-json-value>"
          }
        }
      ],
      "context": {
        "currencies": {
          "<currency-identity-key>": {
            "code": "CNY",
            "label": "¥"
          }
        },
        "timezone": "Asia/Shanghai"
      },
      "sourceAuthority": {
        "kind": "page_block_data_contract",
        "projectionOnly": true,
        "noBusinessFactAuthority": true
      }
    }
  }
}
```

The field source is intentionally not redeclared here. The canonical descriptor
is the existing `ContractV2FieldDescriptor` type, with only the missing
projection keys added to that same type:

```text
ContractV2FieldDescriptor
  optional digits
  optional currencyField
  optional unit
  optional temporal
  optional attachmentRole
```

A `fieldRef` resolves through one of two mutually exclusive references:

```text
kind=widget
  -> layoutContract.containerTree.*.widgetList[widgetId].fieldDescriptor

kind=descriptor
  -> page_orchestration.block_field_descriptors[descriptorId]
```

Both branches return the same `ContractV2FieldDescriptor` shape. Non-widget
business facts such as `project.total`, `payment.pending_amount` and
`project.completion_rate` therefore do not require a fake UI Widget. They also
do not create a second field-descriptor schema.

The current `decodeWidget()` only reads `fieldDescriptor` as an optional
untyped `ContractV2Dictionary`. That is the implementation gap this schema
closes; the existing TypeScript declaration alone is not validation evidence.

Implementation must add one strict decoder,
`decodeContractV2FieldDescriptor()`, and call it from both paths:

```text
decodeWidget()
  -> decodeContractV2FieldDescriptor(widget.fieldDescriptor)

decodePageBlockDataContract()
  -> decodeContractV2FieldDescriptor(block_field_descriptors[descriptorId])
```

The strict schema file is
`docs/architecture/p0_contract_producer_01/contract_v2_field_descriptor.schema.json`.
The existing TypeScript interface is extended in place; no parallel descriptor
type is permitted.

Descriptor validity has four checks. The JSON Schema validates shape, required
fields and conditional rules. Two test-checked projections constrain the
applicable field semantics and the complete native Widget vocabulary. The same
decoder then resolves `semanticType`, `componentKey` and `fieldType` against
the existing `contracts/registry/semantic.yaml` and
`contracts/registry/component.yaml` declarations. The schema enums are
projections of those registries, which remain the sole vocabulary authority.
Adding an industry or customer semantic therefore updates the contract
registry and its validated projection rather than creating a second semantic
list.

The semantic registry also declares action-only semantics. `action` and
`support_action` are not field semantics: they belong to the P0-C action and
feedback contract. The Field Descriptor schema therefore projects only
semantics whose canonical component supports at least one non-action field
type. `fieldType=action` is not a valid field-descriptor type. This is an
explicit responsibility boundary, not a missing semantic declaration.

`widgetType` uses the existing `semantic.yaml.native_widgets` vocabulary as its
sole authority. The schema enum is a test-checked projection of every declared
widget token; no second widget-name list exists. The same registry entry owns
the consumption policy:

- `ready` is accepted normally;
- `fallback` is accepted only when the same entry declares a fallback
  `reason_code`, and that declared reason is preserved;
- `unsupported` is rejected as a normal Field Descriptor and is not
  reinterpreted as a supported component;
- an unknown Widget name or unknown status fails closed.

The strict schema keeps all declared Widget names in its projection so that the
status layer, rather than a second name/status allow-list, decides whether a
declared token is consumable. `domain` and `tier_validation` therefore pass
name-vocabulary validation and are rejected by the registry-status layer.

Component consistency is resolved through the explicit
`semantic.yaml.semantics[semanticType].component` mapping, with
`component.yaml.components[componentKey].field_types` validating the field
type. Shared components are legitimate when the semantic registry declares
multiple semantics for them, as with `reference` and `readable_value`.

Required descriptor fields:

```text
schemaVersion
fieldCode
label
fieldType
widgetType
componentKey
semanticType
```

Conditional declaration rules:

| Semantic case | Required declaration | Forbidden declaration |
| --- | --- | --- |
| money | `digits`, `currencyField`, `semanticType=money` | `unit`, `temporal`, `attachmentRole` |
| percentage | `digits`, `unit.kind=percent`, `unit.code=percent` | `currencyField`, `temporal`, `attachmentRole` |
| duration | `digits`, `unit.kind=duration` with explicit code/label | `currencyField`, `temporal`, `attachmentRole` |
| date | `temporal.kind=date`, `timezoneAuthority=not_applicable` | digits, currency, unit, attachment role |
| datetime | `temporal.kind=datetime`, `timezoneAuthority=user|record` | digits, currency, unit, attachment role |
| relation types | `relation` | unrelated monetary/unit/temporal semantics |
| `ir.attachment` relation | `attachmentRole` | attachment behavior without a role |
| selection | non-empty `selection` key/label pairs | unknown option semantics |

The strict decoder must also reject:

- unknown properties;
- unknown `semanticType` values;
- action-only semantics in a field descriptor;
- component/semantic registry mismatches;
- unknown `widgetType` values outside `native_widgets`;
- malformed `digits`;
- unsupported descriptor schema versions;
- conditional-field inconsistencies.

Contract V2 `2.5` keeps its legacy descriptor decoder for compatibility. A
`2.6` Widget or Page Block carrier must use the strict decoder. New carriers
cannot reference a legacy descriptor.

For widget-backed values, the existing `componentConfig` remains a compatibility
transport projection. For semantic decisions, the canonical
`ContractV2FieldDescriptor` wins.

Rules:

1. `values` contain raw JSON values. Formatted display strings are not the
   semantic value.
2. `0`, `false`, `null`, empty string and missing key remain distinguishable.
3. Money requires `digits`, `currencyField`, and a currency identity reachable
   from the same row/context.
4. Percentage and duration require `componentKey` and `unit`; the frontend does
   not clamp, round or append a default unit.
5. Relations use record identity plus an authoritative label. Bare IDs and
   label-only objects fail closed.
6. Selection stores the original storage key; labels do not replace the key.
7. Datetime values retain the declared type and authoritative timezone.
8. Attachment values reference an attachment fact/role; attachment counts are
   not attachment identity.
9. Each block consumes the carrier through a declared field binding. A block
   must not infer a field from its title, label or dataset key.
10. The block-data carrier contains values and references only; the canonical
    `ContractV2FieldDescriptor` remains the sole field-semantic authority.
11. Widget-backed and non-widget-backed values are both required test cases.

Suggested block binding:

```json
{
  "data_binding": {
    "contract": "<data-source-key>",
    "rowKeyField": "rowKey",
    "labelField": "label",
    "valueField": "amount"
  }
}
```

### Producer ownership

P0 `smart_core`:

- defines the carrier schema, normalization, version gate and tests;
- resolves block-data slots to existing `ContractV2Widget` identities and
  descriptors;
- adds only missing projection context to the existing `componentConfig`;
- supplies authoritative currency/timezone context from the runtime contract;
- guarantees no display value is written back as a form or ORM value.

P1 `smart_construction_core`:

- maps construction block sources to stable field identities;
- supplies industry unit/role meaning where it is a P1 fact;
- must not define a separate semantic carrier.

## 5. P0-B · Attachment fact contract

### Current chain

```text
form collaboration contract / chatter.timeline / One2many relation
  -> partial surface-specific attachment fields
  -> attachment UI or action
```

Existing facts and authorization fragments are useful, but there is no one
fact envelope carrying identity, owner, role, action and failure identity
together.

### Target carrier

Add `runtimeContract.attachmentFacts`:

```json
{
  "schemaVersion": "1.0.0",
  "facts": [
    {
      "factKey": "<stable-fact-key>",
      "identity": {
        "attachmentId": "<positive-record-identity>",
        "name": "<file-name>",
        "mimetype": "<mime-type>",
        "size": 0
      },
      "storageOwner": {
        "model": "<attachment.res_model>",
        "recordId": "<attachment.res_id>"
      },
      "businessOwner": {
        "model": "<page-or-business-context-model>",
        "recordId": "<page-or-business-context-record-identity>"
      },
      "role": {
        "code": "<role-code>",
        "label": "<role-label>",
        "sourceAuthority": {
          "kind": "<p0-or-p1-declaration>",
          "ownerLayer": "P0|P1"
        }
      },
      "actionRefs": {
        "preview": "<action-id-or-empty>",
        "download": "<action-id-or-empty>",
        "delete": "<action-id-or-empty>"
      }
    }
  ]
}
```

Action details remain in `P0-C`. This prevents attachment facts from defining a
second permission model.

The internal `authorizationSubject` is not part of this public carrier and is
not included in the response fixture. It remains only in server execution
authorization; the client receives the resolved authorization result, disabled
reason and failure feedback.

Rules:

1. Attachment identity is an attachment record identity, not a display label,
   count or URL shape.
2. `storageOwner` is the attachment's actual `res_model` / `res_id` storage
   association.
3. `businessOwner` is the page or business-context record whose meaning gives
   the attachment its role. It may differ from `storageOwner`.
4. `authorizationSubject` is action-scoped, server-only and never serialized to
   the client. The frontend neither supplies nor overrides it.
5. For download, the existing `resolve_file_download_auth_subject()` remains
   authoritative and may return a subject different from `storageOwner`.
6. Upload and delete continue to use their existing server-side record and ACL
   checks.
7. Public storage/business owners and the server-only authorization subject must
   never be collapsed into a single `owner` field.
8. `role` is explicit and may differ by industry context. P0 owns the role
   field, while P1/P2 may own which role applies.
9. Preview derives from an explicitly authorized retrieval action; unsupported
   file types may disable preview while download remains allowed.
10. Download and delete use existing governed file services.
11. Failure feedback is supplied by `page-block-action.v1`, preserving reason
   code, message and trace identity.
12. Text URLs and ordinary integers are never attachment facts unless a producer
   explicitly emits this carrier.

### Producer ownership

- `smart_core` owns the generic attachment fact envelope and handles existing
  `file.download`, `file.upload` and `chatter.attachment.delete` authorization.
- `chatter_timeline.py` projects current attachment rows into the envelope.
- `file_download.py` evaluates its resolved authorization subject internally
  and publishes only the authorization result; the subject is not serialized,
  and a request-supplied subject is never accepted as authority.
- Contract V2 attachment surfaces and form collaboration fields reference
  facts; they do not duplicate authorization booleans.
- `smart_construction_core` supplies construction-domain role assignments when
  the model/page contract needs them.

The existing attachment permission policies remain unchanged. Only the
transport of the evaluated result becomes complete and consistent.

## 6. P0-C · Page Block action and feedback contract

### Current chain

```text
page_contracts_builder action_schema
scene_block_schema block actions
  -> PageRenderer/Page Block action event
  -> page-local target fallback and transient error UI
```

Role visibility is not a resolved authorization result. Block actions can lose
the target, and failures are not correlated to the action identity.

### Target carrier

Page Block actions become stable references into the existing resolved action
contract:

```json
{
  "schemaVersion": "1.0.0",
  "actions": {
    "<action-id>": {
      "actionId": "<action-id>",
      "actionRuleRef": "<ContractV2ActionRule.actionId>",
      "actionKey": "<stable-action-key>",
      "label": "<label>",
      "intent": "<intent>",
      "target": {
        "source": "ContractV2ActionRule.target",
        "value": "<exact target object produced and validated by action_target_schema.py>"
      },
      "visibility": {
        "visible": true,
        "source": "action_contract"
      },
      "permission": {
        "evaluated": true,
        "allowed": true,
        "authorizationAllowed": true,
        "businessAvailable": true
      },
      "state": {
        "enabled": true,
        "disabled": false,
        "reasonCode": "",
        "reasonMessage": ""
      }
    }
  }
}
```

The internal `authorizationSubject` is not part of this public action payload.
It stays inside the server authorization execution path.

The target object itself is not wrapped or re-defined by this carrier. Existing
Page Block target shapes remain exactly as the Action Target Schema publishes
them:

```text
{"kind": "scene.key", "scene_key": "..."}
{"kind": "route.path", "path": "..."}
{"kind": "page.refresh"}
{"kind": "menu.first_reachable"}
```

Target forms already used by `ContractV2ActionRule` for concrete action/record
opens remain unchanged and must be validated by that existing schema. The
frontend does not translate one kind into another or fall back to `open_scene`.

Execution feedback uses the same action identity:

```json
{
  "runtimeContract": {
    "actionFeedback": [
      {
        "schemaVersion": "1.0.0",
        "actionId": "<action-id>",
        "status": "success|denied|failed",
        "reasonCode": "<declared-reason-code>",
        "message": "<visible-message>",
        "traceId": "<request-or-response-trace-id>"
      }
    ]
  }
}
```

Rules:

1. `actionId` must resolve to one existing `ContractV2ActionRule`.
2. `target` is the complete existing `ContractV2ActionRule.target` produced by
   `action_target_schema.py`; the design does not define a parallel target
   vocabulary.
3. `visibility.visible` is presentation/role visibility.
4. `authorizationAllowed` is actor authorization only.
5. `businessAvailable` is business/workflow-state availability only.
6. `allowed` is a producer-computed compatibility aggregate equal to
   `authorizationAllowed && businessAvailable && targetResolved &&
   permissionEvaluated`. It is not an independent fact or frontend input.
7. `enabled` is the final server-produced execution state. It may be narrower
   than `allowed`, and `enabled=true` implies `allowed=true`.
8. The frontend consumes `enabled`; it must not recompute it from role labels,
   target shape or business fields.
9. A visible but unavailable action requires a disabled reason.
10. Missing permission evaluation fails closed.
11. Action execution results are correlated by `actionId`, `reasonCode`,
   `message` and `traceId`, carried in `runtimeContract.actionFeedback` (or the
   equivalent runtime action-patch envelope using the same versioned shape).
12. The frontend must not synthesize `open_scene` or another fallback target.
13. The existing Odoo action/authorization service remains the decision and
   execution authority.

### Producer ownership

- `page_contracts_builder.py` emits canonical target and action identity.
- `unified_page_contract_v2_runtime_actions.py` and
  `unified_page_contract_v2_permissions.py` resolve allowed/enabled state.
- `unified_page_contract_v2_status.py` projects page/widget/button status.
- the intent/action dispatcher remains responsible for real execution and
  standard error metadata.
- `scene_block_schema.py` references resolved action IDs rather than creating
  incomplete local action records.

## 7. Cross-carrier rules

- Every business value has exactly one producing declaration.
- No display string is parsed to recover type, precision, unit, relation,
  attachment role or action permission.
- `null`, empty, zero, false and absent remain distinct.
- Currency and timezone come from authoritative context.
- Relation and attachment identities are independent from their labels.
- A producer may emit a compatibility display value during migration, but a
  consumer that has the typed carrier must not use it for business semantics.
- Existing read-only surfaces must continue to issue no business writes.

## 8. Responsibility and file map

| Area | Owner | Likely files |
| --- | --- | --- |
| Carrier schema and normalized projection | P0 | `addons/smart_core/core/unified_page_contract_v2_assembler.py`, new `unified_page_contract_v2_semantic_carriers.py`, `contract_version_compatibility.py` |
| Page orchestration producer | P0 | `addons/smart_core/core/page_contracts_builder.py`, `page_orchestration_data_provider.py` |
| Action resolution and feedback | P0 | `unified_page_contract_v2_action.py`, `unified_page_contract_v2_permissions.py`, `unified_page_contract_v2_status.py`, `action_target_schema.py`, intent/action dispatchers |
| Attachment facts | P0 | `chatter_timeline.py`, existing file upload/download/delete handlers, Contract V2 collaboration projection |
| Construction block mapping | P1 | `addons/smart_construction_core/services/scene_block_schema.py` and industry page assemblers |
| Decode and normalized types | P0 consumer boundary | `frontend/apps/web/src/app/contracts/v2/schema.ts`, `types.ts`, `store.ts`, `app/pageOrchestration.ts` |
| Page Block consumption | Later FCF-02-2 only | `PageRenderer.vue`, `ZoneRenderer.vue`, block components |
| Guards | P4 | existing Page Contract guards plus new carrier/negative tests |

This file map is a design inventory, not authorization to modify all files.

## 9. Compatibility and test matrix

Each implementation package must cover:

### Value carrier

- money zero, negative and mixed currencies;
- percentage `12.5`, precision preservation and no clamping;
- duration in declared units;
- count zero versus absent;
- boolean false versus null/absent;
- known and unknown selection keys;
- relation tuple/object with stable record identity;
- missing relation identity;
- date/datetime with explicit timezone;
- attachment role reference;
- widget-backed descriptor reference;
- non-widget computed/aggregate business fact descriptor;
- old payload without a carrier fails closed for a block whose business
  semantics require it.

### Attachment facts

- same attachment role across form, timeline and One2many;
- different roles on the same owner;
- attachment owner mismatch;
- missing attachment ID;
- download allowed/denied with reason;
- preview supported/not supported;
- delete owner/admin/non-owner paths;
- failure reason/message/trace;
- forged Authorization Subject is rejected/ignored as authority;
- public fact and action payloads contain no Authorization Subject;
- text URL and ordinary integer do not become attachments.

### Action feedback

- visible + allowed + enabled;
- visible + authorization denied + reason;
- visible + business unavailable + reason;
- hidden action;
- missing permission evaluation;
- missing target;
- failed execution with reason/message/trace;
- no `open_scene` or local target fallback.

### Compatibility

- current/base Decoder accepts the existing `2.5.0` projection;
- current/base Decoder rejects a `2.6.0` outer version;
- current/base Decoder rejects undeclared attachment/action-feedback carriers;
- implementation Decoder accepts both the old and new complete projections;
- a client omitting any required carrier capability receives the complete old
  projection;
- a known stable client sending no version declaration receives the complete
  old projection;
- an unknown/missing client with no version declaration receives the typed
  `CONTRACT_VERSION_UNSUPPORTED` error;
- no common accepted version fails closed;
- N-1 consumer reads N payload;
- N consumer reads N-1 payload;
- additive keys are optional;
- unknown major carrier version fails closed;
- old Page Orchestration 2.0 remains readable until the negotiated cutover;
- Page Orchestration 2.1 and Contract V2 2.6 are internally consistent;
- append-only rollback follows the existing compatibility core.

## 10. Migration and rollback

Migration:

1. no database schema or data migration;
2. add schemas, decoder acceptance and fixtures;
3. add producer projection for selected pages behind explicit contract-version
   negotiation;
4. emit typed carriers and legacy display fields together during transition;
5. switch consumers by capability, then run the contract-gap probes again;
6. retire legacy display-only fields only after zero consumers are proven.

Rollback:

1. disable producer emission of the additive carriers;
2. continue serving the previous negotiated contract version;
3. consumers render an explicit contract-gap state rather than guessing;
4. revert code only; no data rollback is required.

## 11. Validation

Read-only design verification passed:

- Contract Fidelity plan plus P0 design consistency: 22 Python tests.
- Strict Descriptor structural and registry validation: 24 positive/negative
  fixture cases.
- Semantic registry lint: PASS; 28 semantics and 33 components remain
  consistent with their generated frontend and backend projections.
- Page Contract orchestration: 19 pages.
- Page Contract action semantics: 19 pages.
- Page Contract data-source semantics: 19 pages.
- Page Block renderer smoke and registry guard: PASS.
- Contract N-1/N/N+1 compatibility core: 31 tests.
- Agent ledger: 18 tests.
- Real current Decoder checks: 4 checks; old projection accepted, `2.6.0` and
  two undeclared carriers rejected.
- Machine design reconciliation: 3 packages, 56 planned positive/negative
  cases, 44 compatibility rows and 27 current-source hashes.
- `ci.local.iteration`: PASS.
- `ci.delivery.freeze.prepare`: PASS.

No product source, backend contract, database, fixture or runtime state was
changed. No runtime or browser PASS is claimed for the future implementation.

## 12. FCF-02-2 unlock conditions

FCF-02-2 remains locked until all of the following are true:

1. this design is independently approved;
2. generic carrier schemas and version negotiation are implemented in `smart_core`;
3. P1 mappings in `smart_construction_core` are implemented and reviewed;
4. existing file and action services remain the execution authorities;
5. positive and negative tests cover all three carriers;
6. accepted-version negotiation and both old/new Decoder tests pass, including
   the capability-omission and no-common-version negatives;
7. the CFG-GAP-02/04/05 probes are rerun on the new exact source identity and
   no longer return `contract_gap` for the required surfaces;
8. the new contract is served and read back through a governed runtime identity;
9. an independent review approves the producer change.

Until then, no second frontend interpretation path may be introduced.
