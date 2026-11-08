# ADR-FE-RENDERER-02C-02A: Thin Primitive Adapter Architecture Decision

- Status: owner direction accepted; pending independent architecture review. This ADR does not authorize product-code migration.
- Audit baseline: `c8be18bc26cb262a30764a53b9d0765f646427aa`
- Date: 2026-11-08
- Formal Product Layer: P0 platform kernel product
- Layer Target: Frontend renderer / Scene composition / Sc primitive authority boundary
- Module: Sc Design System, `@sc/ui` Scene composition, Primitive Port, and Web Sc Adapter
- Standard vs User-Specific: platform engineering standard
- Chinese version: [frontend_thin_primitive_adapter_adr_v1.md](frontend_thin_primitive_adapter_adr_v1.md)

## 1. Decision

Keep the Sc Design System and `@sc/ui` as separate systems, but redefine their authorities and dependency direction:

1. The Sc Design System is the only base-control authority.
2. `@sc/ui` owns Scene page regions, layout, and composition. It does not implement a second base-control system.
3. `@sc/ui` defines vendor-neutral Primitive Ports required by Scene composition.
4. The Web product runtime supplies Sc-backed adapters that map those Ports to `ScButton`, `ScInput`, `ScSelect`, `ScDateField`, `ScTextarea`, `ScTable`, and platform icons.
5. TDesign and Browser Native are internal Sc implementation choices. They are not a second component authority selected by Scene or users.
6. The TDesign Bridge belongs to the Web implementation boundary of the Sc Design System. Do not create an `@sc/tdesign` package in this program.
7. `frontend/packages/design-tokens` is the only design-token source. `@sc/ui` keeps only the `compact` and `cozy` Scene-density semantics and no second color, radius, or control-height facts.
8. Professional Scene composition such as `SceneObjectPage`, `SceneCollectionSurface`, and `SceneHierarchySurface` remains in `@sc/ui`; it is not moved into Sc or discarded.

This ADR records the decision, target protocol, migration graph, guards, and acceptance boundaries. It changes no product code, removes no driver, and changes no runtime behavior.

## 2. Why This Optimization Is Needed

The problem is not simply that two component packages exist. Three authorities currently overlap:

- `@sc/ui/primitives` is treated as the vendor-bridge authority.
- The Sc Design System owns base-control presentation and interaction.
- Scene has a separate Kit Runtime that chooses TDesign or Native.

This creates an inverted dependency:

```text
Sc Design System
      |
      v
@sc/ui/primitives
      |
      v
TDesign
```

The product runtime also consumes Scene composition from `@sc/ui`. The package therefore behaves both as a vendor export and as an upper-level Scene library.

Two base-control drivers duplicate prop mapping, event mapping, readonly/disabled behavior, error state, density, and native fallback. Scene also owns business presentation and design values that belong to platform authorities.

The result is a bounded architecture simplification: remove duplicate base-control implementations and runtime selection while preserving professional Scene composition.

## 3. Read-Only Audit Facts

### 3.1 Responsibilities and Consumers in `@sc/ui`

`frontend/packages/ui/src` currently contains 30 files, including 12 Vue components:

| Category | Components | Current role | Target role |
| --- | --- | --- | --- |
| Scene page composition | `SceneObjectPage`, `SceneCollectionSurface`, `SceneHierarchySurface` | Page regions and business-scene composition | Keep |
| Scene layout/content composition | `ScenePageFrame`, `SceneWorkspaceHeader`, `SceneActivityTabs`, `SceneNotice`, `SceneReviewPanel` | Layout, facts, notices, activity, review regions | Keep |
| Scene base controls | `SceneFieldControl`, `SceneButton`, `SceneRelationTable` | Drive either TDesign or Native | Thin adapters over Primitive Ports |
| Adapter container | `SceneUiProvider` | Load a Kit, select a Driver, inject tokens and density | Inject Primitive Adapter and density only |

The apps/web source contains 11 actual imports from `@sc/ui`:

