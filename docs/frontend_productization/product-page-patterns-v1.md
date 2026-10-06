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

### Current page-type adoption (TPL-07, locally verified)

This section supersedes the historical model-pilot scope below. The existing
page owners now declare their responsibility; no business model whitelist
selects the standard list, form or readonly detail composition.

| Existing responsibility | Shared implementation | Preserved capabilities / explicit exceptions |
|---|---|---|
| `ListPage` standard query list | `ProductListSurface` in populated and empty states | Existing server search/sort/pagination, grouping, selection and actions; the legacy pass-through container is removed. Kanban, dashboards, hierarchy and worksheets remain dedicated page owners. |
| `ContractFormPage` record form, including master/detail handling | Existing section `ScForm` / `ScFormItem`, one validation registry and save chain | Existing field controls, relation adapters, master/detail business extensions and data authority; designer sections and standalone sections without a runtime remain explicit exceptions. |
| Readonly `ContractFormPage` facts | Existing `ScDescriptions` for supported scalar facts | Collection, attachment, dedicated controls, unknown fact types and configuration-editing sections remain contract-field extensions with `data-detail-section-reason`; the page composition marker does not claim every section is a descriptions table. |
| Login credential submission (`WEB-BOOT-01`) | Existing `ScForm` / `ScFormItem` / `ScInput` / submit feedback, following Starter `pages/login/components/Login.vue` | Only the official engine's successful result may call the existing login/init/return chain. Native required semantics stay; `novalidate` avoids competing browser validation. Database pinning and public page actions stay authoritative. |
| Public activation stages (`WEB-AUTH-02`) | Existing `ScForm` / `ScFormItem` engine, with independent code/password stage identities | Original challenge lifecycle, required/12-character input constraints, backend confirmation/policy execution and credential clearing remain. Native form submit containers have exited. Recovery is a read-only channel notice, not an unimplemented password form. |
| Home and My Work workspace (`WEB-BOOT-01`) | `ProductWorkspaceSurface`: summary, query, main/actions and auxiliary card regions, following Starter `dashboard/base` organization | Existing `product_workspace` facts/actions, authorized navigation and recent activity remain with their adapters. My Work remains a handling workspace, not a service-paged ordinary list. Private outer panel/header layout has exited these consumers. |


The selection functions accept page responsibility and (for detail) the effective
render profile. They neither infer permissions nor add business capabilities.
Field validation coverage still determines which rules the legacy precheck may
exclude; unmounted required fields and domain validations are not bypassed.
The old model arrays are removed rather than expanded. Reverting the scoped
P0 commit restores rollout behavior; the reusable controls remain single-source.

WEB-LC-01 follow-up: the previous probe supplied a one-column **full list
configuration**, not a label patch. The V2 direct-column policy intentionally
replaced the configurable column universe and removed optional hidden columns
during that probe. Rollback restored them. That evidence must not be cited as
proof of label-only capability preservation. It does not invalidate unchanged-
configuration page-type adoption; future label-only configuration verification
must preserve and compare the complete column contract.

WEB-LC-02 closes that follow-up for the payment action: the formal native
baseline is retained under explicit full-list configuration, and personal list
preferences remain subject to its existing locks. The real draft → publish →
rollback loop preserved all 22 columns, 13 hidden columns, schema mappings,
actions, query scope and record identities. Only the tested label and the exact
configuration-authority marker may differ during draft/publication; restoration
must return to native authority. This is API/contract/list acceptance, not full
configuration-workbench UI acceptance. Evidence is in the existing iteration
record under WEB-LC-02.

WEB-STYLE-01 keeps those page-type defaults while separating their shared owners:
form save/epoch handling delegates designer selection, visibility and ordering to
`useRecordFormDesignerActions`; return wiring lives in the existing record
navigation runtime. Neither extraction creates a second state or execution path.
The style and explicit-type guards now pass without increasing size allowances.
This is local source/test verification. Runtime build identities and subsequent
bootstrap observations are recorded in the existing iteration record.

