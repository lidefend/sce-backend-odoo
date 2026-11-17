# NATIVE-SCENE-01 / P0-8 · Native Field Context and Options Passthrough

Status: implementation and exact-head verification pass on
`787a1846f30e95caf19dd3ff40eba49a7a387ffa`; publication and remote CI remain
pending.

Baseline main: `91056172b8cb1244ffa0378b3b9626c900e4d530`

## Boundary

- Formal Product Layer: P0 platform kernel product.
- Layer Target: explicit Odoo View field Context and options passthrough into
  the existing `fieldDescriptor.context` and `widget_options` carriers.
- Module: `addons/smart_core`.
- Standard vs User-Specific: platform-neutral native View semantics.
- Why Here: View XML parsing, field descriptors and generic Widget options are
  existing P0 mechanisms shared by every Odoo module.
- Why Not Elsewhere: no Renderer can recover a Context/options value dropped
  before the contract, and no industry/customer layer owns View XML.
- Blast Radius: Form relation/input fields and editable collection columns that
  declare native Context or options.
- Exclusions: Context evaluation, option support-matrix, embedded Widget nodes,
  professional views, Parser/AST rewrite, database and deployment.

## Gap

Field options already have an existing `widget_options` carrier and Context has
an existing descriptor carrier, but explicit XML values are not consistently
copied into them. The fix therefore stays in the native parser and uses the
existing contract fields.

## Implementation

The native parser will:

- copy View XML `context` as source evidence into `fieldInfo`;
- preserve parsed `options` in the existing `widget_options` map;
- keep raw attributes and occurrence `nativeBehavior.optionsRaw/contextRaw`
  available for audit identity.

The assembler will continue emitting the existing descriptor fields. No new
Context expression, option vocabulary or frontend decoder branch is added.

The parser files are also added to the assembled-contract cache input set so
future parser-only changes cannot leave stale contracts.

The assembled contract cache advances to `v76` with inputs SHA256
`643e7cb563b1f5a3b87a4d235ea4598bdfd66b3506408962b760b30a2cea939f`.
The A01 inventory binds inputs SHA256
`ea4168533172b3f894a0f766582089273efdd63bab51261efabe6d2b4054725d`.

## Verification

| Check | Result |
| --- | --- |
| `make verify.unified_page_contract.v2.assembler` | PASS |
| `make verify.native_occurrence.contract.orm` | PASS, 7 disposable ORM tests |
| `make verify.frontend.canonical_form_presenter.unit` | PASS, including native Context/options cases |
| `python3 addons/smart_core/tests/test_native_view_parser_surfaces.py` | PASS, 45 tests |
| `python3 addons/smart_core/tests/test_unified_page_contract_v2_kanban_action_registry.py` | PASS, 13 tests |
| `make ci.local.iteration` | PASS, 12 affected targets |
