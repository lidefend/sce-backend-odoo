# FE-CONTRACT-FIDELITY-02-2

## Read-only contract-gap probes

Status: probe complete; contract gaps confirmed; FCF-02-2 product implementation
remains locked pending P0 producer remediation and independent review.

Review candidate: PR #972.

Mainline closure:

- Reviewed head: `5e3805932dbf04b251193bc5e6b4e65b8cc03271`
- Merge commit / design baseline:
  `dec7e985d3985e248c8b5c4903e8f77739bb807d`
- Independent review: approved
- Mainline integration: completed
- Deployment and user acceptance: not applicable to this read-only batch

Baseline:

- Mainline after FCF-02-1:
  `5f032c1729e37ae7ac4642f51a5018ef3f78b02c`
- FCF-02-1 reviewed head:
  `29029ddd339130426b255b55badf1fceacecdd44`
- Probe branch:
  `audit/fcf-02-1-closeout-fcf-02-2-probes-20261123`

Formal product layer:

- Layer: P0 generic frontend contract interpretation and transport boundary.
- Standard vs user-specific: platform-generic runtime.
- Why here: the questions concern whether Contract V2 carries business facts
  before any page-local renderer interprets them.
- Why not elsewhere: missing semantics must not be reconstructed by a page,
  customer configuration, CSS, ORM fallback or second value runtime.
- Blast radius: Readonly Collection transport, Page Block values/actions/feedback
  and attachment identity/role. This batch changes no product source.

Explicit exclusions:

- no backend contract, ACL, workflow, ORM or persisted-value change;
- no database, fixture, service, credential or deployment write;
- no FCF-02-2 product implementation;
- no FCF-02-3 My Work or Progress remediation;
- no visual redesign, Renderer, Registry, Bundle or second value runtime.

## Method and evidence level

The probe followed each value from its producer declaration through the current
frontend consumer and checked it against existing runtime contract snapshots.
It did not infer correctness from component names or from the ability to render a
string.

Evidence used:

1. Current producer and consumer source at the exact mainline baseline.
2. Existing checked-in contract readbacks:

   - `docs/contract/snapshots/workspace_home_enter_intent_admin.json`
   - `docs/contract/snapshots/system_init_intent_admin.json`
   - `docs/contract/snapshots/native_view/semantic_page_project_form_collab_v1.json`

3. Machine-readable result:
   `docs/audit/fe_contract_fidelity_02_2/gap_probes.json`

No new browser run or served-runtime PASS is claimed. The decisive facts are the
absence of required declarations in producer schemas and producer outputs. A
renderer showing a value does not close a missing semantic contract.

One existing guard,
`verify.page_orchestration.target_completion.guard`, fails on the unchanged
mainline because its required legacy tokens are absent from
`workspace_home_contract_builder.py` and `WorkbenchView.vue`. Those files are not
changed by this probe batch. The failure is classified as a
`validation_tool_defect`/stale guard and is excluded from probe evidence; it is
not rewritten or hidden in this branch.

## Summary

| Probe | Semantic | Decision | Immediate effect |
| --- | --- | --- | --- |
| `CFG-GAP-02` | Page Block business-value carrier | `contract_gap` | FCF-02-2 transport implementation locked |
| `CFG-GAP-04` | Attachment identity and role | `contract_gap` | FCF-02-2 attachment work locked |
| `CFG-GAP-05` | Page Block action and feedback | `contract_gap` | FCF-02-2 action/feedback work locked |

The result is not “the frontend lacks a consumer”. Consumers exist. The producer
does not currently publish enough semantic identity for those consumers to
preserve the business fact without guessing.

## CFG-GAP-02 · Page Block business-value carrier

### Declared producer

`addons/smart_construction_core/services/scene_block_schema.py`

- `BLOCK_SCHEMA` requires display-shell fields such as `key`, `type`, `title`,
  `value`, `items`, `model`, `view_mode` and `target`.
