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
| Standard query list | `src/pages/list/base/index.vue` | `components/product-list/ProductListSurface.vue` (one `t-card.list-card-container` wrapping the query row and the table) plus `product-list/ProductListHeader.vue` (search field) — TPL-03 |
| Standard readonly detail | `src/pages/detail/base/index.vue` | `components/template/FormSection.vue` readonly-facts branch (`t-descriptions` label/value per section, same readonly value identities) — TPL-03 |
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

### Validation ownership on an adopted surface

One generic authority per rule. On an adopted surface the official engine
(`ScForm`/`ScFormItem` → TDesign `Form.validate()`) decides the generic rules for
the positions it really renders and declares rules for; those positions are
reported as `coveredFieldNames` and excluded from the page-level required
precheck, so a save is never decided twice. Everything the engine does not cover
keeps its previous precheck, domain validation and the server constraints.

The engine's result (not the call order) decides the save:

| Engine outcome | Effect |
|---|---|
| non-success result | rejected codes join the one existing error store; no write |
| success | domain validation and the existing save chain continue, one write |
| unreadable / absent result | fail closed — no write, draft kept |
| adopted, required positions declared, none covered | fail closed — the runtime or section registration is missing |
| adopted, contract genuinely has no required position | legal empty set, save allowed |

An adopted section that declares rules but has no engine instance, or whose
result cannot be read, raises instead of returning "passed". A surface outside
the pilot scope adopts nothing and needs no runtime. The real-engine integration
proof is `frontend/apps/web/scripts/adopted_form_engine_decision_test.ts`
(`make verify.frontend.adopted_form_engine_decision.unit`, 67 cases, real
`TDesignForm`/`TDesignFormItem`, counted writes — it does not stub the engine or
expose an instance in the production build).

### Cross-model reuse (TPL-02)

The second model joins by being listed in `STANDARD_FORM_COMPOSITION_PILOT_MODELS`;
the render call sites stay model-agnostic, so this is a reuse of the same
composition, not a second implementation. Verified on the real application
route (project edit → contract, through the dirty-form guard → back to project
edit): each model renders its own field set, section registration, errors and
action identity, with `official=24 legacy=0` and `official=13 legacy=0`
respectively, no state carried across, and `official=13 legacy=0` at both
`1440×900` and `390×844` with no horizontal overflow. The project html field was
re-verified through the actual edit surface (type → save → reload read-back →
restore), allowing normal HTML normalization.

## Official list and readonly detail adoption (TPL-03)

TPL-03 extends the same adoption mechanism to the standard query list and the
standard readonly detail. Both reuse the previous round's carriers instead of
adding a second page implementation.

### List composition

- `app/presentation/standardListComposition.ts` is the pure adoption policy. It
  resolves one model to `{ composition, adopted, reason }` and owns the explicit
  pilot list (`project.project`, `sc.general.contract`); it imports no Vue, DOM,
  or TDesign.
- `components/product-list/ProductListSurface.vue` is the official container:
  one `ScCard appearance="table" :bordered="false"` (the official
  `t-card.list-card-container` shape) wrapping the query row and the table, with
  the zero body padding carried by the card's `table` appearance rather than by
  a selector onto the vendor's internals. Outside the adopted scope the slot is
  passed through unchanged, so a list never renders through two containers.
- `pages/ListPage.vue` resolves the decision from the page model, wraps the
  populated branch in the surface, and publishes `data-list-composition` /
  `data-list-composition-reason` on the page root. The list surface itself never
  names a model, so a second model is a reuse, not a second implementation.

### Readonly detail composition

- `app/presentation/standardDetailComposition.ts` is the pure adoption policy;
  only the `readonly` render profile adopts, and the pilot list is
  `sc.general.contract`. An editable surface keeps its previous composition
  (`reason=not-a-readonly-profile`) because the official detail page has no
  editing state.
- `pages/contractForm/standardDetailCompositionRuntime.ts` provides the resolved
  decision down the existing section tree (the readonly counterpart of
  `standardFormCompositionRuntime`); `pages/ContractFormPage.vue` creates it from
  the page model and render profile and publishes `data-detail-composition` /
  `data-detail-composition-reason`.
- `components/template/FormSection.vue` renders its readonly facts through
  `ScDescriptions` (`t-descriptions`, `:bordered="false"`) when the page is
  adopted, the section is presented as readonly facts, and the section has
  fields. Every item is built from the section's own contract field facts, and
  the value slot reuses the **same** readonly value identities as the previous
  fact grid (relation entry, html, task action, plain value). A narrow viewport
  collapses to one fact per row via `composables/useNarrowViewport.ts`.

### Adoption scope (TPL-03)

| Surface | Model | Verified entry | Round |
|---|---|---|---|
| Standard query list | `project.project` | `menu_sc_product_project_edit_v1` (menu 680) | TPL-03 |
| Standard query list | `sc.general.contract` | `menu_sc_p1_daily_contract` (menu 662) | TPL-03 |
| Standard readonly detail | `sc.general.contract` | record `/r/sc.general.contract/11` | TPL-03 |

### Boundary (TPL-03)

Contract and Odoo facts still decide which columns, fields, values, records,
actions and permissions exist. The adopted composition only decides how an
already-authorized list or readonly record is arranged. Adoption is never
derived from field names, labels, semantic roles, action IDs, menu IDs, roles,
or renderer selection, and it is never an authorization input; the list and
detail surfaces carry no model name.

### Deliberately not adopted

The official shell (`src/layouts/`, TPL-04) and the master-detail handling page
(TPL-05) are still out of scope. The official detail page's `t-steps` timeline
is **not** adopted: this project already owns a richer audit/collaboration
timeline, and replacing it would drop business capability rather than re-express
presentation. The legacy list and detail surfaces (for example `res.partner`)
and every editable form keep their previous composition.

### Evidence (TPL-03)

`frontend/apps/web/scripts/standard_collection_composition_test.ts`
(`make verify.frontend.standard_collection_composition.unit`, 64 cases) proves
the policies are pure, that the pilot lists are explicit, that the call sites
never name a model, and that the shipped surfaces really render the adopted
markers. The two real-route journeys are bound in
`artifacts/frontend-web-fix-20260928/tpl03/`: `tpl03-journey-results.json`
(30/30: adopted contract list and readonly detail at `1440×900` and `390×844`,
project list, and legacy/edit controls) and `tpl03-switch-results.json` (7/7:
adopted list → adopted detail → legacy detail → legacy list → back, with no
fact, card, error, or registration leaking across models).