| Consumer | Current use | Direction |
| --- | --- | --- |
| `pages/contractForm/ContractFormDriverHost.vue` | `SceneUiProvider`, `SceneButton` | Keep Provider; product actions use `ScButton` |
| `pages/contractForm/CanonicalActionBar.vue` | Direct `SceneButton` | Use `ScButton` |
| `components/template/FormSection.vue` | `SceneFieldControl`, optional Kit context | Pilot field path uses Primitive Port to Sc |
| `components/action/SceneReadonlyCollectionRenderer.vue` | `SceneUiProvider`, `SceneCollectionSurface` | Keep readonly composition; remove Kit selection |
| `pages/contractForm/useContractFormComponentDriverRuntime.ts` | Kit decision and preference I/O | Retire with migration |
| `app/action_runtime/useActionViewSceneComponentDriverRuntime.ts` | Collection Scene decision and preference I/O | Retire with migration |
| `app/renderers/sceneComponentDriverPolicy.ts` | Scene/Form Driver policy | Replace with one Primitive Adapter runtime |
| `app/renderers/sceneReadonlyCollectionBridge.ts` | Scene composition contract bridge | Keep |
| `components/template/contractFormDriverField.ts` | Scene field DTO mapping | Keep and target the Port DTO |
| `components/design-system/tdesignPrimitiveBridge.ts` | Obtains TDesign through `@sc/ui/primitives` | Move into Web Sc Design System |
| `components/design-system/scIcon.ts` | Obtains TDesign icons through `@sc/ui/icons` | Replace with the Web Icon Adapter |

`SceneObjectPage` and `SceneHierarchySurface` currently have no apps/web consumer. They remain valid Scene composition capabilities and are not deletion candidates.

The form Scene path covers only a subset of fields admitted by feature flags and field type. The readonly collection path admits only pages with no mutation actions and no selection.

### 3.2 TDesign Runtime Dependency

- `frontend/packages/ui/package.json` directly depends on `tdesign-vue-next@1.20.5` and `tdesign-icons-vue-next@0.4.9`.
- `frontend/packages/ui/src/primitives.ts` exports 61 `TDesign`-prefixed symbols, including type aliases, covering Input, Button, Select, Table, Dialog, DatePicker, Form, Descriptions, Tree, Upload, and others.
- `frontend/packages/ui/src/icons.ts` exports 49 TDesign icons.
- `frontend/packages/ui/src/kits/tdesign/register.ts` imports TDesign components and styles directly and implements the `tdesign-modern` Scene Driver.
- `SceneHierarchySurface`, `SceneReviewPanel`, `SceneObjectPage`, and `SceneWorkspaceHeader` import TDesign icon wrappers from `@sc/ui/icons`.
- The Sc Design System contains 63 `Sc*.vue` components; 52 consume `tdesignPrimitiveBridge`.
- `tdesignPrimitiveBridge.ts` obtains TDesign from `@sc/ui/primitives`, creating `Sc -> @sc/ui -> TDesign`.

`@sc/ui` is therefore not a pure Scene composition package.

### 3.3 Dual Drivers and Kit Selection

Two real mechanisms exist:

```text
A: ScInput / ScSelect / ScButton / ScTable
       -> tdesignPrimitiveBridge
       -> TDesign / Browser Native

B: SceneFieldControl / SceneButton / SceneRelationTable
       -> SceneUiProvider
       -> SceneUiDriverRuntime
       -> Native HTML / TDesign
```

- `SceneUiKitId` has two values: `sc-native` and `tdesign-modern`.
- Both kits advertise essentially the same capabilities.
- `sceneComponentDriverPolicy.ts` fixes `allowUserOverride` to `false`.
- Both runtime hooks still read or write the `scene_ui_driver` user preference.
- Only `ContractFormDriverHost.vue` and `SceneReadonlyCollectionRenderer.vue` mount `SceneUiProvider` in apps/web.
- The Provider dynamically selects a Driver and can fall back to another kit.

There is no effective user-selectable component-library capability, but the policy, preferences, telemetry, fallback, and duplicate implementations remain.

### 3.4 Duplicated Business Presentation

`@sc/ui` currently makes these business decisions:

- `SceneFieldControl.vue` hardcodes `CNY` in both TDesign and Native branches.
- `SceneRelationTable.vue` renders `row.values[column.key] || '无'`.
- `SceneCollectionSurface.vue` mobile cards also use `|| '无'`.
- `SceneObjectPage.vue` renders `field.value || '无'`.
- `SceneTone` and `data-tone` define a local status vocabulary.
- `sceneFieldControlValue.ts` normalizes field values again inside Scene.

These paths bypass `frontend/apps/web/src/app/presentation/businessValuePresentation.ts`. Currency, precision, empty text, status labels, and dates must come from the platform layer as already-interpreted facts. Scene only places and composes those results.

