# NATIVE-SCENE-01 / P0-7 · Native Field Domain Passthrough

Status: native Domain passthrough and focused backend/frontend contract tests
pass on exact head `9f82643e9438cc648e375c261fb9c9fcb04a70b9`; PR publication
and remote CI remain pending.

Baseline main: `c36f3a1d3e9231097388b970421dbe13cdb7281d`

## Boundary

- Formal Product Layer: P0 platform kernel product.
- Layer Target: explicit Odoo View field Domain passthrough into the existing
  field descriptor and relation-domain expression path.
- Modules: `addons/smart_core`.
- Standard vs User-Specific: platform-neutral native View semantics.
- Why Here: every Odoo module uses the same View XML field interpretation and
  relation-query contract chain.
- Why Not Elsewhere: a Renderer cannot reconstruct a Domain omitted before the
  Widget contract, and no industry/customer/low-code layer owns native XML.
- Blast Radius: Form and editable collection relation fields that declare an
  XML Domain.
- Exclusions: Context, Widget options support-matrix, embedded Widget nodes,
  List/Kanban/Activity Renderers, professional views, Parser/AST rewrite,
  database and deployment.

## Gap

The P0-4 occurrence identity preserves `domainRaw`, and the frontend already has
a bounded Domain expression evaluator. However, the Form Widget assembly only
compiles a Domain already present in the field source. The explicit XML
`domain` attribute therefore remains occurrence evidence but can be absent from
the field descriptor consumed by relation option queries.

## Implementation Contract

No parallel Domain expression or provenance object is introduced. The explicit
Odoo View value remains the native `domain` attribute and is projected into the
existing fields:

- `nativeIdentity.nativeBehavior.domainRaw` for occurrence evidence;
- `fieldDescriptor.domain` for the raw View expression;
- `fieldDescriptor.domain_expression` for the existing bounded compiler output.

The existing frontend relation evaluator consumes `domain_expression` unchanged.
Unsupported expressions retain `kind=unsupported` and continue to fail closed in
that existing evaluator.

## Producer

- Parser Form fields copy the View XML `domain` attribute into `fieldInfo`.
- Tree parsing copies a native View Domain into the existing column modifier
  carrier.
- `_native_field_node()` and `_field_source_with_node_info()` copy XML
  attributes without normalizing the Domain text.
- `_field_widget()` continues to use the existing
  `compile_relation_domain()` branch to publish
  `fieldDescriptor.domain_expression`.

The assembled contract cache advances to `v75` with inputs SHA256
`5da798c8e7afadaa2f0ed506f65807af07725ce9d2b09d2dafe6a2c4bd134f89`.
The refreshed A01 inventory binds inputs SHA256
`85fc009b474d8c6b4d06cfef329bb1e79e4a0bb0c35e4a1c8683afdb5b861264`.

## Consumer

The Contract V2 decoder, normalized store, relation option query and bounded
expression evaluator are unchanged. This checkpoint proves the native View
Domain now reaches that existing path instead of creating a second one.

## Verification

| Check | Result |
| --- | --- |
| `make verify.unified_page_contract.v2.schema` | PASS |
| `make verify.unified_page_contract.v2.assembler` | PASS |
| `make verify.native_occurrence.contract.orm` | PASS, 7 disposable ORM tests |
| `python3 addons/smart_core/tests/test_native_view_parser_surfaces.py` | PASS, 45 tests |
| `python3 addons/smart_core/tests/test_unified_page_contract_v2_kanban_action_registry.py` | PASS, 13 tests |
| `make verify.frontend.dev.incremental.unit` | PASS, 166 tests |
| `make verify.frontend.contract_record_action_state.unit` | PASS, 38 cases |
| `make verify.form_structure_authority_unification.unit` | PASS, 264 tests |
| `make ci.local.iteration` | PASS on `9f82643e9`, 12 affected targets |

## Deliberate Limits

- Context remains raw occurrence evidence; no context execution protocol is added.
- Widget options retain their existing pass-through and support matrix.
- Embedded Widget nodes, List/Kanban/Activity Renderers and professional views
  remain excluded.
- L4 browser, real-role and business execution acceptance is not claimed.

## Rollback

Revert the parser/assembler Domain passthrough, cache re-pin, focused tests and
this audit record together. No database or persistent configuration rollback is
required.