### Historical rollout records

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
| Application shell | `src/layouts/` | `app/presentation/standardShellComposition.ts` (adoption policy) + `App.vue` (shell gate) + `layouts/AppShell.css` (token layer) — TPL-04 |
| Master-detail handling page | form/list/upload/overlay composition | Adopted through the shared record-form composition (TPL-05A) and the page-responsibility selection (TPL-07); the list, form, upload and overlay owners are the existing ones, with the master/detail business extension preserved. |

### Adoption switch

- `app/presentation/standardFormComposition.ts` is the pure adoption policy.
  It resolves a page *responsibility* to `{ composition, adopted, reason }` and does
  not import Vue, the DOM, or TDesign. It reads no model name and holds no scope
  list: TPL-07 removed `STANDARD_FORM_COMPOSITION_PILOT_MODELS` (and the list/detail
  equivalents), so `app/presentation/standardPageType.ts` is the only input.
- `pages/contractForm/standardFormCompositionRuntime.ts` provides the resolved
  policy down the existing render chain and collects the adopted sections'
  validation results (`createStandardFormValidationRegistry`).
- `pages/ContractFormPage.vue` creates the runtime from the page model and
  `components/template/FormSection.vue` consumes it. A section that is not in
  the adopted scope renders its previous DOM unchanged (`bare` mode), so a
  single page never runs two competing compositions.

### Adopted scope (historical — superseded by the TPL-07 page-type adoption above)

The model-pilot list described here (`STANDARD_FORM_COMPOSITION_PILOT_MODELS`) no
longer exists in the shipped code; it was deleted when page responsibility became the
only selection input. The table is kept as rollout history only.


| Model | Verified entry | Round |
|---|---|---|
| `project.project` | `menu_sc_product_project_edit_v1` (menu 680) — retired, see note below | TPL-01 |
| `sc.general.contract` | `menu_sc_p1_daily_contract` (action `action_sc_general_contract`, menu 662) | TPL-02 |

> Retirement note: the `project.project` round above was verified against the
> 项目信息编辑 entry that has since been retired. Its complete composition is now
> carried by the single 项目台账 record entry
> (`smart_construction_core.action_sc_project_list` / view
> `smart_construction_core.view_project_overview_form`); the row is kept as
> rollout history and is not a live entry reference.

TPL-02 also adopted the sibling menu `一般合同（公司）` (`menu_sc_general_contract`, menu 353)
because adoption is decided per model, not per menu. That menu is not a row of the entry
matrix; its form was verified structurally, not through the business journey.

### Application shell (TPL-04)

The shell is a single surface, so its adoption scope is scoped by *route layout* rather than
by model. `STANDARD_SHELL_COMPOSITION_LAYOUTS` lists the layouts verified against the official
composition; `App.vue` resolves one pure decision
(`{ composition, adopted, reason }`) and uses it both as the shell gate and as the published
`data-shell-composition` / `data-shell-composition-reason` identity, so a gate and its evidence
cannot drift apart. A route that is not adopted — or an embedded relation dialog, which
intentionally bypasses the shell — renders its page component exactly as it did before.

The shell container driver was already the official `t-layout` primitive
(`ProductAppShell` → `ScLayout`); TPL-04 aligns the shell's *style layer* and makes the adoption
scope explicit. It removes no capability: the workspace panel modes (`navigation`, `catalog`,
`company`, `record`), the sidebar, the activity tabs and the minimal/compact topbar are all
unchanged.

Style-layer migration (presentation only, value-preserving):

- `layouts/AppShell.css` no longer declares or consumes its own
  `--surface/--ink/--muted/--accent/--panel/--layout-divider` alias block. Those positions now
  consume the canonical semantic tokens (`--sc-semantic-text-primary`,
  `--sc-semantic-text-secondary`, `--sc-semantic-surface-panel`,
  `--sc-semantic-border-default`), which is what `frontend/packages/design-tokens/token-authority.json`
  already classified the block as belonging to (owner `frontend.app_shell`).