### 3.5 Token, Theme, and Density Duplication

`frontend/packages/design-tokens` owns primitive, semantic, component, and pattern tokens. `component.json` already contains button, input, and table heights, radii, spacing, and focus values.

Current duplicate facts remain:

- `frontend/packages/ui/src/kits/tokens.ts` defines three local palettes and radius sets.
- `apps/web/src/styles/tokens/profile.css` repeats the same profile IDs and semantic values.
- `frontend_theme_profile_guard.py` currently enforces equality between these two sources instead of validating one authority.
- `SceneUiProvider.vue` uses local token values as CSS fallbacks and declares `cozy=44px` and `compact=36px`.
- `SceneObjectPage.vue` also declares local `--sc-scene-*` values at `:root`.
- No apps/web caller passes `tokenProfile`, but the two mounted Providers still activate Provider-local default values.

The target keeps light/dark mode and theme profiles, but profiles override semantic tokens. Scene density becomes a mapping to component tokens, not a second set of dimensions inside `@sc/ui`.

### 3.6 Documentation and Guard Facts

`docs/frontend_productization/runtime-theme-profile-switching.md` states that apps/web never mounts `SceneUiProvider`. That statement is stale because two entries currently mount it. The remaining true fact is that no apps/web caller supplies `tokenProfile`.

The following guards also participate in the migration:

- `scripts/verify/frontend_primitive_adapter_guard.py` requires the Web bridge to obtain TDesign from `@sc/ui/primitives`, directly preserving the wrong dependency.
- `scripts/verify/frontend_scene_component_bridge_guard.py` requires `@sc/ui/form`, Provider, Kit selection, and legacy driver wiring.
- `frontend/apps/web/scripts/primitive_adapter_contract_test.ts` tests Sc primitive identity and some interaction, but not Scene Port/Sc equivalence.
- `frontend/apps/web/scripts/scene_component_driver_bridge_test.ts` tests legacy Kit/Runtime decisions, not equivalent behavior through FormSection and SceneFieldControl.
- `frontend_business_semantics_guard.py` scans apps/web only and cannot reject `CNY`, `无`, or local tone vocabularies in `@sc/ui`.

Guards must change with the owning migration stage. Implementations must not violate existing gates first, and incorrect dependencies must not be preserved merely to keep old guards green.

## 4. Target Architecture

### 4.1 Four Layers

| Layer | Responsibility | Authority |
| --- | --- | --- |
| L1 Vendor Layer | TDesign / Browser Native | No platform business semantics |
| L2 Platform Primitive Authority | Sc Design System | Only base controls and Sc-internal drivers |
| L3 Scene Composition | `@sc/ui` | Page regions, layout, and Scene composition |
| L4 Product Runtime | Vue Web application | Contract V2, presentation, renderer, permissions, actions, and adapter assembly |

### 4.2 Allowed Dependency Direction

```text
Product Runtime
      |
      +-------------------> Sc Design System
      |                           |
      |                           v
      |                     TDesign / Native
      |
      +-------------------> @sc/ui
                                  |
                                  v
                          Primitive Port
                                  ^
                                  |
                          Sc-backed Adapter
                                  |
                            Product Runtime
```

Rules:

1. Product Runtime may depend on Sc, `@sc/ui`, and the Adapter.
2. Sc may depend on the Web-internal TDesign Bridge.
3. Sc must not depend on `@sc/ui`, `@sc/ui/primitives`, `@sc/ui/icons`, or Scene components.
4. `@sc/ui` may depend on Vue, its own DTOs, and Primitive Ports.
5. `@sc/ui` must not depend on apps/web paths, TDesign, concrete Sc Vue implementations, or vendor icon types.
6. Product Runtime supplies the Adapter. The Adapter may map Ports to Sc, but Sc props are not the Scene protocol.
7. Scene DTOs such as `SceneField` and `SceneRelationTable` may remain. Business values must already be interpreted by the platform before reaching Scene.

### 4.3 TDesign Bridge and Icons

The first stages do not create a new workspace package:

```text
frontend/apps/web/src/components/design-system/
    ScInput.vue
    ScSelect.vue
    ScButton.vue
    ScTable.vue
    vendor/tdesignBridge.ts
    vendor/scIconAdapter.ts
```

