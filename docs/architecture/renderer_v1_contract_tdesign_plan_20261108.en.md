# FE-RENDERER-V1: Contract-Driven Unified TDesign Component Delivery

- Status: V1-01/V1-02 implemented and focused tests pass; real product pages and final build pending
- Baseline: `f1ba79c173c4701c642b3e505daf33c7aaaedfb9`
- Branch: `feature/fe-renderer-v1-contract-tdesign-20261108`
- Formal Product Layer: P0 platform kernel product
- Layer Target: Frontend Contract V2 component identity, binding and unified Sc/TDesign implementation
- Module: Semantic Registry, Component Registry, Canonical Form Render Model, Professional Component Registry, FormSection, Sc Design System, TDesign Bridge
- Standard vs User-Specific: platform engineering standard
- Chinese version: [renderer_v1_contract_tdesign_plan_20261108.md](renderer_v1_contract_tdesign_plan_20261108.md)

## 1. V1 Objective

V1 delivers:

```text
Contract V2
  -> Semantic Registry
  -> Professional Component Registry
  -> Canonical Render Model
  -> componentKey + declared variant
  -> Sc component
  -> TDesign
```

It does not introduce a multi-renderer runtime, plugin marketplace, React Host or
complete Native component library. Page, Composition, Specialized and `@sc/ui`
hosts remain. V1 unifies component identity, base implementation binding and
interaction contract.

## 2. Baseline and PR #845 Identity

- Latest `origin/main`: `f1ba79c173c4701c642b3e505daf33c7aaaedfb9`
- PR #845: OPEN, MERGEABLE
- PR #845 HEAD: `7d3ed98979c17125b3dc987c26fcf6df3f1be701`
- Latest required PR checks: all SUCCESS
- Merge state: not merged

PR #845 adds 54 files and 3,423 lines relative to main. Its core is Primitive
Port, seven `ScScene*` adapters, a Provider and Conformance tests. V1 reuses only
the useful attribute, event, focus and accessibility repairs for existing Sc
components. It does not automatically inherit the seven Scene adapters as the
production architecture.

## 3. V1-00 Current-State Reconciliation

### 3.1 Declaration Scale

| Object | Count |
| --- | ---: |
| semantics | 27 |
| components | 28 |
| field components | 26 |
| platform field components | 25 |
| industry field components | 1 |
| node components | 2 |
| `Sc*.vue` components | 63 |

Twenty-two listed Sc files directly consume `tdesignPrimitiveBridge`; the others
are composition, facade or non-TDesign semantic components.

### 3.2 Real Call Chain

```text
contracts/registry/semantic.yaml
  -> contracts/registry/component.yaml
  -> scripts/contract/generate_semantic_registry.py
  -> semantic_registry.generated.ts
  -> professionalComponentRegistry.ts
  -> contractFormPresenter.resolveContractProfessionalComponent()
  -> CanonicalFormRenderModel.componentResolution
  -> canonicalFieldToFormSection()
  -> FormSectionFieldSchema
  -> FormSection
  -> professional/base controller
  -> Sc component
  -> TDesign
```

Evidence:

- `contracts/registry/semantic.yaml:90-117`
- `contracts/registry/component.yaml:41-68`
- `scripts/contract/generate_semantic_registry.py:338-396`
- `frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts:113-209`
- `frontend/apps/web/src/app/presentation/contractFormPresenter.ts:277-285`
- `frontend/apps/web/src/app/presentation/canonicalFormRenderModel.ts:38-71`
- `frontend/apps/web/src/pages/contractForm/canonicalFormRenderer.ts:163-219`
- `frontend/apps/web/src/components/template/FormSection.vue:200-406`

### 3.3 Current componentKey Implementation Map