- The two `44px` touch-target blocks in the minimal topbar consume the shared
  `--sc-touch-target-min` contract instead of repeating the literal.
- The reserved shell dimension aliases (`--sc-shell-sidebar-collapsed-width`,
  `--sc-shell-navigation-item-height`, `--sc-shell-page-gutter`) stay declared in the alias layer
  but have **no runtime consumer**, because the shell has no collapsible rail, its navigation rows
  are not 44 px, and its routed page gutter is already owned by the responsive
  `--sc-page-padding` contract. No consumer was fabricated to "use" them.

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
(`make verify.frontend.adopted_form_engine_decision.unit`, 74 cases, real
`TDesignForm`/`TDesignFormItem`, counted writes — it does not stub the engine or
expose an instance in the production build).

### Cross-model reuse (TPL-02)

**Historical (TPL-02).** The second model joined by being listed in the then-current
model pilot list. That list no longer exists: TPL-07 made the page responsibility the
only selection input, and the render call sites stay model-agnostic, so a second
model is still a reuse of the same composition, not a second implementation. Verified on the real application
route (project edit → contract, through the dirty-form guard → back to project
edit): each model renders its own field set, section registration, errors and
action identity, with `official=24 legacy=0` and `official=13 legacy=0`
respectively, no state carried across, and `official=13 legacy=0` at both
`1440×900` and `390×844` with no horizontal overflow. The project html field was
re-verified through the actual edit surface (type → save → reload read-back →
restore), allowing normal HTML normalization.

### Save-operation identity across the awaits (TPL-02R)

An adopted save awaits the engine, relation creates and the write, so the record
the page is bound to can move during any of them — including back to a record it
showed before. "Same model, same record id" is therefore not an identity: the id
comes back but the draft session does not. `pages/contractForm/useRecordFormActions.ts`
opens a save operation before its first await (bound surface key + a surface
epoch that advances on every change to the bound model/record) and re-checks that
it still owns the surface at every real side effect: the engine's error write, the
precheck error write, focus, the write request, its target record, the feedback,
and the busy flag. The single-flight join is scoped to the same key, so a save for
another record is never joined and a superseded `finally` cannot clear a newer
save's loading state. The values handed to the write are also proved to be the
values the engine saw (a submission snapshot compared before the write), so an
edit that lands mid-validation keeps the draft and stops the save instead of
riding on the older answer.

Scope note (do not overstate): this binds a save whose surface is lost **before**
the write request is sent — such an operation writes nothing. If the request was
already sent, the response is discarded as-is; that is not a rollback and is not
retried.

## Official list and readonly detail adoption (TPL-03)

TPL-03 extends the same adoption mechanism to the standard query list and the
standard readonly detail. Both reuse the previous round's carriers instead of
adding a second page implementation.

### List composition

- `app/presentation/standardListComposition.ts` is the pure adoption policy. It
  resolves one model to `{ composition, adopted, reason }` and owns the explicit
  pilot list (`project.project`, `sc.general.contract`, `payment.request` — the
  last one added by TPL-06A so one business flow does not run two list
  implementations); it imports no Vue, DOM, or TDesign.
  The pilot list is a **rollout switch, not a capability source**: membership
  says "this list renders through the official container", never "this model
  supports deletion, a given sort, or a given state action". Those stay with the
  effective contract, and a page that is not a member keeps an explicitly
  registered, still-correct implementation rather than silently falling back.
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
| Standard query list | `project.project` | `menu_sc_product_project_edit_v1` (menu 680) — retired, see TPL-01 note | TPL-03 |
| Standard query list | `sc.general.contract` | `menu_sc_p1_daily_contract` (menu 662) | TPL-03 |
| Standard query list | `payment.request` | `menu_sc_user_payment_apply` (menu 545) | TPL-06A |
| Standard readonly detail | `sc.general.contract` | record `/r/sc.general.contract/11` | TPL-03 |

