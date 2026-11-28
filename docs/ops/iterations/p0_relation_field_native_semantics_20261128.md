# P0 Relation Field Native Semantics 2026-11-28

## Objective

Normalize Odoo `get_view` relational access declarations so every form relation
field exposes them through `fieldDescriptor.relationActiveActions`, not through
generic field `attributes`.

## Boundary

- Formal Product Layer: P0 platform kernel.
- Layer Target: Unified Page Contract V2 native occurrence and field descriptor
  projection.
- Module: `smart_core`.
- Standard vs user-specific: platform mechanism.
- Why Here: Odoo `get_view` and the custom native-view parser own the projection;
  `relationActiveActions` is the existing strict field-level relation carrier.
- Why Not Elsewhere: ACL remains in Odoo, the frontend must not reinterpret
  generic attributes, and P1/P2/P3 do not own this mechanism.
- Blast Radius: relational field occurrences in forms and reusable tree
  occurrences; generic `attributes`; `many2many_tags` create/write projection.
- Exclusions: ACL or permission changes, host-field readonly semantics, relation
  executors, business writes, low-code configuration, migrations, PR 1019.

## Fact Chain

1. The source view declares `sc_user_permission_group_ids` as an editable
   `many2many_tags` field with no `can_create`, `can_write` or `readonly`.
2. Odoo `get_view` marks editable many2one/many2many fields with
   `model_access_rights`; `_postprocess_access_rights` replaces it with target
   model `check_access_rights('create'/'write')` results.
3. The fixture account can read but cannot write `res.groups`, so Odoo injects
   `can_create="False"` and `can_write="False"` on the relation occurrence.
4. Those attributes mean target relation create/edit capability. They do not
   mean the host `res.users` field is readonly.
5. The final contract already declares the host field and widget as editable.
   The generic frontend relation control must therefore consume only the
   relation contract, never reinterpret these raw attributes as field auth.

## Acceptance

- Every relational occurrence projects `can_create` and `can_write` into strict
  `relationActiveActions`.
- Generic relational `attributes` no longer retain those two operational keys.
- `many2many_tags` preserves both create and write declarations when Odoo
  supplies them.
- Non-relational `can_create` attributes remain untouched.
- Parser, assembler, schema and frontend decoder checks execute non-zero.

## Evidence

### Parser and frontend consumers

- `make verify.frontend.collection_view_semantics.unit`: passed.
- Native parser executed 54 tests; collection semantics executed 21 tests.
- Relational `can_create` and `can_write` are present only as
  `relation_active_actions` at the parser boundary.
- Generic relation-field `attributes` no longer contain either operational key.
- Non-relational `can_create` remains raw, proving the normalization is scoped
  to actual relational semantics.

### Producer, schema and cache identity

- `make verify.p0_contract_producer.p0a.unit`: passed, 44 Python tests plus the
  TypeScript P0-A decoder check.
- `make verify.unified_page_contract.v2.schema`: passed, 7 tests.
- `make verify.unified_page_contract.v2.assembler`: passed.
- Assembled-contract cache version is
  `ui-contract-v2-demand-driven-snapshot-v131`.
- The input digest is
  `b3ce0213aee385c9a43733b58ff72f2502a2010e2fd8323320892682e969e875`.

### Real producer to frontend consumer

- `make verify.contract.relation_active_actions.integration`: passed.
- Governed isolated ORM execution: 3 tests.
- Real contract output:
  `.runtime/relation-active-actions/real-contract.json`.
- Frontend strict decode and consumer test: 1 test.
- `partner_id`: `create=false`, `write=true`.
- `reviewer_id`: dynamic `create=state != 'done'`, no invented `write`.
- `tag_ids`: `create=true`, `write=false`.

### Incremental gate

- `make ci.local.iteration`: passed.
- 24 executed targets, 9 non-zero test targets, 725 tests, 6 static checks and
  0 unmapped paths.
- Receipt:
  `.runtime/frontend-dev-validation/executions/20261128T073119Z-498373-218411761/receipt.json`.

The exact-head PR gate remains pending because the candidate is not yet
committed or published.