`vendor/tdesignBridge.ts` becomes the only Web runtime TDesign export inside the Sc Design System. TDesign can be removed from `@sc/ui` only after its primitive, icon, and Scene Driver exports have migrated.

Temporary legacy exports are allowed only during migration. New Scene code must not add vendor dependencies.

## 5. Primitive Port v1

### 5.1 Contract Rules

Ports are stable interfaces between Scene and the platform. They are neither aliases for TDesign props nor a `Record<string, Component>`.

Mandatory rules:

- The caller owns controlled values; an Adapter keeps no shadow business state.
- Readonly and disabled controls emit no value changes.
- Loading does not fabricate a successful value; a loading button does not invoke business actions.
- Events carry the real native event whenever the platform exposes it. IME and keyboard callers must not lose event identity.
- Error state exposes a perceptible state plus `aria-invalid` / `aria-describedby`.
- Text and icon-only buttons must have an accessible name.
- Controls expose `focus()`; focusable controls emit `focus` and `blur`.
- Ports define no currency, precision, status copy, displayed date, or empty text.

### 5.2 Common Types

The following is the schema-level TypeScript protocol. 02C-02B implements it and enforces Adapter conformance through type and component tests.

```ts
export type ScenePrimitiveSize = 'small' | 'medium' | 'large';
export type SceneControlStatus = 'default' | 'error';
export type SceneDensity = 'compact' | 'cozy';

export interface PrimitiveHandle {
  focus(options?: FocusOptions): void;
}

export interface PrimitiveCommonProps {
  id?: string;
  name?: string;
  size?: ScenePrimitiveSize;
  status?: SceneControlStatus;
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  loading?: boolean;
  describedBy?: string;
  ariaLabel?: string;
}

export interface ControlEvents {
  change: [value: string, event: Event];
  focus: [value: string, event: FocusEvent];
  blur: [value: string, event: FocusEvent];
  keydown: [event: KeyboardEvent];
  keyup: [event: KeyboardEvent];
}
```

### 5.3 ButtonPort

```ts
export interface ButtonPortProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: ScenePrimitiveSize;
  disabled?: boolean;
  loading?: boolean;
  loadingLabel?: string;
  accessibleLabel?: string;
}

export interface ButtonPortEmits {
  activate: [event: MouseEvent | KeyboardEvent];
  focus: [event: FocusEvent];
  blur: [event: FocusEvent];
}

export interface ButtonPortSlots {
  default(): unknown;
}
```

Requirements:

- Enter and Space activate; disabled or loading does not activate.
- Icon-only or textless buttons require `accessibleLabel`.
- Loading exposes a busy state and readable loading text.
- Product action regions use `ScButton` directly. `SceneButton` remains only as a thin Scene composition wrapper.

### 5.4 InputPort

```ts
export interface InputPortProps extends PrimitiveCommonProps {
  value: string;
  type?: 'text' | 'search' | 'number' | 'email' | 'tel' | 'url' | 'password';
  inputMode?: 'text' | 'decimal' | 'numeric';
  placeholder?: string;
  autocomplete?: string;
  min?: string | number;
  max?: string | number;
  step?: string | number;
  maxLength?: number;
}

export interface InputPortEmits extends ControlEvents {
  'update:modelValue': [value: string];
  input: [value: string, event: Event];
  compositionstart: [event: CompositionEvent];
  compositionend: [event: CompositionEvent];
}

export interface InputPortSlots {
  prefix?(): unknown;
  suffix?(): unknown;
}
```

Requirements include real IME events, no value changes while readonly/disabled/loading, and no currency or precision in InputPort.

### 5.5 SelectPort

```ts
export interface SelectPortOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectPortProps extends PrimitiveCommonProps {
  value: string;
  options: readonly SelectPortOption[];
  placeholder?: string;
  filterable?: boolean;
  emptyText?: string;
}

export interface SelectPortEmits extends ControlEvents {
  'update:modelValue': [value: string];
  search: [query: string];
  popupVisibleChange: [event: { visible: boolean; trigger: string }];
}
```

Requirements include accessible naming, expanded state, error/description associations, and keyboard open/select/search/Escape/focus behavior. The current ScSelect focus/blur/change gaps must be implemented or explicitly wrapped before conformance.

### 5.6 DateFieldPort

