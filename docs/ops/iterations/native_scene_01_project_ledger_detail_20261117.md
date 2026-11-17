# NATIVE-SCENE-01 / Project Ledger to Detail Closure

Status: verification_pending

## Boundary

- Formal Product Layer: P1 construction industry standard product.
- Layer Target: formal project ledger, project detail and declared project actions.
- Module: `smart_construction_core` plus generic `frontend/apps/web` consumption.
- Standard vs User-Specific: construction product standard.
- Why Here: project stages, stage requirements, project insight and next actions
  are construction business semantics.
- Why Not Elsewhere: P0 may own only generic node transport/consumption;
  customer-specific or production data changes are not required.
- Blast Radius: project ledger and project detail presentation, declared project
  actions, one reversible project field write, restricted-role behavior, list
  return identity and the project presentation acceptance target.

## Target User Result

Open a draft project and an in-progress project from the formal 项目台账 entry,
render their declared content and actions, perform one reversible edit with
server readback, verify restricted-role behavior, and return to the same list
identity at 1440px and 390px.

## Explicit Exclusions

- unrelated contract/payment/cache iterations;
- professional Renderer redesign;
- OWL/iframe hosting or native JavaScript execution;
- production or customer data mutation;
- deleting unsupported-contract negative coverage.

## Evidence

### Existing runtime finding before this batch

The deployed main `e890568b9c75bcf8059c5ea67030992492dbd440` opened the formal
project record `/r/project.project/15` from the demo object entry and produced
the expected structured contract gap:

```text
native_view_widget.NATIVE_VIEW_WIDGET_UNSUPPORTED
```

The observed final contract was `2.5.0`; its unsupported project Widget was
`sc_insight_banner`; `web_ribbon` was already rendered through
`sc.display.ribbon`. Both 1440px and 390px had no horizontal overflow, no
console error, no page error and no 5xx response. This proves correct
fail-closed decoding, not project-page usability.

### Implementation

- P0 embedded Widget nodes may receive a product-layer payload selected by the
  already stable `occurrenceKey`; the kernel performs only payload transport,
  identity/provenance checks and fail-closed degradation.
- P1 `smart_construction_core` maps the three project Widgets to existing
  project services:
  - `sc_insight_banner` -> `insight_summary.v1`;
  - `sc_stage_requirements` -> `action_list.v1`;
  - `sc_next_actions` -> `action_list.v1`.
- The project payload preserves stage completion, insight wording and next
  action target/context. It does not infer business data from Widget names in
  the frontend.
- The frontend renders the payload through existing cards, buttons and the
  existing native action dispatch chain.
- Unsupported or payload-missing nodes still fail closed. The dedicated negative
  case remains separate from the positive project acceptance target.

### Local verification

| Check | Result |
| --- | --- |
| `verify.semantic.registry.lint` | PASS |
| `verify.unified_page_contract.v2.schema` | PASS |
| `verify.unified_page_contract.v2.assembler` | PASS |
| `verify.node_component_validation.unit` | PASS |
| P1 project widget payload service test | PASS, 3 tests |
| `verify.frontend.node_component.unit` | PASS, 49 cases |
| `verify.frontend.node_component.component` | PASS, 59 SSR cases plus existing browser/component locks |
| `verify.frontend.canonical_form_presenter.unit` | PASS |
| `make ci.local.iteration` | PASS; 33 affected targets, 71 ORM tests plus frontend contract/component suites |

Dry-run of the daily presentation probe remains valid only as pre-fix evidence.
The deployed project page and business journey must be re-run after candidate
release; runtime save/readback and restricted-role evidence remain pending.
