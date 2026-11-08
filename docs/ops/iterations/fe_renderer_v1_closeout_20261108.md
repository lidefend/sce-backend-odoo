# FE-RENDERER-V1 Closeout

## Identity

- Goal: `FE-RENDERER-V1-CLOSEOUT`
- Branch: `fix/fe-renderer-02c-02b-02-sc-adapter-phase1-20261108`
- PR: #845
- Current product/evidence head: `0ef405468dc28a1aab0f4dc48dc9b6e90dd721fa`
- Later metadata-only commits do not change the product tree or re-bind L4.
- Fourth-review product fixes: `476cb6278`, `8c0876c2f`, `986e60535` and `0ef405468`
- Previously reviewed head: `ba5d4b53f7e19748669cce34c9f144fedb4aa5ba`
- Previous reviewed head: `12ea32ecd2fca13d5abff8ce7c4008c5bc991360`
- Previous L4/metadata candidate: `866afcb11e16d67c18cf7d2035fc954b95b0bade`
- L4 evidence/P4 candidate: `79e0e704af2fbdbd6046a1b960da857083181fc6`
- Original PR head: `7d3ed98979c17125b3dc987c26fcf6df3f1be701`
- Remote main at start: `f1ba79c173c4701c642b3e505daf33c7aaaedfb9`
- Worktree was clean at the `0ef405468` L4 checkpoint.

## Scope

FE-RENDERER-V1 proves contract-driven uniform TDesign component delivery for the
standard business-page mainline. It does not require all pages to use
`FormSection`, does not turn all 25 `componentKey` values into independent
professional controls, and does not introduce a new renderer runtime.

## Workstreams

- A: Textarea/Input runtime event truthfulness and exact-count Chromium regression.
- B: reconciliation of 25 `componentKey` identities, renderer families,
  implementations and product consumers.
- C: verification of 33 product-required official TDesign component takeovers
  and three real business-page acceptance surfaces.
- Total control: public mapping, registry wiring, integration, evidence and final
  V1 delivery decision.

The delegated executor channel failed to resume after creation and accepted no
work. All scoped work was therefore executed sequentially by total control; no
PASS was inherited from an inactive executor.

## Baseline Facts

- Semantic registry source currently declares 25 component keys.
- The renderer union currently contains five names.
- `FormSectionField` is the generic type-directed sentinel.
- Four independent professional controls exist: BaseField, BusinessValue,
  RelationField and DetailCollection.
- Current driver inventory reports 33 required `apps/web` adapters present, with
  zero missing, bridge-only, raw behavioral or direct vendor-import bypasses.
- `frontend/packages/ui/src` is outside that scan boundary: its legacy Scene
  primitives and TDesign driver imports are explicitly recorded and are not
  presented as repository-wide zeroes.
- PR #845 four required checks succeeded on `7d3ed9897`; that evidence does not
  apply after later edits.

## Results

### V1 delivery chain

```mermaid
flowchart LR
  A[Odoo native model/view/workflow facts] --> B[Contract V2 assembler]
  B --> C[semantic.yaml / component.yaml]
  C --> D[semantic_registry.generated.ts]
  D --> E[professionalComponentRegistry resolver]
  E --> F[FormSectionField or four professional controls]
  F --> G[Sc Design System]
  G --> H[TDesign bridge / official component]
```

The component vocabulary has one declaration authority (`semantic.yaml` and
`component.yaml`), one generated frontend carrier and one runtime resolver. This
closeout does not add a parallel component-key table or a second renderer runtime.

### P0 runtime event closure

The duplicate Textarea `change` was traced to two competing authorities:

- TDesign/ScTextarea emitted a change while the controlled control was still
  handling the edit;
- ScSceneTextarea then synthesized another change from blur.

The scene adapter now owns the native DOM event boundary. It captures `input`
before a controlled driver can restore the old value, emits `update:modelValue`
and `input` only for an actual value transition, and commits `change` against
the last committed value. Real native change and blur cannot both commit the same
edit. No debounce, timer window or value-equality timer is used.

Chromium `147.0.7727.15` real-SFC evidence:

- 87 exact assertions, 0 console errors;
- three typed Input characters produce exactly three `update` and three `input`
  events;
- one Input edit commit produces exactly one `change`;
- one Textarea fill produces exactly one `update`, one `input` and one `change`;
- `update` precedes the committed `change`, and blur does not repeat it;
- disabled/readonly DOM input attempts produce zero model updates;
- Chromium CDP IME composition produces `compositionstart`,
  `compositionupdate`, a committed value and one final `input`; forwarding of
  `compositionend` is separately asserted with a browser-dispatched
  `CompositionEvent` because headless Chromium does not emit the native end
  event through CDP;