### Boundary (TPL-03)

Contract and Odoo facts still decide which columns, fields, values, records,
actions and permissions exist. The adopted composition only decides how an
already-authorized list or readonly record is arranged. Adoption is never
derived from field names, labels, semantic roles, action IDs, menu IDs, roles,
or renderer selection, and it is never an authorization input; the list and
detail surfaces carry no model name.

### Ordering is a contract capability, not a header decoration (TPL-06A)

While adopting the payment-request list, the header offered an `amount` sort that
the request sanitiser silently dropped: the column declares `sort_field: "amount"`
in the contract, but the request allowlist was built only from field codes and
primary/search candidates, so the clause was discarded and the previous order was
sent. The click looked applied while the server kept its old order — a silent
no-op rather than a refusal.

`useActionViewLoadPreflightRuntime.collectContractOrderFields` now also collects
each widget's declared `sort_field`, so the header's affordance and the request
allowlist read the **same** contract declaration. Fail-closed behaviour is
unchanged in the other direction: a field the contract does not declare, a
non-identifier, or an unknown direction is still dropped
(`make verify.frontend.list_order_field_contract.unit`; the counterexample fails
without the fix).

### Deliberately not adopted

WEB-LC-01 verified the existing company/action-scoped list configuration on the
TPL-06A payment list: a temporary column label reached the effective contract and
the official surface, then platform rollback restored the contract labels and
visible headers. The same 20 ordered record IDs, fixed business fields (including
write_date), server query and company context were preserved. This is an API-to-
consumer configuration loop, not configuration-workbench UI acceptance or proof
of role-specific list configuration. Other projection structure changed during
publication; broader capability parity remains a requirement for type rollout.
See the WEB-LC-01 section of
`docs/ops/iterations/frontend_shared_foundation_gap_audit_20260909.md` for original
success/failure evidence and the three before/published/restored screenshots.

**Superseded (recorded for history).** This paragraph used to state that the
master-detail handling page's form side still kept `legacy-form-section` because
`payment.request` was absent from the model pilot list. Both the pilot list and that
scope gap are gone: the payment form and every other record form now resolve their
composition from the contract's declared page responsibility, and the current
candidate's browser check asserts the payment master/detail page mounts the official
form engine (`payment-master-detail: official form engine mounted` contract). The official detail page's `t-steps` timeline
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

The same two journeys are re-bound to one traceable candidate in
`artifacts/frontend-web-fix-20260928/tpl03r/`: source `f017d42d` (the TPL-02R
fix commit; the docs-only `9fd6a4b6` above it changes no product source), one
off-repo build served by `release_static_server.mjs` pid 2166107 on `:5176`
with all 100 files proven byte-identical over HTTP, re-run as **30/30** and
**7/7**. This replaces the earlier build's un-retraceable product-identity
claim (its bundle was overwritten); the historical `tpl03/` record is kept
unchanged and is not back-filled. Two boundaries apply: the switch journey's
legacy-detail step uses `/r/res.partner/1`, which shows a pre-existing
`加载失败` page in this environment (identical at `bffc4b7e`) and so only proves
the adopted composition did not leak — a rendering legacy detail is shown
separately at `/r/project.project/10` under `fixture_role_pm`
(`legacyGrids=4`, `facts=0`). Resize-without-reload across the narrow breakpoint
is now verified on the same candidate: `tpl03r/logs/resize-no-reload.log` shows
the adopted readonly detail at 2 facts per row at `1440`, 1 per row after a live
`setViewportSize(390)` (breakpoint 640), and back to 2 at `1440` — both
directions without a reload.

### Bootstrap-led coverage boundaries (WEB-BOOT-01)

