# FE-RENDERER-V1 Closeout

## Identity

- Goal: `FE-RENDERER-V1-CLOSEOUT`
- Branch: `fix/fe-renderer-02c-02b-02-sc-adapter-phase1-20261108`
- PR: #845
- Current second-review product commit: `f88e49d5901119489eda5aa8ffd001042f346412`
- Previous reviewed head: `12ea32ecd2fca13d5abff8ce7c4008c5bc991360`
- Current L4/metadata candidate: `866afcb11e16d67c18cf7d2035fc954b95b0bade`
- Original PR head: `7d3ed98979c17125b3dc987c26fcf6df3f1be701`
- Remote main at start: `f1ba79c173c4701c642b3e505daf33c7aaaedfb9`
- Worktree was clean at the L4 acceptance checkpoint.

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
- Current driver inventory reports 33 required adapters present, with zero missing,
  bridge-only, raw behavioral or direct vendor-import bypasses.
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

- 59 exact assertions, 0 console errors;
- three typed Input characters produce exactly three `update` and three `input`
  events;
- one Input edit commit produces exactly one `change`;
- one Textarea fill produces exactly one `update`, one `input` and one `change`;
- `update` precedes the committed `change`, and blur does not repeat it;
- disabled/readonly DOM input attempts produce zero model updates;
- native IME `compositionstart`, `compositionupdate` and `compositionend` are
  observed; Input/Textarea `compositionstart`/`compositionend` are forwarded;
- name, inputmode, ARIA, required, error and Textarea element identity remain
  intact.
- if a user draft is replaced by an external controlled `modelValue` update
  before blur, neither Input nor Textarea emits a stale draft `change`; blur
  reports the displayed controlled value.

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
- pointer/programmatic focus provenance;
- passive Table rows emitting row activation;
- an unnamed non-decorative Icon;
- unrelated same-file Sc tags inflating TDesign adapter attribution.

The second independent review then found the remaining coalesced-delay boundary
and a TypeScript blind spot in the generated takeover inventory. Product commit
`f88e49d59` now:

- treats all outstanding user echoes as an ordered queue, accepts a coalesced
  latest echo, and keeps stale history across a resumed edit after an external
  server update;
- preserves the user's newest edit when an older coalesced echo arrives late;
- validates the non-decorative Icon label reactively, so a post-mount prop change
  also fails closed;
- scans `.ts` and `.js` source for raw behavioural APIs, with a negative test for
  `window.prompt`;
- maps `TDesignRadioGroup` to the radio driver and Layout `Aside/Header/Content/
  Footer` subcomponents to the Layout driver;
- replaces the Contract Form action-reason `window.prompt` path with the
  contract-local `ContractReasonDialog`, built from ScDialog, ScFormField,
  ScTextarea and ScButton.

The takeover inventory now reports two real bridge-consumer bypasses rather than
hiding them: `NativeFormTreeRenderer` for alert input and
`ProfessionalManyToManySelect` for select input.

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
Current result:

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
| button | ScButton, ScIconButton | 462 | adapter present |
| card | ScCard, ScPanel | 87 | adapter present |
| checkbox | ScCheckbox | 14 | adapter present |
| collapse | ScCollapse, ScDisclosure | 10 | adapter present |
| date-picker | ScDateField, ScDatePicker | 4 | adapter present |
| descriptions | ScDescriptions | 5 | adapter present |
| dialog | ScDialog | 15 | adapter present |
| drawer | ScDrawer | 3 | adapter present |
| dropdown | ScDropdown | 5 | adapter present |
| empty | ScEmptyState | 34 | adapter present |
| form | ScForm, ScFormField, ScFormItem | 27 | adapter present |
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
- backend and preview both bound to the product candidate.

The fixture password was supplied through the existing Make secret variable and
was not written to the report, run record or logs.

| sample | governed evidence | result |
|---|---|---|
| Contract Form | `verify.frontend.contract_form_presentation.browser` | PASS: `sc.general.contract/2`, action 758/menu 664, 1440/1024/768/390, 0 overflow, 0 console/page/http errors |
| Payment Request | `verify.frontend.business_entry.payment_request.browser` | PASS: `FE-DELIVERY-HARDENING-001`, two declared settlement rows, inline edit 200→150 persisted, restored to row count 0 / amount 20.00, 0 problems |
| Scene Collection | `verify.frontend.list_surface_structure.browser` | PASS: full list matrix, 18 normal/batch/empty × viewport states, 0 failures |
| Scene Collection table identity | `verify.frontend.business_entry.matrix.browser` | PASS: project ledger menu 382/action 590, four rows, row search/detail contract, direct create=false, authorized delegated `项目立项` action 795, rendered create affordance=true, edit=true, expected negative 403 retained |

Machine evidence:

- `.runtime/final-acceptance/contract-form-presentation/contract/summary.json`
  and four viewport PNGs, SHA256
  `802dce545ec1f5417f4074bab88c9d4b5d2cc15dea3b9773aec969654511a0a6`;
- `artifacts/frontend-business-entry-payment-request/1794158165902/report.json`
  and `after-save.png`, report SHA256
  `3cc3c0e8780c3319c4f32bc88d23c7db9804aa901f511585a0fd5350465d5e18`;
- `.runtime/final-acceptance/list-surface-structure.json` and its 18 screenshots,
  SHA256
  `75f3f3f8df6c5314cf8430f595da1efe57c389aaceb42399c1a0a34c4acf8117`;
- `.runtime/final-acceptance/scene-collection-table/866afcb11/summary.json`,
  SHA256
  `22528ae103a5fc622a2cc712d62bf4db3b663c47cdbb2e2b80169dcdd3946c90`;
- `.runtime/acceptance-evolution/evidence.v1.json`, SHA256
  `1d8da7c989daf15da9d9b77816c1bf27f4aa0d9be8282f2b8858b957b4526515`.

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

### Current acceptance state

L4 product acceptance passed on candidate `866afcb11`, whose frontend product
tree is from `f88e49d59`. The managed backend and 5180 preview both reported the
candidate identity, the fixture was reset through the governed entry, and the
page evidence was not inherited from `9cea1b661`.

The complete affected incremental iteration passed all 18 required targets with
non-zero execution:

- Agent ledger;
- Agent resume;
- ActionView create authority;
- ActionView page-size runtime;
- ActionView surface gate;
- Business-entry evidence scope and incremental model;
- Canonical form presenter;
- Component driver takeover inventory;
- Contract-basis unit and enforce;
- Development-incremental routing unit;
- frontend lint;
- page-pattern reference parity;
- Primitive Adapter;
- Primitive Port;
- Product page pattern;
- Scene Primitive Adapter;
- real Scene Primitive behavior;
- style-system guard;
- strict UI/web typecheck.

Receipt:
`.runtime/frontend-dev-validation/executions/20261108T174449Z-2277077-703451500/receipt.json`.

The frontend production build passed on the same product content: 5,375 modules
transformed in 25.20 seconds. The existing large-chunk advisory remains.

Overall V1 remains `verification_pending` only for the evidence/metadata commit,
publication, fresh independent review and exact-head remote CI.

## Exclusions

Page Assembly, ActionView, HomeView and legacy/canonical form consolidation are
registered follow-up work, not V1 blockers.

## Next Exact Step

Commit this L4/metadata closeout, publish the clean candidate through the governed
PR flow, and request a fresh independent review bound to the exact pushed head.
Do not merge or deploy.