- name, inputmode, ARIA, required, error and Textarea element identity remain
  intact.
- if a user draft is replaced by an external controlled `modelValue` update
  before blur, neither Input nor Textarea emits a stale draft `change`; blur
  reports the displayed controlled value.

The latest owner review found that coalesced echoes were matched by concatenating
complete input snapshots. That could mistake a legitimate external value `aab`
for the snapshot sequence `a` + `ab`. The concatenation path is removed: delayed
echoes now match only complete, ordered snapshot values. Input and Textarea
Chromium regressions cover `a -> ab -> external aab -> blur`, including a late
echo, with zero stale changes. All three echo-history queues are bounded to 256
entries so a long-lived control cannot accumulate unbounded history. The browser
suite now has 87 exact assertions and rejects reintroduction of snapshot
concatenation.

The fourth review then found that TDesign date-picker calendar callbacks carry
no native `e`. `ScDateField` now always normalizes the value transition and
emits a synthetic untrusted `change` event when the vendor supplied only its
semantic callback context. A synchronous last-committed-value authority also
prevents the two internal TDesign clear callbacks from producing duplicate
update/change pairs. Chromium selects `2026-11-15` and clears the field with
exactly one update and one change for each transition, and both operations
carry `source=pointer`. `clearable` and the `clear` capability are now explicit
DateField Port members rather than undeclared attribute fallthrough.

The same browser proof found that `ScFormField` declared help/error content but
TDesign did not render the slots because the corresponding props were not
explicitly set. Help and tips now use TDesign's official function-valued props;
the visible text and generated IDs match the control's `aria-describedby`.

The real Contract V2 action path exposed a reason-contract gap that the direct
dialog fixture could not see. Backend action rules carry reason authority in
`presentation.requires_reason`; the frontend action projection now consumes that
declared field, so the decoded reject rule opens the dialog even when top-level
`requires_reason` and `required_params` are absent from the normalized carrier.
The test now goes through snapshot decode, store resolution and action
projection. Canceling the dialog resolves as a deliberate no-op rather than
reporting a missing-reason error.

The fifth independent review (`REQUEST_CHANGES` on `e8f954876`) identified the
same real-V2 reason boundary, undeclared DateField clearability/provenance,
cancel error and stale evidence identity. Product commit `986e60535` addresses
the first three; this closeout carries the resulting L4/manifest evidence to
the new head.

### First-review follow-up

The first independent review identified two boundaries that were not yet pinned:

- Input/Textarea did not distinguish a user-driven model echo from a genuinely
  external controlled-value reset;
- collection create capability had product behavior but no executable
  missing/false/true regression boundary.

The scene adapters now track ordered pending user echoes and superseded echoes.
A delayed parent echo cannot replace a newer external server value. On commit,
they use the displayed DOM value only when it is the current controlled value;
otherwise they use the latest user edit.

ActionView now delegates create visibility to
`resolveCollectionCreateAuthority`. Direct `record_create` targets require the
declared effective `create=true` capability. Delegated `action` targets consume
the producer-authorized `list.create` rule and complete action/menu identity
without incorrectly requiring direct create. Eleven executable cases cover
missing, false and true direct capability; authorized delegated actions; absent
or unauthorized rules; incomplete targets; and invalid identity.

The local review and first independent-review follow-up also closed:

- delayed parent echo versus newer external server state;
- pointer/keyboard/programmatic focus provenance, including Tab entry;
- passive Table rows emitting row activation;
- an unnamed non-decorative Icon;
- unrelated same-file Sc tags inflating TDesign adapter attribution.

The second independent review then found the remaining coalesced-delay boundary
and a TypeScript blind spot in the generated takeover inventory. Product commit
`f88e49d59` now:

- treats all outstanding user echoes as an ordered queue, accepts a coalesced
  latest echo, and keeps stale history across a resumed edit after an external
  server update;
- tombstones values acknowledged by a newer/coalesced echo, so an older echo
  arriving afterward cannot replace the newest value;
- validates the non-decorative Icon label reactively, so a post-mount prop change
  also fails closed;
- scans `.ts` and `.js` source for raw behavioural APIs, with a negative test for
  `window.prompt`;
- maps `TDesignRadioGroup` to the radio driver and Layout `Aside/Header/Content/
  Footer` subcomponents to the Layout driver;