```ts
export interface DateFieldPortProps extends PrimitiveCommonProps {
  value: string;
  format: 'YYYY-MM-DD' | 'YYYY-MM-DD HH:mm:ss';
  placeholder?: string;
  clearable?: boolean;
}

export interface DateFieldPortEmits extends ControlEvents {
  'update:modelValue': [value: string];
}
```

`format` defines the value protocol, not display copy. The current `ScDateField` lacks change/focus/blur events and must be corrected before it satisfies this Port.

### 5.7 TextareaPort

```ts
export interface TextareaPortProps extends PrimitiveCommonProps {
  value: string;
  placeholder?: string;
  rows?: number;
  maxRows?: number;
}

export interface TextareaPortEmits extends ControlEvents {
  'update:modelValue': [value: string];
  input: [value: string, event: Event];
}
```

ScTextarea may use TDesign or Native internally, but the Port exposes no vendor props.

### 5.8 TablePort

```ts
export interface TablePortColumn {
  key: string;
  label: string;
  width?: string;
  align?: 'left' | 'center' | 'right';
}

export interface TablePortRow {
  id: string | number;
}

export interface TablePortProps<Row extends TablePortRow> {
  rows: readonly Row[];
  columns: readonly TablePortColumn[];
  rowKey?: keyof Row & string;
  loading?: boolean;
  emptyText?: string;
  interactiveRows?: boolean;
  selectionMode?: 'none' | 'single' | 'multiple';
  selectedRowKeys?: readonly (string | number)[];
  accessibleLabel: string;
}

export interface TablePortEmits<Row extends TablePortRow> {
  rowActivate: [row: Row, event: Event];
  selectionChange: [keys: Array<string | number>, event: Event];
}

export interface TablePortSlots<Row extends TablePortRow> {
  topContent?(): unknown;
  empty?(): unknown;
  cell?(props: { row: Row; column: TablePortColumn }): unknown;
}
```

Row activation and selection remain distinct. Interactive rows need keyboard activation and accessible names. The horizontal scroll region must not swallow focus. Empty text comes from the platform.

### 5.9 IconPort

```ts
export type SceneIconName =
  | 'check' | 'close' | 'chevron-down' | 'chevron-right'
  | 'file' | 'folder' | 'refresh' | 'search' | 'user';

export interface IconPortProps {
  name: SceneIconName;
  size?: 14 | 16 | 18 | 20 | 24;
  label?: string;
  decorative?: boolean;
}
```

Scene uses semantic icon names. `decorative=true` hides the icon from assistive technology; non-decorative icons require a label. The Web Icon Adapter maps names to `ScIcon`.

### 5.10 Adapter Injection

```ts
export interface PrimitivePortDefinition<Props, Emits, Slots> {
  props: Props;
  emits: Emits;
  slots: Slots;
  exposed: PrimitiveHandle;
}

export interface PrimitiveBinding<Props, Emits, Slots> {
  component: Component;
  readonly contract: PrimitivePortDefinition<Props, Emits, Slots>;
}

export interface ScenePrimitiveAdapter {
  Button: PrimitiveBinding<ButtonPortProps, ButtonPortEmits, ButtonPortSlots>;
  Input: PrimitiveBinding<InputPortProps, InputPortEmits, InputPortSlots>;
  Select: PrimitiveBinding<SelectPortProps, SelectPortEmits, Record<never, never>>;
  DateField: PrimitiveBinding<DateFieldPortProps, DateFieldPortEmits, Record<never, never>>;
  Textarea: PrimitiveBinding<TextareaPortProps, TextareaPortEmits, Record<never, never>>;
  Table: PrimitiveBinding<TablePortProps<TablePortRow>, TablePortEmits<TablePortRow>, TablePortSlots<TablePortRow>>;
  Icon: PrimitiveBinding<IconPortProps, Record<never, never>, Record<never, never>>;
}

export interface SceneCompositionContext {
  primitives: ScenePrimitiveAdapter;
  density: SceneDensity;
}
```

Each `PrimitiveBinding.component` must use Vue `DefineComponent`, `ComponentProps` / `ComponentEmits` / `SlotsType` assertions, or equivalent typed machinery in 02C-02B to prove conformance with `contract`. The `contract` is also the runtime declaration consumed by component contract tests; it cannot exist only in documentation.

### 5.11 Target Provider

```ts
interface SceneUiProviderProps {
  primitives: ScenePrimitiveAdapter;
  density?: SceneDensity;
  compositionContext?: SceneCompositionContext;
}
```