- `_page_block()` emits `key`, `block_type`, `title`, `subtitle`, `priority`,
  `tone`, `data_source` and simplified `actions`.
- `_dataset()` emits a heterogeneous `value`, count, label and optional target,
  but no field identity or value-type declaration.

`addons/smart_core/core/page_contracts_builder.py`

- `_build_page_orchestration()` links a block to a `data_source`.
- `page_orchestration_data_provider.py` describes only the source provider,
  page/section identity and section tag. It explicitly declares
  `no_business_fact_authority`.

### Runtime contract readback

The checked-in `workspace.home` intent snapshot contains metric rows with:

```text
action_key, hint, key, label, target, tone, value
```

The values are raw JSON numbers, including a legitimate zero. Blocks contain:

```text
actions, block_type, data_source, key, priority, subtitle, title, tone
```

There is no field name, type, `componentKey`, digits, currency, unit, selection,
relation identity, temporal semantics or attachment role in the block value
carrier.

### Current consumer result

The current call chain is:

```text
page_orchestration
  -> ZoneRenderer.resolveDataset(data_source)
  -> BlockRenderer
  -> BlockMetricRow / BlockRecordSummary / BlockRecordTable / BlockProgressSummary
  -> String() / JSON.stringify()
```

Observed consequences:

- A metric number reaches `BlockMetricRow` but the block cannot distinguish
  money, percentage, duration, quantity or a plain count.
- `BlockRecordSummary` renders an object value as `--`.
- `BlockRecordTable` renders an object value with `JSON.stringify()`.
- `BlockProgressSummary` currently applies local unit, rounding and clamping
  rules; those are FCF-02-3 defects and demonstrate why the source fact is not
  sufficient.

Positive boundary:

- A JSON number is not converted before reaching the Page Block component.
- `0` is not collapsed by the current metric component.

Negative boundary:

- Raw type or numeric presence alone is insufficient: the same `0` has different
  business meaning as money, percentage, count or duration, and no declaration
  tells the renderer which meaning applies.

### Decision

`contract_gap`.

Business judgment is affected because a value can be numerically visible while
its unit, precision, currency, identity or relation meaning is lost. FCF-02-2
must not repair this by displaying a generic number with a guessed suffix.

Responsibility:

- Primary owner: P0 producer declaration for a Page Block value carrier.
- P1 industry block assembly may consume that carrier but must not define a
  competing semantic schema.
- Frontend implementation starts only after the declaration is reviewable and
  complete.

## CFG-GAP-04 · Attachment identity and role

### Existing partial declarations

Three partial carriers currently exist:

1. Form collaboration contract
   (`addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py`
   and `page_assembler.py`) declares attachment enablement, upload/download
   intents, labels and delete policy.
2. Chatter timeline
   (`addons/smart_core/handlers/chatter_timeline.py`) emits a stable attachment
   `id`, name, mimetype, `can_download`, `download_intent`, `can_delete` and
   `delete_intent`.
3. Native Contract V2 structure
   (`unified_page_contract_v2_assembler.py`) can declare an `attachment_zone` or
   attachment container, but the checked-in collaboration semantic snapshot only
   carries:

   ```json
   {
     "type": "attachment_block",
     "data": {
       "enabled": true,
       "field": "attachment_ids"
     }
   }
   ```

One2many attachment rows infer their behavior from the relation comodel
`ir.attachment`; after FCF-02-1 they no longer infer a preview entry from a
Chinese label or count text.

### Missing unified semantics

The inspected declarations do not provide one attachment contract containing all
of the following:

- stable attachment identity;
- owning model and record identity;
- explicit semantic role such as bill evidence, collaboration attachment or
  workflow evidence;
- supported preview/download action;
- deletion authorization and disabled reason;
- failure reason code, message and trace identity.

The form, chatter, One2many and Contract V2 paths therefore expose partial,
surface-specific attachment facts rather than one contract that every renderer
can consume faithfully.

### Boundary examples

Positive:

- An authenticated chatter attachment with an ID and
  `download_intent=file.download` is a strong partial action declaration.
- An ordinary integer or arbitrary text URL is not treated as a stable
  attachment identity by the shared value authority.

Negative:

- The same attachment identifier has no contract-level semantic role across the
  form attachment field, collaboration timeline and Page Block contexts.
- A read-only Page Block or attachment zone does not receive enough information
  to enable preview/download without inspecting unrelated form or timeline data.
- Failure feedback is component-local text, not a declared reason/message/trace
  result.

### Decision

`contract_gap`.

Business judgment is affected because users can see an attachment count or an
attachment-shaped value without a stable, authorized way to identify and act on
the file. FCF-02-2 must not recreate attachment identity from labels, counts,
URLs or model-name assumptions.

Responsibility:

- P0 producer declaration for attachment identity, ownership, role, action and
  failure semantics.
- Existing governed file upload/download/delete APIs remain the execution
  authority and must not be bypassed.

## CFG-GAP-05 · Page Block action and feedback

### Existing partial declarations

`page_contracts_builder.py` can publish an `action_schema` entry with:

```text
label, intent, target, visibility
```

The current system-init contract readback confirms `target` and role visibility.
`scene_block_schema.py` can place a target in a dataset row and create a simple
block action key and label.

The Page Block orchestration type currently carries action `key`, `label`,
`intent` and `target`; it does not carry a resolved permission result.

### Current consumer result

- `PageRenderer` renders global actions without a disabled binding or reason.
- Metric, entry, todo and alert blocks forward an action key and optional item.
- Several block components synthesize `open_scene` when an item action key is
  absent. That is a frontend fallback, not an authoritative action declaration.
- A failed action has no block-level contract for `reasonCode`, message or trace
  identity; page-level error plumbing cannot prove which block action failed or
  why it was disabled.

Positive boundary:

- A declared `target` can be forwarded unchanged through the UI event.
- Some action schemas declare role/capability visibility.

Negative boundary:

- Visibility is not the same as a resolved permission result.
- The visible action may have no target, disabled reason or failure identity.
- Permission denial and backend failure cannot be represented consistently per
  action without component-local inference.

### Decision

`contract_gap`.

Business judgment is affected because a user may be shown an action that is not
executable and receive no authoritative reason, trace or recovery message. The
frontend must not decide whether the action is allowed from role labels or
action names.

Responsibility:

- P0 producer declaration for action target, permission result, enabled/disabled
  state, disabled reason, error reason code, message and trace identity.
- Existing action execution and authorization services remain the only decision
  authority.

## Minimum P0 remediation shape

The smallest coherent producer change is three explicit, versioned carriers:

1. **Block value**

   - field identity and complete applicable descriptor;
   - raw JSON value with its type;
   - currency/unit/precision/selection/relation/temporal/attachment role;
   - no formatted display string as the only value.

2. **Attachment value**

   - attachment ID;
   - owning model and record identity;
   - semantic role;
   - preview/download/delete capability and authorization result;
   - failure reason, message and trace identity.

3. **Block action/feedback**

   - resolved target;
   - permission result and disabled reason;
   - error reason code, message and trace identity;
   - explicit action identity that can be joined to the backend result.

These are declaration and decode requirements, not a new runtime. Existing
Contract V2 and the existing action/file services should be extended or consumed.

## Dependency decision

`CFG-GAP-02`, `CFG-GAP-04` and `CFG-GAP-05` all resolve to `contract_gap`.

Therefore:

1. FCF-02-2 product implementation remains locked.
2. No frontend default, label inference, URL test, role label or component-local
   reconstruction may unlock it.
3. The next product batch must be a separately reviewed P0 producer remediation.
4. After producer implementation and consumer decode are reviewed and verified,
   the probe status must be re-evaluated at the new exact source identity.

This result approves the need for a P0 producer batch. It does not approve a
particular schema design or authorize implementation in this branch.