- replaces the Contract Form action-reason `window.prompt` path with the
  contract-local `ContractReasonDialog`, built from ScDialog, ScFormField,
  ScTextarea and ScButton;
- consumes backend-declared `presentation.reason_input` copy and fails closed
  when a required reason action omits any title, label, help or action copy.

The takeover inventory now reports two real bridge-consumer bypasses rather than
hiding them: `NativeFormTreeRenderer` for alert input and
`ProfessionalManyToManySelect` for select input.

The fourth-review browser harness now mounts the real `ContractReasonDialog`
through `collectActionParams`. It asserts the exact backend-declared copy,
cancel emits no operation request, and submit emits exactly one trimmed reason
payload. The same run verifies visible FormField help/error content and its ARIA
association.

The development-incremental route was corrected so ActionView create-boundary
inputs select their executable contract target, and scene text changes select
the real browser behavior target. The routing itself is covered by 87 non-zero
unit tests; this is P4 verification plumbing, not product behavior.

### P1 componentKey reconciliation

The generated platform carrier contains 25 field component keys. `component.yaml`
also contains two node identities (`sc.feedback.message`, `sc.navigation.anchor`);
the semantic lint total of 28 components includes those two node identities plus
the industry payment key. The V1 field reconciliation below is exactly 25 rows.

`FormSectionField` is the type-directed sentinel. It is not one of the four
independent professional controls.

| componentKey | semantic | field types | renderer | actual implementation | TDesign target | product consumer | status |
|---|---|---|---|---|---|---|---|
| `sc.input.text` | text | char | `FormSectionField` -> `ProfessionalBaseFieldControl` | ScInput | TDesignInput | Contract Form FormSection/PBF | ready |
| `sc.input.binary` | binary | binary | `FormSectionField` | ScFileField | TDesignUpload | FormSection binary branch | ready |
| `sc.input.textarea` | long_text | text, html | `FormSectionField` -> `ProfessionalBaseFieldControl` | ScTextarea; RestrictedHtmlEditor for html | TDesignTextarea | Contract Form FormSection/PBF | ready, HTML uses the governed editor |
| `sc.input.number` | number | integer, float, monetary | `FormSectionField` -> PBF for integer/float; sentinel monetary branch | ScNumberInput; ScInput for monetary | TDesignInputNumber; TDesignInput | Contract Form FormSection | ready, split implementation |
| `sc.select.remote` | choice | selection | `FormSectionField` -> PBF | ScSelect | TDesignSelect | Contract Form FormSection/PBF | ready |
| `sc.input.boolean` | boolean | boolean | `FormSectionField` -> PBF | ScCheckbox | TDesignCheckbox | Contract Form FormSection/PBF | ready |
| `sc.input.date` | date | date | `FormSectionField` -> PBF | ScDateField | TDesignDatePicker | Contract Form FormSection/PBF | ready |
| `sc.input.datetime` | datetime | datetime | `FormSectionField` -> PBF | ScDateField `with-time` | TDesignDatePicker | Contract Form FormSection/PBF | ready |
| `sc.table.data` | detail_table | one2many, many2many | `FormSectionField` | generic collection/table path; no dedicated form control | ScTable/TDesignTable on table surfaces | ui.contract.v2 table projection | declared; specialized form consumer not proven |
| `sc.tree.data` | hierarchical_collection | one2many, many2many | `FormSectionField` | no dedicated Contract Form control owned by this key | governed hierarchy surface | hierarchical worksheet contract | declared; not a universal FormSection consumer |
| `sc.relation.many2one` | relation | many2one | `ProfessionalRelationFieldControl` | ProfessionalRelationFieldControl / ProfessionalMany2oneFieldControl -> ScRelationField | TDesignSelect | Contract Form FormSection | ready |
| `sc.relation.many2many` | relation_collection | many2many | `ProfessionalRelationFieldControl` | ProfessionalRelationFieldControl -> X2ManyRelationRenderer | TDesignSelect/Table by relation mode | Contract Form FormSection | ready |
| `sc.relation.table` | detail_collection | one2many | `ProfessionalDetailCollectionControl` | ProfessionalDetailCollectionControl -> X2ManyRelationRenderer | TDesignTable | Contract Form FormSection | ready |
| `sc.select.tags` | tag_collection | many2many | `ProfessionalRelationFieldControl` | X2ManyRelationRenderer -> ProfessionalManyToManySelect | TDesignSelect | formSection.mapper for tag collections | ready |
| `sc.button.action` | action | action | `FormSectionField` | generic action/form-action presentation | ScButton/TDesignButton | Contract action presentation | declared; not a form field edit control |
| `sc.auth.credential_entry` | credential_entry | char | `FormSectionField` | generic field infrastructure; no dedicated current product consumer | ScInput/TDesignInput | declaration-only in current product search | ready identity, consumer pending |
| `sc.auth.secret_confirmation` | secret_confirmation | char | `FormSectionField` | generic field infrastructure; no dedicated current product consumer | ScInput/TDesignInput | declaration-only in current product search | ready identity, consumer pending |
| `sc.auth.challenge_status` | challenge_status | char, selection, text | `FormSectionField` | generic field infrastructure; no dedicated current product consumer | ScInput/ScSelect | declaration-only in current product search | ready identity, consumer pending |
| `sc.auth.one_time_secret` | one_time_secret | char, text | `FormSectionField` | fail-closed declaration; no editable implementation | none by design | auth backend only in current search | fail-closed |
| `sc.auth.support_action` | support_action | action | `FormSectionField` | generic action infrastructure; no dedicated current product consumer | ScButton/TDesignButton | declaration-only in current product search | ready identity, consumer pending |
| `sc.value.money` | money | monetary | `ProfessionalBusinessValueControl` | ProfessionalBusinessValueControl -> ScMoney/ScInput | no vendor for ScMoney; TDesignInput for edit | Contract Form business values | ready |
| `sc.value.percentage` | percentage | float, integer | `ProfessionalBusinessValueControl` | ProfessionalBusinessValueControl -> ScInput | TDesignInput | Contract Form business values | ready |
| `sc.display.status` | status | selection, char | `ProfessionalBusinessValueControl` | ProfessionalBusinessValueControl -> ScStatusBadge/ScSelect | TDesignTag/TDesignSelect | Contract Form status values | ready |
| `sc.value.duration` | duration | float, integer | `ProfessionalBusinessValueControl` | ProfessionalBusinessValueControl -> ScInput | TDesignInput | Contract Form business values | ready |
| `sc.display.text` | readable_value | `*` | `FormSectionField` | readonly fact or generic ScInput fallback | no vendor for readonly text; TDesignInput when editable | Contract Form facts | ready |