The Provider injects the Primitive Adapter, density, and Scene composition context. It no longer chooses a vendor Kit, loads a vendor Driver, switches to a second control implementation, or owns colors, radii, heights, or business copy.

## 6. Component and Dependency Migration

```text
02C-02A  ADR (this batch)
      |
      v
02C-02B  Primitive Port v1 + Sc Adapter + Conformance Tests
      |
      +----> 02C-02C-1  Product direct actions: SceneButton -> ScButton
      |
      +----> 02C-02C-2  SceneFieldControl -> ScInput/Select/Date/Textarea
      |
      +----> 02C-02C-3  SceneRelationTable -> ScTable
                              |
                              v
02C-02D  Driver / Kit / Preference / Vendor / Token / Guard retirement
```

### 02C-02B

Deliver:

- Port types, Provider injection, and Adapter contract tests in `@sc/ui`.
- A thin Web `createScScenePrimitiveAdapter()`.
- A gap list and minimal corrections for ScDateField, ScSelect, and other conformance gaps.
- A feature flag for the new path; no broad consumer migration.

### 02C-02C

Three production samples:

1. `SceneButton -> ScButton`, including direct-action cleanup in `CanonicalActionBar` and `ContractFormDriverHost`.
2. `SceneFieldControl -> ScInput / ScSelect / ScDateField / ScTextarea`, retaining the SceneField DTO.
3. `SceneRelationTable -> ScTable`, retaining Scene table composition and row-navigation semantics.

Each sample must be independently switchable, verifiable, and reversible.

### 02C-02D

1. Stop new `scene_ui_driver` preference writes while retaining historical reads.
2. Migrate all Scene controls and remove the TDesign Scene Driver.
3. Move the TDesign and Icon Bridges into the Web Sc Design System.
4. Remove `primitives`, `icons`, and vendor runtime dependencies from `@sc/ui`.
5. Map Scene density to component tokens.
6. Remove the Kit Registry, Native Driver, and user Kit selection.
7. Update stale theme documentation and make guards enforce the target direction.

## 7. Guard Design

| Target guard | Existing anchor | New or changed assertions |
| --- | --- | --- |
| `scene_vendor_dependency_guard` | `frontend_primitive_adapter_guard.py` and vendor checks in the Scene Bridge Guard | Reject TDesign/TDesign Icons in `@sc/ui`; the only vendor exit moves into Web Sc Design System; reject the legacy inverse path |
| `scene_primitive_authority_guard` | `frontend_scene_component_bridge_guard.py` | Scene base controls must use Ports; allow layout `section/div/dl` and dedicated composition; reject reimplementations of button/input/select/textarea/table interaction |
| `scene_semantic_authority_guard` | `frontend_business_semantics_guard.py` | Scan `@sc/ui`; reject local currency, monetary formats, empty text, and status vocabularies; require platform-interpreted values |
| `scene_token_authority_guard` | `design_token_system.py`, `frontend_style_system_guard.py`, `frontend_theme_profile_guard.py` | Reject new color/radius/height facts in `kits/tokens.ts` or Scene; validate semantic-token derivation instead of equality between duplicate sources |
| `scene_adapter_contract_guard` | `primitive_adapter_contract_test.ts`, `scene_component_driver_bridge_test.ts` | Validate every Port prop, event, slot, focus rule, and ARIA contract against Sc |
| `scene_application_import_guard` | governed-entry checks in the Scene Bridge Guard | Ordinary product pages must not import Scene base controls; allow Scene composition, governed readonly renderers, and Adapter assembly; do not ban legitimate layout HTML |

Existing guards cannot remain unchanged because they explicitly require the legacy authority:

- The primitive adapter guard requires `@sc/ui/primitives`.
- The Scene Bridge Guard requires old Kit and Driver wiring.
- The theme-profile guard requires matching duplicate values in `kits/tokens.ts` and `profile.css`.

Guard changes belong to their implementation stages, not this ADR batch.

## 8. Acceptance Matrix

### 8.1 Port Conformance

| Capability | Assertion |
| --- | --- |
| Value change | `update:modelValue` / `change` match the real DOM/TDesign event |
| readonly / disabled | No value or business activation; visual and assistive states are explicit |
| Error state | `status=error`, `aria-invalid=true`, and error text linked through `aria-describedby` |
| Focus / Blur | Adapter exposes `focus()` and preserves event order in both directions |
| Keyboard | Button Enter/Space; Select open/select/Escape; Date entry/popup; Table row activation |
| Slots/help | Button content; input prefix/suffix; table top/cell/empty are preserved |
| IME | `compositionstart` / `compositionend` preserve real events and committed text |
| Accessibility | Names, roles, states, scroll-region behavior, and icon hiding match |