| componentKey | Declared field types | Current implementation |
| --- | --- | --- |
| `sc.input.text` | char | `ProfessionalBaseFieldControl -> ScInput` |
| `sc.input.binary` | binary | `FormSection -> ScFileField` |
| `sc.input.textarea` | text, html | text: `ScTextarea`; html: `RestrictedHtmlEditor` |
| `sc.input.number` | integer, float, monetary | integer/float: `ScNumberInput`; monetary: business rendering |
| `sc.select.remote` | selection | `ScSelect`; `widget=radio`: `ScRadioGroup` |
| `sc.input.boolean` | boolean | `ScCheckbox` |
| `sc.input.date` | date | `ScDateField`; `widget=daterange`: two `ScDateField`s |
| `sc.input.datetime` | datetime | `ScDateField(withTime)` |
| `sc.relation.many2one` | many2one | `ProfessionalRelationFieldControl` |
| `sc.relation.many2many` | many2many | `ProfessionalRelationFieldControl` |
| `sc.select.tags` | many2many | `ProfessionalRelationFieldControl` |
| `sc.relation.table` | one2many | `ProfessionalDetailCollectionControl -> X2ManyRelationRenderer -> ScTable` |
| `sc.payment.settlement_detail_collection` | one2many | industry dynamic renderer |
| `sc.value.money` | monetary | `ProfessionalBusinessValueControl` |
| `sc.value.percentage` | float, integer | `ProfessionalBusinessValueControl` |
| `sc.display.status` | selection, char | `ProfessionalBusinessValueControl` |
| `sc.value.duration` | float, integer | `ProfessionalBusinessValueControl` |
| `sc.auth.*` | char/selection/text/action | base family; `one_time_secret` fails closed |
| `sc.display.text` | `*` | type-directed sentinel |
| `sc.table.data` | one2many, many2many | declared, Form field host not closed |
| `sc.tree.data` | one2many, many2many | declared, Form field host not closed |
| `sc.button.action` | action | declared, Form field host not closed |

### 3.4 Three Critical Facts

1. A componentKey is not a one-to-one raw Vue component identity.
2. `ProfessionalBaseFieldControl` is already the unified base-field host, but it
   still branches over Sc components by field type.
3. `sc.table.data`, `sc.tree.data` and `sc.button.action` currently declare more
   than the Form field host consumes. V1 must record these host gaps instead of
   inventing implementations.

The binding identity is therefore:

```text
componentKey
  + declared fieldType
  + declared widget/variant
  + render profile
  -> binding
```

Every selection input must come from Contract V2. Model names, field names, menu
labels and action IDs cannot fill a missing component declaration.

## 4. V1 Implementation Slice

### V1-01 Base Field Component Binding Map

The first slice covers unambiguous ordinary base fields:

- `sc.input.text -> ScInput`
- `sc.input.textarea -> ScTextarea`, with an explicit `html` variant
- `sc.input.number -> ScNumberInput`
- `sc.select.remote -> ScSelect`
- `sc.input.boolean -> ScCheckbox`
- `sc.input.date -> ScDateField`
- `sc.input.datetime -> ScDateField(withTime)`

The binding must validate:

- componentKey belongs to the generated carrier;
- field type is in the binding's closed set;
- widget/profile variants are declared by contract;
- missing, unknown or mismatched bindings fail visibly closed;
- no second complete componentKey vocabulary exists.

### V1-02 TDesign Base Component Closure

Reuse existing Sc components first. Adopt only real capability repairs from the
candidate:

- Input / Textarea: name, actual event context, IME, focus/blur.
- Select: name, actual change/search/popup events, focus/blur, keyboard.
- DateField: name, focus/blur, keyboard, loading/ARIA.
- Table: real consumer capabilities such as emptyText.
- Number / Checkbox: preserve controlled-value and event semantics; add only
  consumer-backed gaps.

### V1-03 Page Integration

Keep:

- `FormSection`
- `PageRenderer`
- `ActionSurfaceRendererHost`
- `ProfessionalComponentRegistry`
- `@sc/ui` Scene Composition

The new binding replaces only base-field implementation selection. It does not
rewrite page, list, kanban, detail or relation composition. Legacy
`SceneFieldControl` remains a compatibility path, not a V1 binding source.