No duplicate componentKey registration was found. The principal remaining
inconsistency is not duplicate vocabulary but split implementation for
`sc.input.number` (number versus monetary) and collection/auth identities whose
consumer is a generic host or declaration-only. V1 must not invent dedicated
controls merely to make every key map one-to-one.

### P2 official TDesign takeover

The authoritative generated inventory is
`docs/frontend_productization/rendering-detail/component-driver-takeover-inventory-v1.json`.
The published scope is exactly `frontend/apps/web/src` production sources,
excluding the design-system adapter layer. `frontend/packages/ui/src` contains
active legacy Scene primitives and TDesign driver imports; it remains outside the
FE-RENDERER-V1 takeover count and is explicitly listed in `scopeExclusions`.

Current `apps/web` result:

- official components inventoried: 71;
- product-required components: 33;
- adapter-present: 33;
- missing: 0;
- bridge-only: 0;
- adapter-unconsumed: 0;
- unassessed required takeover: 0;
- raw behavioral surface: 0;
- direct vendor-import bypass: 0;
- bridge-consumer bypasses: 2, explicitly recorded;
- non-required components: 38, not defects and not forcible takeover targets.

The 33 required drivers are:

| official driver | adapter key(s) | production consumer count | status |
|---|---|---:|---|
| alert | ScErrorState, ScInlineState | 80 | adapter present; bridge consumer bypass: `NativeFormTreeRenderer` |
| badge | ScBadge | 1 | adapter present |
| button | ScButton, ScIconButton | 464 | adapter present |
| card | ScCard, ScPanel | 87 | adapter present |
| checkbox | ScCheckbox | 14 | adapter present |
| collapse | ScCollapse, ScDisclosure | 10 | adapter present |
| date-picker | ScDateField, ScDatePicker | 4 | adapter present |
| descriptions | ScDescriptions | 5 | adapter present |
| dialog | ScDialog | 16 | adapter present |
| drawer | ScDrawer | 3 | adapter present |
| dropdown | ScDropdown | 5 | adapter present |
| empty | ScEmptyState | 34 | adapter present |
| form | ScForm, ScFormField, ScFormItem | 28 | adapter present |
| input | ScInput | 62 | adapter present |
| input-adornment | ScInputGroup | 1 | adapter present |
| input-number | ScNumberInput | 1 | adapter present |
| layout | ScAside, ScContent, ScFooter, ScHeader, ScLayout | 7 | adapter present |
| list | ScList | 8 | adapter present |
| loading | ScInlineState, ScLoading | 77 | adapter present |
| menu | MenuTree | 1 | adapter present |
| pagination | ScPagination | 1 | adapter present |
| progress | ScProgress | 1 | adapter present |
| radio | ScRadio, ScRadioGroup | 6 | adapter present |
| select | ScRelationField, ScSelect | 46 | adapter present; bridge consumer bypass: `ProfessionalManyToManySelect` |
| skeleton | ScSkeleton | 1 | adapter present |
| space | ScActionBar | 4 | adapter present |
| table | ScTable | 24 | adapter present |
| tabs | ActivityPageTabs, ScTabs | 3 | adapter present |
| tag | ScStatusBadge | 16 | adapter present |
| textarea | ScTextarea | 9 | adapter present |
| timeline | ScTimeline | 1 | adapter present |
| tooltip | ScTooltip | 1 | adapter present |
| upload | ScFileField, ScUpload | 3 | adapter present |

