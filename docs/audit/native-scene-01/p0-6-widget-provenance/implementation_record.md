# NATIVE-SCENE-01 / P0-6 · Native Widget Provenance and Fail-Closed Resolution

Status: the merged implementation had one independent-review source-authority
defect in the Form node assembly path. The bounded repair and its assembly-chain
regression coverage pass on exact head `8baf4773c1ace0f69f73d507229118a42f0d7f65`;
PR publication, remote CI and final review remain pending.

Baseline main: `bb63c755238b27c39844701411de4c4dddd8c17e`

Review-repair baseline main: `15d8e83923943e784b4364114d0b07c2a62bee79`

## 1. Boundary

- Formal Product Layer: P0 platform kernel product.
- Layer Target: native Odoo View Widget provenance and generic Contract V2
  component resolution.
- Modules: `addons/smart_core`, `contracts/registry/` and the generic Web
  Contract V2 decoder.
- Standard vs User-Specific: platform-neutral. No industry or customer
  semantics are introduced.
- Why Here: every Odoo module uses the same XML Widget interpretation and
  component-selection chain.
- Why Not Elsewhere: a Renderer cannot reconstruct a lost explicit Widget name;
  P1/P2/P3 configuration is not the owner of native View semantics.
- Blast Radius: Form, List, Kanban and other fields that pass through the
  generic Widget projection; all current observed XML Widget names are declared
  in the existing semantic registry.
- Exclusions: List/Kanban/Activity Renderer implementation, embedded
  `<widget name>` implementation, Domain/Context compilation, professional
  analysis views, database and business configuration.

## 2. Implemented Contract

The existing Widget now carries a `componentConfig.widgetProvenance` object:

```text
nativeWidget
widgetSource
declaredWidget
derivedWidgetType
resolvedWidgetType
resolutionStatus
reasonCode
```

Sources:

- `native_explicit`: `widget="..."` was present in the native View XML.
- `model_metadata_derived`: the value came from field type defaults.
- `compatibility_default`: no native marker exists; a bare compatibility
  `widget` value remains useful but is not presented as a native fact.

Resolution statuses:

- `ready`
- `fallback`
- `unsupported`
- `not_applicable`

`componentConfig.nativeWidget` is now published only for
`native_explicit`. A field-type default no longer claims to be an Odoo-native
Widget declaration.

## 3. Registry Authority

`contracts/registry/semantic.yaml:22-84` now declares every observed repository
Widget name and whether it is:

- ready;
- a known generic/visual fallback;
- unsupported.

The list includes all 18 names in the current A01 view inventory and other
canonical aliases already supported by the platform.

Examples:

- `statusbar`, `badge`, `percentage`, `json`, `daterange`,
  `analytic_distribution`, `many2many_binary` and `many2one_avatar_user` are
  declared ready.
- `handle`, `image`, `boolean_toggle` and `res_partner_many2one` are explicit
  fallbacks.
- `domain` and the QWeb-only `tier_validation` are unsupported.
- any explicit token absent from the registry is unresolved and fail-closed.

`contracts/registry/component.yaml:70` declares:

```text
sc.unsupported.native_widget
  semantic: unsupported_native_widget
  field_types: ["*"]
  readiness: fail_closed
```

This reuses the existing semantic/component registry and frontend readiness
mechanism; no second component dictionary was introduced.

The generator projects the declaration into
`semantic_registry_generated.py`. Semantic lint checks the generated Python and
TypeScript carriers and verifies that every observed Widget has a declaration.
The A01 inventory was regenerated after commit and now binds clean revision
`7af300c1ecf882916e421ebeceee1e587a438753` with no dirty paths. Its inputs
SHA256 remains
`4dfb0b593025817559af176954a03a070ddf9df676b3d358e8b96ccd6d9de17e`.

## 4. Producer

### 4.1 Parser source marker

`addons/smart_core/app_config_engine/services/view_Parser/base.py:264-273`
marks field-type defaults as `model_metadata_derived`.

`parsers Tree Form.py`:

- `:537-545` marks each Tree column occurrence according to whether the XML
  explicitly supplies `widget`.
- `:584-587` carries the source into `columns_schema`.
- `:1185-1204` marks explicit Form XML Widgets and retains derived defaults
  otherwise.
- `:1752-1768` applies the same rule to the lossless conversion path.

### 4.2 Generic resolution

`addons/smart_core/core/native_widget_profile.py` is a pure project helper:

- `:28-50` distinguishes explicit, metadata-derived and compatibility sources;
- `:53-72` constructs the provenance object;
- `:75-92` selects the normal component resolution or the explicit fail-closed
  component.

`addons/smart_core/core/contract_runtime/semantic_resolver.py:130-149`
looks up explicit Widget declarations. An unrecognized explicit token returns
`NATIVE_WIDGET_UNRECOGNIZED`; it is never treated as a successful type-derived
control.

`addons/smart_core/core/unified_page_contract_v2_assembler.py:2316-2348` uses
the provenance before component selection and publishes:

- canonical `widgetType`;
- registry-resolved `componentKey`;
- explicit-only `nativeWidget`;
- nested `widgetProvenance`.

Normalized child Widget nodes cannot re-promote canonical `widgetType` back to
native evidence: `_field_source_with_node_info()` accepts only an XML
`attributes.widget` value as explicit source.

## 5. Consumer

`frontend/apps/web/src/app/contracts/v2/types.ts:369-388` defines the typed
Widget provenance shape.

`frontend/apps/web/src/app/contracts/v2/schema.ts:781-895`:

- strictly decodes the optional provenance object;
- rejects unknown keys;
- validates source and resolution enums;
- requires a native token for explicit source;
- forbids `nativeWidget` for non-native sources;
- requires unsupported status to use
  `sc.unsupported.native_widget` and a reason code;
- forbids the fail-closed component for supported/fallback facts.

`sc.unsupported.native_widget` is registered with `readiness: fail_closed`.
The existing professional component registry therefore refuses to bind a
working input control to an unsupported native Widget.

## 6. Independent Review Repair

Independent review found an S2 defect at the Form node assembly boundary:
`_native_field_node()` treated a canonical top-level `node.widget` as fresh
native XML evidence. That could:

- promote a `model_metadata_derived` or `compatibility_default` Widget to
  `native_explicit`;
- overwrite a parser-declared native token with a canonical type such as
  `input` or `date`;
- make the intermediate node/component evidence disagree with the final formal
  Widget descriptor.

The repair makes the authority order explicit:

1. XML `attributes.widget` is native evidence;
2. an occurrence-level `fieldInfo.widget_source` remains authoritative;
3. an explicit source carried by the occurrence field preserves its native
   token;
4. a bare canonical `node.widget` is only a compatibility value and cannot
   promote or overwrite a stronger source.

Because the Form node output changes, the assembled contract cache advances
from `v72` to `v74` and its input fingerprint is re-pinned to
`70c83ba9e99757ce570f70db30d97e038d1d8947085cd933cdb1a1ea178a791b`.

`test_unified_page_contract_v2_kanban_action_registry.py` now exercises four
cases through `_native_field_node()` and the formal
`_field_source_with_node_info()` → `_field_widget()` path:

- model-derived plus canonical node Widget;
- unmarked legacy plus bare Widget;
- unknown explicit native token plus canonical node Widget;
- supported explicit `daterange` plus canonical node Widget.

The frontend `daterange` positive fixture was also corrected to use the real
Producer shape (`widgetType=date`, `componentKey=sc.input.date`) instead of
claiming date provenance while retaining a text-input fixture.

The review-repair inventory run binds 1,354 source files with inputs SHA256
`b617f91a862f148ecadfcceed9ff5c9b8db2644bb1158322d774af68561a6f99`.

## 7. Validation Governance Closure

The implementation exposed two validation-system issues unrelated to product
semantics:

1. local iteration and freeze preparation evaluated the all/deployment plan,
   causing deployment-only runtime evidence to block a P0 contract candidate;
2. newly added checks initially had no lane anchor and no changed-path mapping.

Corrections:

- `make/guards.mk:372-376` adds `ci.delivery.plan.merge`;
- `make/ci.mk` uses the merge-stage plan for local iteration and freeze
  preparation;
- backend Widget provenance is wired into
  `verify.contract.architecture.suite`;
- frontend Widget provenance is wired into the frontend quick and release lanes;
- changed-path routing maps Parser/Widget/semantic changes to the exact
  provenance and semantic-registry tests;
- the contract-schema snake-case whitelist registers only the new governed
  provenance tokens.

Deployment-only daily runtime evidence remains deferred to deployment, not lost
or waived.

## 8. Verification

Passed during the dirty candidate and rechecked on the clean exact head:

| Check | Result |
| --- | --- |
| `make verify.native_widget.provenance.unit` | PASS, 7 tests |
| `make verify.frontend.native_widget_provenance.unit` | PASS |
| `make verify.semantic.registry.lint` | PASS |
| `make verify.unified_page_contract.v2.schema` | PASS, 4 tests |
| `make verify.unified_page_contract.v2.assembler` | PASS, 4 sources |
| `make verify.frontend.professional_component_registry.unit` | PASS |
| `make verify.form_structure_authority_unification.unit` | PASS, 264 tests |
| `make verify.frontend.dev.incremental.unit` | PASS, 165 tests |
| `python3 addons/smart_core/tests/test_unified_page_contract_v2_kanban_action_registry.py` | PASS, 12 tests after review repair |
| `make verify.native_widget.provenance.unit` | PASS, 7 tests after review repair |
| `make verify.frontend.native_widget_provenance.unit` | PASS after review repair |
| `make audit.verification.lane_coverage.check` | PASS |
| `make ci.local.iteration` | PASS on dirty candidate |
| `make ci.local.iteration` | PASS on `7af300c1e`, 23 required targets |
| `make ci.local.iteration` | PASS on review-repair dirty candidate, 11 required targets |
| `make ci.local.iteration` | PASS on `8baf4773c`, 11 required targets |
| `python3 scripts/audit/native_scene_inventory.py --check` | PASS after clean-head regeneration |

The exact-head iteration executed all 23 required targets, including frontend
lint, strict typecheck and semantic-registry generation checks, after the
validation routing corrections. The independent-review repair then re-ran the
affected 11-target set, including strict typecheck and all Unified Page
Contract action/assembler/runtime/status guards.

## 9. Deliberate Limits

This batch does not implement:

- rendering of unsupported Widgets;
- a Domain editor;
- a QWeb/tier-validation renderer;
- List/Kanban/Activity Widget semantics;
- embedded `<widget name>` node components;
- Domain/Context compilation into Widget selection behavior;
- Calendar, Gantt, Pivot, Graph or Dashboard;
- browser or real-role L4 acceptance.

Those remain separate, reviewable follow-up checkpoints.

## 10. Rollback

Revert the P0-6 registry, parser marker, Widget profile, Contract V2 Decoder,
focused tests, validation-routing and this record together. No database,
persistent configuration or deployed runtime state is involved.