### V1-04 Business Presentation and Actions

Continue using:

- `businessValuePresentation.ts`
- Contract V2 permission/readonly projection
- Action Registry / action contract
- server ACL

Sc/TDesign does not format business money/status/empty values and does not decide
action authorization.

### V1-05 Real Product Acceptance

Three surfaces:

1. Contract Form: base fields, date, selection, boolean and error state.
2. Payment Request: master-detail, money, actions, readonly/disabled.
3. Scene Collection: collection table, row navigation and readonly facts.

Reusable test entries:

- `verify.frontend.professional_component_registry.unit`
- `verify.frontend.professional_base_field.unit`
- `verify.semantic_runtime_resolution`
- `verify.frontend.professional_business_value.unit`
- `verify.frontend.professional_relation_field.unit`
- `verify.frontend.professional_detail_collection.unit`
- `verify.frontend.canonical_form_presenter.unit`
- `verify.frontend.business_semantics.unit`
- `verify.frontend.action_surface_renderer_registry.unit`
- `verify.local.dev.payment_request.full_chain`
- `verify.local.dev.payment_request.settlement_component.journey`

## 5. PR #845 Asset Disposition

| Existing result | V1 decision |
| --- | --- |
| Primitive Port | Keep, do not expand |
| ScSceneButton | Not a default Form base-field path |
| ScSceneInput/Textarea | Reuse real-event repairs; do not default to wrapper |
| ScSceneSelect/DateField | Reuse event, focus and name repairs |
| ScSceneTable/Icon | Reuse only consumer-backed repairs |
| ScenePrimitiveProvider | Not introduced as a global V1 provider |
| Seven-adapter Registry | Not promoted to the global Component Binding Map |
| Legacy Scene Kit | Keep compatibility until real consumers migrate |

## 6. Acceptance Criteria

- Platform component bindings cannot drift from the generated carrier.
- The binding does not add a second global componentKey vocabulary.
- Ordinary base fields choose implementation by componentKey plus declared
  variant.
- Unknown keys, field-type mismatch and undeclared variants fail closed.
- Existing relation, business-value and industry renderers do not degrade into a
  generic input.
- Business presentation, permissions and action chains do not change.
- The same Contract field uses consistent Sc/TDesign base components in
  Form/Detail.
- A new ordinary model and Contract can use the unified component set through
  declaration only.

## 7. Current Evidence

Latest-main baseline tests:

- `verify.frontend.professional_component_registry.unit`: PASS; registry cases
  `>=184`, guard 162 tests.
- `verify.frontend.professional_base_field.unit`: PASS; model matrix 54,
  counterexamples 6, guard 16 tests.
- `verify.semantic_runtime_resolution`: PASS; 119 cases.

These are pre-V1 baseline observations, not V1 acceptance. V1 acceptance remains
pending component binding, host integration, real journeys and final build.

V1 implementation evidence:

- `contract_component_bindings_test`: PASS; 11 base componentKeys, 23 key/type
  variants and 7 implementations.
- `contract_tdesign_components_test`: PASS; 67 checks and 0 console errors,
  covering real TDesign DOM, controlled value, input/change, focus/blur,
  keyboard, Select search/popup, ARIA, and `ProfessionalBaseFieldControl`
  consumption of the binding map.
- `verify.frontend.professional_base_field.unit`: PASS; model matrix 54, 19
  guard tests, with map/carrier drift and host-consumption checks.
- Professional Registry 162 tests, Primitive Adapter 41 tests, and focused
  business-value/relation/detail/Canonical/Action Surface tests all PASS.
- `ci.local.iteration`: PASSED with all 8 required incremental targets.
- `verify.frontend.lint.src`: 0 errors; one pre-existing out-of-scope
  `StatusPanel.vue` warning remains.
- `verify.frontend.typecheck.strict`: PASS.

This proves the V1 base binding and TDesign interaction slice. It does not yet
prove the three real product journeys or the final build; V1-05 remains pending.
