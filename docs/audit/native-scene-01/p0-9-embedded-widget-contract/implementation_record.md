# NATIVE-SCENE-01 / P0-9 · Embedded Widget Node Contract

Status: local affected validation passed; exact-head publication and remote gates
pending.

Baseline main: `bec4a38da10f15d6f4008af355db3bcc4332e13d`

## Boundary

- Formal Product Layer: P0 platform kernel product.
- Layer Target: native Form embedded `<widget name="...">` node identity,
  component readiness and generic Contract V2 consumption.
- Modules: `addons/smart_core` and the generic web frontend.
- Standard vs User-Specific: platform-neutral native View semantics.
- Why Here: View XML nodes, occurrence identity and component readiness belong
  to the shared P0 contract runtime.
- Why Not Elsewhere: no industry or customer layer owns a native widget token,
  and the frontend cannot recover facts dropped before the contract.
- Blast Radius: native Form embedded widget nodes, node components and their
  modifiers.
- Exclusions: business UI for `sc_insight_banner`, `sc_stage_requirements` or
  `sc_next_actions`; OWL hosting; business-method dispatch; professional view
  Renderer work; persistence, database, ACL and deployment changes.

## Target

`web_ribbon` is consumed through a registered node component. Every other
embedded widget is preserved as a native node and rejected through the existing
contract-gap path with an explicit reason. Recognition is separate from support.

## Implemented Contract

- The Form parser preserves widget name, native locator, occurrence index, source
  position, raw attributes, raw options, parsed options and normalized modifiers.
- The compatibility parser path preserves existing native identity when present
  and never manufactures one when absent.
- Options resolution is type-checked: raw evidence must be a string, parsed
  resolution must carry its parsed value, and unsupported expression evidence
  remains distinguishable.
- The existing native occurrence identity algorithm now accepts the `widget`
  kind.
- The assembler publishes widget nodes with the existing layout node,
  `componentKey`, `componentConfig` and status carriers. Widget nodes do not gain
  `fieldCode` or `fieldDescriptor`.
- `contracts/registry/semantic.yaml` maps `web_ribbon` to
  `sc.display.ribbon`. Unknown embedded widgets use
  `sc.unsupported.native_node` with `NATIVE_VIEW_WIDGET_UNSUPPORTED`.
- Contract V2 advances to `2.5.0`. The schema accepts `widget` occurrence
  identity and the frontend decoder consumes versions through `2.5.x`.
- The assembler cache advances to `v78`; its complete input SHA256 is
  `1875c4ddf4f1dfa5b7759d6268762a37245a70690f032caf43ff3a3a825cf6aa`.

## Positive Contract

The producer-generated fixture
`frontend/apps/web/scripts/fixtures/native_embedded_widget_contract_v2.json`
contains two same-name `web_ribbon` occurrences and one
`sc_stage_requirements` occurrence.

- Both ribbons preserve distinct `widget` occurrence identities.
- `Paid` preserves `{'bg_color': 'text-bg-success'}`.
- `Draft` preserves the legal options value `False`.
- The industry widget preserves `{'limit': 3}` and the explicit unsupported
  reason.
- The web client decodes the supported subset through the normal schema decoder,
  store and presenter.
- The decoder does not synthesize `fieldCode` or `fieldInfo` for widget nodes,
  and rejects field carriers supplied by a client.
- Native-tree and canonical rendering paths both show one ribbon per visible
  occurrence.
- Feedback nodes continue to resolve the real TDesign Alert component; component
  resolution warnings are regression failures.
- Self-hidden and parent-hidden nodes render nothing.
- The unsupported industry node stops through `ContractGapError` before any
  business request is emitted.
- Native attribute name/options evidence is checked against projected widget
  names/options and rejected on conflict.
- A registered widget lacking native occurrence identity is projected as
  unsupported with `NATIVE_VIEW_WIDGET_IDENTITY_MISSING`, never as a contradictory
  ready-unsupported combination.

## Unsupported Contract

No P0 code contains a name branch for an industry widget. All unmapped names use
the default node component and reason. The following native nodes are therefore
recognized but explicitly unsupported:

| View | Native widget |
| --- | --- |
| `smart_construction_core.view_project_form_sc_core` | `sc_insight_banner` |
| `smart_construction_core.view_project_overview_form` | `sc_stage_requirements` |
| `smart_construction_core.view_project_overview_form` | `sc_next_actions` |

These pages previously omitted the widgets silently or showed incomplete
name-based placeholders. They now fail closed with
`NATIVE_VIEW_WIDGET_UNSUPPORTED` until their P1 business renderers are separately
approved. No business UI, data service or action binding is implemented here.

## Verification

| Check | Result |
| --- | --- |
| `make ci.local.iteration` | PASS, 38 required targets, 23 executed and 15 content-identical prefixes reused |
| `make verify.native_occurrence.contract.orm` | PASS, 8 disposable ORM tests |
| `make verify.frontend.native_embedded_widget.browser` | PASS, both render paths, self/parent hidden cases, unsupported fail-closed, 0 business requests |
| `make verify.frontend.node_component.unit` | PASS, 48 cases |
| `make verify.frontend.node_component.component` | PASS, actual SFC server/browser component checks |
| `make verify.frontend.canonical_form_presenter.unit` | PASS |
| `make verify.semantic.registry.lint` | PASS |
| `make verify.unified_page_contract.v2.schema` | PASS |
| `make verify.unified_page_contract.v2.assembler` | PASS |
| `make verify.backend.contract_lifecycle.authority` | PASS |
| `make verify.local.dev.conditioned.feedback.orm` | PASS, 0 failed of 26 tests |
| `make verify.frontend.lint.src` | PASS, warnings only in pre-existing files |
| `make verify.frontend.typecheck.strict` | PASS |
| `make verify.docs.all` | FAIL, pre-existing `baseline_evidence_defect`: 72 repository-wide links remain unresolved |

Not run: deployment, L4 role/business acceptance, real consumption of
`sc_insight_banner`, `sc_stage_requirements` or `sc_next_actions`.