`system.init.navigation.nav`, `navigation.route_authority` and effective page
contracts determine the observed scope; fixture roles are evidence scopes, not
runtime selection rules. Three roles expose 15, 3 and 86 leaf entries (87 distinct
menu identities), which is not the formal 89-entry business acceptance matrix.
The role surface's declared landing path may refine the general default route.
Home consumes its initialized page contract and `my.work.summary`; it does not
need a fabricated extra `ui.contract` call.

A list/table `pageInfo` does not override an explicit
`listProfile.collection_presentation.semantic=hierarchical_worksheet` with
`navigation_mode=sheet_groups`. Those entries use the registered worksheet
renderer exclusively; a contract kanban likewise remains dedicated. They are
not legacy standard-list fallbacks. Public account activation/recovery keep
specialized challenge/credential lifecycles; this batch does not claim those
write workflows were exercised or their entire presentation adopted.

The WEB-BOOT-01 targeted runtime observation resolves the dedicated collection
entries: menus 335/663 use `core.hierarchical_worksheet` (sheet groups), 454 uses
`core.standard_collection` with `workflow_board`, and 702/703 use `core.pivot`.
All report renderer status `ready`; none is counted as an ordinary-list fallback.
Menu 417 remains the dedicated P3 business-configuration workbench, whose
coverage scan is a read projection, distinct from configuration bootstrap/publish
writes. Public challenge flows and dedicated designers are explicit remaining
presentation scopes; this inventory does not claim full official adoption of
every specialized editor or formal 89-entry business acceptance.

WEB-AUTH-02 supersedes only the activation-form presentation exception above.
Both stages now use the official form engine; public account lifecycle and the
recovery-channel notice remain specialized responsibilities. Its browser proof
intercepts all API calls and simulates stage/error/success responses, so it is UI
acceptance and not evidence of activating a real account or changing a password.

### Anonymous public-page bootstrap (WEB-AUTH-03)

`GET /api/v1/auth/page-contracts` returns `{ok, data: {schema_version: "1.0.0", pages}}`.
The canonical builder projects only `login`, `account_activation`, and
`password_recovery`, without caller context/profile input. Each page carries its
existing schema version, texts, sections, and only public global/action targets;
no role, navigation, company, record or authenticated page projection is exposed.
The registered default action provider supplies `open_login` for activation and
recovery, matching the existing shared action-target authority.

The anonymous session loads this projection once per context, exposes loading
and retryable failure, and rejects missing public actions. Context epoch, request
sequence and authentication state prevent stale responses from replacing the
subsequent authenticated `system.init` result. The existing page action executor
consumes the targets; neither views nor the loader invent fallback destinations.
Activation challenge state remains mounted while public configuration retries.

WEB-AUTH-03 closes the anonymous return-navigation gap: the registered preview
passes 18 scoped checks with real public contract/recovery reads and simulated
activation writes, including retry and both return-to-login actions. Canonical
public zones and referenced data-source identities are projected without role
or authorization metadata. Error feedback and the submit action occupy separate
official form items. The authenticated finance startup regression remains valid;
no real account activation or password reset is claimed.

### Shared configuration field editor (WEB-CONFIG-01)

`LowCodeFieldChipEditor` uses `ScForm`/`ScFormItem` and controlled `ScInput`
values for its advanced field-name input; the official form validates before
emitting the existing `addName` event. Native form submission and private input
border/padding styling no longer control this scope. Field catalog search also
uses the controlled input contract. The shared component serves list columns,
search filters/grouping, pivot measures/dimensions and graph measures/dimensions.
P3 field validity, deduplication, ordering, drafts and publication remain owned by
the existing configuration handlers. Chips and field catalogs remain specialized
editor responsibilities, not ordinary collection-page fallbacks.

The real configuration-administrator journey covers the list/search consumer,
input synchronization, Enter/button submission, reversible local ordering and
1440/390 layouts (12 checks). It does not prove seven independent browser journeys
or publication; 14 component checks cover the shared wiring. Only resume-only
change-set reads are permitted, with `created=false` verified; no configuration
save/publish occurred. Login/session and usage telemetry remain permitted.
Menu configuration's native tree/editor controls and dedicated form-designer
interactions remain explicit adoption work; this batch does not mark them complete.