### 8.2 Same Field Through Two Paths

Use the same synthetic Contract V2 field through:

1. Ordinary `FormSection` directly using Sc base components.
2. `SceneFieldControl` through Primitive Port and the Web Sc Adapter.

Compare:

| Dimension | Required equality |
| --- | --- |
| Value change | Final callback value for input, select, date, and textarea |
| readonly / disabled | Editability and event emission |
| Error | Visible error, `aria-invalid`, and `aria-describedby` |
| Focus / Blur | Order, value, and accessible focus |
| Keyboard | Enter, Space, Escape, Tab, and arrow keys |
| Slots/help | prefix/suffix, help, source/hint, and empty state |
| Accessible name | Label association and icon-button name |

This is not a screenshot-only comparison. It checks DOM events, ARIA, focus order, and actual values.

### 8.3 Validation Layers

- L1: Port types, static dependency direction, Adapter contracts, and guard tests.
- L2: non-zero Scene component tests, existing Primitive Adapter tests, and business-semantic tests.
- L3: three samples in the governed local development environment.
- L4: browser journeys for affected fields and collections.
- L5: independent review, exact-head remote gates, and protected PR integration.

This ADR batch requires only documentation and `.agent` metadata checks. Product L2-L4 are not applicable.

## 9. Rollback and Compatibility

1. This ADR rolls back by deleting the documents and agent metadata; runtime is unaffected.
2. Until consumers migrate, 02C-02B Ports and Adapters have no behavioral effect.
3. Each 02C-02C sample is enabled independently under `scene_primitive_adapter_v1`; a failed sample rolls back without changing Contract V2 or data.
4. Keep the old Kit Driver until 02C-02D completes. After deletion, rollback restores a reviewed prior version and does not reintroduce user Kit selection.
5. Stop new `scene_ui_driver` writes and drain old values. Do not delete unaudited data.
6. Temporary TDesign compatibility exports are allowed during migration, but new code uses the Web-internal Bridge.
7. Scene DTOs, Contract V2, presentation, permissions, backend contracts, and persistence are outside the rollback surface because this plan does not modify them.

## 10. Explicit Non-Goals

- Move all Sc components into `@sc/ui`.
- Merge Sc and `@sc/ui` into a giant package.
- Create a third component library.
- Route every page through Scene.
- Require TDesign for every base control.
- Remove Native implementations immediately.
- Let users select `sc-native` or `tdesign-modern` as a product feature.
- Change Contract V2, the Renderer Extension Protocol, business presentation, backend performance, or permissions.
- Change product code, the stale theme document, or runtime configuration in this batch.
- Deploy or merge.

## 11. Known Gaps and Risks

1. `ScDateField` does not yet expose enough events for DateFieldPort.
2. `ScSelect` lacks a complete focus/blur/native change contract. An Adapter must not fabricate events.
3. `ScTextarea` and `ScTable` currently rely mainly on TDesign; Native fallback cannot be assumed from documentation.
4. `SceneButton` has both `activate` and passthrough `click` consumption. Activation semantics must converge before migration.
5. Forty-nine icon exports and 61 vendor exports currently coexist with Scene composition. Dependency removal must be staged to avoid breaking the build.
6. Existing guards and theme documentation preserve stale facts and must change with their owning migration stage.
7. This batch is a static read-only audit. It does not prove browser interaction, visual, keyboard, or screen-reader equivalence.

## 12. Conclusion and Next Step

The optimization is not merely an abstraction named `PrimitiveAdapter`. It removes:

- dual authority for base components;
- the Sc-to-`@sc/ui` inverse dependency;
- vendor drivers and runtime Kit selection inside Scene;
- Scene-owned business presentation and design-token facts.

The target is a bounded simplification: Sc remains the base-control authority, `@sc/ui` remains Scene composition, Primitive Ports invert the dependency, the Web supplies Sc Adapters, and TDesign/Native remain internal Sc implementation choices.

After independent review, start `FE-RENDERER-02C-02B` with Primitive Port v1 and the Sc Adapter. Do not migrate product components before this ADR is reviewed.
