# Product Page Patterns v1

## Authority

Product Page Patterns are P0 structural presentation authorities. They organize
existing renderers and controls; they do not infer Contract semantics, select
business components, or grant capabilities.

The four formal patterns are:

- `task-form`: task-focused create, edit, handling, and explicit readonly presentation.
- `workspace-form`: Native structured form for professional management and decision work.
- `collection`: search, filter, group, list/kanban, selection, batch action, and pagination organization.
- `dashboard`: metric, risk, todo, readable fallback, and drilldown organization.

## Axes and invariants

Form pattern and render profile are orthogonal:

```text
task-form      × create | edit | readonly
workspace-form × create | edit | readonly
collection     × readonly
dashboard      × readonly
```

`presentationMode` remains the backend-declared form authority. The frontend
must not derive task/workspace from fields, semantic roles, model names, action
IDs, menu IDs, or renderer selection. A pattern/mode mismatch fails closed.

## Production wiring

- `ContractFormDriverHost` selects `TaskFormPattern` only from the existing
  explicit task floorplan decision and `WorkspaceFormPattern` for the existing
  Native branch. The pattern does not replace either renderer.
- `ActionView` selects `CollectionPattern` or `DashboardPattern` from its formal
  decoded view mode. Existing list, kanban, toolbar, filter, pagination, and
  dashboard surfaces remain unchanged inside the pattern.
- Every pattern emits `data-product-page-pattern`, `data-presentation-mode`, and
  `data-render-profile` for deterministic runtime evidence.

## Exclusions

- No Contract V2 or permission changes.
- No model/action/menu special cases.
- No professional component registry or readiness claims.
- No industry component implementation.
- No route, mutation, or settlement changes.

## Official template adoption (FE-TPL)

The presentation composition for standard pages is taken from the official
`Tencent/tdesign-vue-next-starter` sources instead of being re-assembled per
page. The reference snapshot is
`aeed57076217f7777158b905f353d73585bad1c4`; it is a reference baseline, not a
dependency upgrade. Local library identity stays `tdesign-vue-next@1.20.5`
(lockfile version, re-read by `verify.frontend.component_driver_takeover.unit`).

| Page type | Official source | Takeover position in this repository |
|---|---|---|
| Standard edit form | `src/pages/form/base/index.vue` | `components/template/FormSection.vue` (field grid, label, error slot) plus `design-system/ScForm.vue` / `ScFormItem.vue` (validation and instance capability pass-through) |
| Standard query list | `src/pages/list/base/index.vue` | not adopted yet (planned TPL-03) |
| Standard readonly detail | `src/pages/detail/base/index.vue` | not adopted yet (planned TPL-03) |
| Application shell | `src/layouts/` | not adopted yet (planned TPL-04) |
| Master-detail handling page | form/list/upload/overlay composition | not adopted yet (planned TPL-05) |

### Adoption switch

- `app/presentation/standardFormComposition.ts` is the pure adoption policy.
  It resolves one model to `{ composition, adopted, reason }` and owns the
  explicit pilot scope list; it does not import Vue, the DOM, or TDesign.
- `pages/contractForm/standardFormCompositionRuntime.ts` provides the resolved
  policy down the existing render chain and collects the adopted sections'
  validation results (`createStandardFormValidationRegistry`).
- `pages/ContractFormPage.vue` creates the runtime from the page model and
  `components/template/FormSection.vue` consumes it. A section that is not in
  the adopted scope renders its previous DOM unchanged (`bare` mode), so a
  single page never runs two competing compositions.

### Adopted scope

`STANDARD_FORM_COMPOSITION_PILOT_MODELS` lists the surfaces verified against the
composition. A model joins by being listed there and by carrying a contract the
composition already understands; the rendering surfaces never name a model, so a
second model is a reuse of the same composition rather than a second
implementation of it.

| Model | Verified entry | Round |
|---|---|---|
| `project.project` | `menu_sc_product_project_edit_v1` (menu 680) | TPL-01 |
| `sc.general.contract` | `menu_sc_p1_daily_contract` (action `action_sc_general_contract`, menu 662) | TPL-02 |

TPL-02 also adopted the sibling menu `一般合同（公司）` (`menu_sc_general_contract`, menu 353)
because adoption is decided per model, not per menu. That menu is not a row of the entry
matrix; its form was verified structurally, not through the business journey.

### Style boundary

The adopted row is selected by the primitive identity this project already puts on the adapter
(`.field-control-row[data-semantic-component='ScFormItem']`), never by a vendor class. A TDesign
class may appear on an Sc root; its internal descendants stay uncoupled, so a version swap cannot
silently change what the section styles. `verify.frontend.rendering_detail_state.unit` enforces
this (`internalVendorSelectorGapCount` must stay 0).

### Boundary

Contract and Odoo facts decide what exists, what is editable, and what may be
shown. The adopted composition decides how the form is laid out and when
generic field validation runs and how errors surface. The existing business
runtime keeps the single draft, the occurrence write decision, permission,
domain validation, and the save chain. Validation rules are built from the
contract's field facts (`components/template/contractFormValidationRules.ts`),
not from model names or labels.