This proves structural adapter and consumer presence. It does not assert that
every production consumer already routes through Sc, nor that every
prop/event/slot combination of every driver has a dedicated browser test. The
two remaining bridge-consumer bypasses are explicit boundaries, not hidden
coverage.

### P3 real business-page acceptance

All three pages ran against the managed isolated Acceptance profile:

- project `sc-fe-r2-p1-01`;
- database `sc_frontend_acceptance`;
- backend port `18082`;
- standard preview `5180`;
- backend and preview both observed served revision `0ef405468`.

The fixture password was supplied through the existing Make secret variable and
was not written to the report, run record or logs.

| sample | governed evidence | result |
|---|---|---|
| Contract Form | `verify.frontend.contract_form_presentation.browser` | PASS: `sc.general.contract/2`, action 758/menu 664, 1440/1024/768/390, 0 overflow, 0 console/page/http errors |
| Payment Request | `verify.frontend.business_entry.payment_request.browser` | PASS: `FE-DELIVERY-HARDENING-001`, two declared settlement rows, inline edit 200→150 persisted, restored to row count 0 / amount 20.00, 0 problems |
| Scene Collection | `verify.frontend.list_surface_structure.browser` | PASS: full list matrix, 18 normal/batch/empty × viewport states, 0 failures |
| Scene Collection table identity | `verify.frontend.business_entry.matrix.browser` | PASS: project ledger menu 382/action 590, four rows, row search/detail contract, direct create=false, authorized delegated `项目立项` action 795, rendered create affordance=true, edit=true, expected negative 403 retained |
| Relation roundtrip | `verify.frontend.relation_roundtrip.browser` | PASS: 13 declared entries, 7 contract comparisons, 3 records opened, 0 blocking differences, 0 denied/console errors |

Machine evidence:

- `.runtime/final-acceptance/contract-form-presentation/contract/summary.json`
  and four viewport PNGs, SHA256
  `f24b9a57709ab6073eb24a56f43d7a6bf2637d287fa39a7a16d0f390b15fbb4d`;
- `.runtime/final-acceptance/payment-request/0ef405468/report.json`
  and `after-save.png`, report SHA256
  `818a86cd05eb22caec9315f420703a43a58d49c417534a27c252b7f108436d29`;
- `.runtime/final-acceptance/list-surface-structure.json` and its 18 screenshots,
  SHA256
  `ff84acf265f8ebb4d1c5780f96e5bcddf4ff5e69d4e09b31782b02caed54e064`;
- `.runtime/acceptance/local/98a9f76c29688f1aa6a85b6add205fbbf7752cd3/relation-roundtrip/20261108T203832097Z-3349383-07c20af8/summary.json`,
  SHA256
  `0e29b879901f6be3dcea65891a6bd57086e68eeed34ade6f94e88195a342c11e`.
  This relation probe has no DateField, reason-action or primitive-Port input;
  its unchanged suite fingerprint is carried to `0ef405468`.
- `.runtime/acceptance-evolution/evidence.v1.json` is recorded at merge stage:
  list surface and relation roundtrip retain their validated evidence heads and
  are carried to the final metadata tip; deployment-only
  `path_namespace_identity` is explicitly deferred. The final runtime hash is
  reported from the current file after the metadata commit.