### Menu configuration presentation (WEB-CONFIG-02)

The dedicated menu editor uses `ScPageHeader` for its identity and action area,
retaining contract actions, dirty count, disabled conditions and configuration
callbacks. Its seven text/search controls across creation, selection, bulk rows
and tree filtering use controlled `ScInput` values. Page-owned header styling and
native search-input border/height/padding no longer render that adopted scope.
Text updates consume emitted values; native event adapters remain for unchanged
number/select/checkbox controls. All text fields share the existing draft store.

Tree drag/drop, role selection, numeric ordering, version selection and the
specialized bulk table remain explicit dedicated responsibilities; this change
is not a conversion to ordinary server-paginated collections. Their remaining
native controls and page-level feedback are not counted as fully adopted.


WEB-CONFIG-03 restores the menu panel's runtime navigation by consuming the
existing `IdentityResolver` identity profile, preserving multiple roles, exposure
and deny rules before `DeliveryEngine` filtering. A configuration-administrator
flag does not grant platform discovery. The installed industry's identity profile
and startup override provider currently use the same role policy source. This is
not a guarantee of equivalence for future root/scene/priority override providers;
those must preserve the same effective identity contract when introduced.


The registered CONFIG02/03 preview passes 12 real administrator UI checks after
the navigation repair, including synchronized selected/bulk text drafts, clear
and restore, tree search, empty-create disabling and 1440/390 layouts. No menu
save, create, publish or rollback request is executed; this closes presentation
and read-projection scope only, not persistent configuration-write acceptance.


### Menu configuration choice controls (WEB-CONFIG-04)

Creation, selected-menu and bulk-row fields now use shared `ScSelect`,
`ScNumberInput`, `ScCheckbox` and `ScRadio`; the native input/select path and its
private border/padding styling exit this page. Option identities, the zero-value
sentinels, parent exclusion rules, role catalogs, draft normalization and publish
callbacks remain unchanged. Select values are converted to numeric menu IDs;
numeric clearing retains zero while existing zero overrides display empty.
Checkboxes consume booleans and own their labels. Version radios select only on
checked=true and retain the common group name. Number controls use the official
normal theme so narrow ordering columns retain readable values.

The dedicated tree, bulk editing table and page-level feedback remain specialized
composition work. Control adoption does not establish save/publish/rollback
acceptance, nor replace the server's configuration/permission constraints.


CONFIG04 passes 24 scoped real-page checks, including number clearing/restoration,
selected/bulk checkbox synchronization, role toggles, default-parent selection and
both viewport popup bounds. Version reads succeed without bootstrap; the existing
acceptance data has no historical versions, so live version-radio interaction is
explicitly unverified. No persistent configuration write or fixture creation occurs.


### Menu configuration feedback (WEB-CONFIG-05)

`ScInlineState` owns menu error, success notice, loading and version-explanation
presentation, using official Alert/Loading drivers. Its additive `success` state
uses the official success theme. Error retains priority over the existing saved
notice; loading remains independent. A fully successful panel load clears a stale
read error without discarding the saved notice. Failures continue to show the
original handler error and the existing refresh action remains the recovery path.
Private status/error/success, loading and version-empty styles exit this scope.

The rendering inventory now verifies adopted workspace delegation and actual
workflow/body action bindings instead of requiring retired tags/button counts.
Public bootstrap states and the official list card are registered in the existing
ownership source with explicit bindings and negative tests. This static coverage
is separate from browser acceptance and from the formal 89-entry business scope.


CONFIG05 passes 33 scoped menu checks, including a simulated read failure with a
simulated saved notice followed by a real panel refresh. Loading/busy, alert/status
semantics, error priority, recovery and both viewport feedback bounds pass. This
is feedback/recovery evidence, not a real save. The no-history version-radio
coverage limit remains explicit; no fixture or configuration write is introduced.