Two reproducible product defects were found and fixed during L4:

1. collection create was rendered from `list.create` even when the runtime
   effective record capability declared `create=false`;
2. the controlled list search listened only to `input`, so a driver that emitted
   `update:modelValue` rolled typed text back to empty and prevented empty-state
   search.

Neither fix changes ACL, Contract V2 or business data authority.

### P4 architecture and duplication audit

- Contract V2 remains the runtime authority; no Contract V2 rewrite was made.
- The frontend semantic vocabulary remains generated from the declaration files;
  no second componentKey list was added.
- `FormSectionField` remains the explicit generic sentinel; the four independent
  professional controls remain BaseField, BusinessValue, RelationField and
  DetailCollection.
- No required official driver is missing, bridge-only or raw.
- Reused Sc adapters across multiple TDesign drivers (for example ScButton across
  alert/button/collapse/tabs/upload) are shared semantic adapters, not duplicate
  registries.
- The legacy `SceneUiProvider` remains the scene-composition host and still has
  active consumers in `ContractFormDriverHost`, `SceneReadonlyCollectionRenderer`
  and `@sc/ui` scene surfaces. No zero-consumer deletion is justified.
- `ContractFormPage` still has the canonical/legacy selection boundary around
  `canonicalProductRendererActive`; consolidating it is excluded as
  `FE-FORM-CONSOLIDATION-01`.
- Page Assembly, ActionView and HomeView remain independent follow-ups:
  `FE-PAGE-01`, `FE-ACTION-01`, `FE-HOME-01`.
- The project-ledger acceptance probe now distinguishes direct record creation
  from an authorized delegated `list.create` action. The first run incorrectly
  treated the rendered delegated-create affordance as a direct capability
  mismatch; the corrected probe binds the complete action/menu identity without
  changing product authority.
- The relation acceptance probe now recognizes `--`, `—` and `–` placeholders as
  empty values. This corrected the false claim that empty owner/cost/document
  relations lacked public controls; the rerun opened the three actually populated
  relations.
- The managed local preview now binds Vite's dev/HMR client port to its actual
  service port, and stale-listener recovery recognizes the real
  `vite/bin/vite.js` command shape. These are P4 environment fixes; no business
  route or local.dev projection was changed.
- Suite input fingerprints are revision-stable. Historical evidence no longer
  changes hash merely because the inspected revision is not the current
  checkout, so metadata-only or unrelated product commits cannot falsely
  invalidate acceptance evidence.

### Current acceptance state

L4 passed at served revision `0ef405468` for Contract Form, Payment Request and
Scene Collection. Relation roundtrip executed at `98a9f76c` and is carried only
because its declared suite inputs are unchanged. The merge-stage
acceptance manifest records the suite-specific bound heads and is carried to the
final metadata tip; the deployment-only
`path_namespace_identity` suite is deferred explicitly rather than represented
as passed. No page evidence was inherited from `866afcb11` or older candidates.

The complete affected incremental iteration passed all 24 required targets with
non-zero execution:

- Acceptance evolution binding;
- Acceptance runtime tooling;
- Agent ledger;
- Agent resume;
- ActionView create authority;
- ActionView page-size runtime;
- ActionView surface gate;
- Business-entry evidence scope and incremental model;
- Canonical form presenter;
- Component driver takeover inventory;
- Contract-basis unit and enforce;
- Contract header action projection;
- Delivery-hardening probe toolchain;
- Development-incremental routing unit;
- frontend lint;
- page-pattern reference parity;
- Primitive Adapter;
- Primitive Port;
- Product page pattern;
- Scene Primitive Adapter;
- real Scene Primitive behavior;
- Standard preview tooling;
- static proxy target;
- style-system guard;
- strict UI/web typecheck.

Receipt:
`.runtime/frontend-dev-validation/executions/20261108T220455Z-3940103-933294859/receipt.json`.

The frontend production build passed on the same product content: 5,375 modules
transformed in 23.77 seconds. The existing large-chunk advisory remains.

Overall V1 remains `verification_pending` only for publication, fresh independent
review and exact-head remote CI. The metadata-only closeout is complete; the
manifest intentionally stays bound to product/evidence head `0ef405468`.

## Exclusions

Page Assembly, ActionView, HomeView and legacy/canonical form consolidation are
registered follow-up work, not V1 blockers.

## Next Exact Step

Commit the final L4/evidence metadata, publish the clean candidate through the
governed PR flow, and request a fresh independent review bound to the exact
pushed head. Do not merge or deploy.
