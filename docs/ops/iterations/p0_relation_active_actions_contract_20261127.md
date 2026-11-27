# P0 Relation Active Actions Contract 2026-11-27

## Objective

Move occurrence-level `relation_active_actions` from the non-authoritative
`componentConfig` carrier into strict `fieldDescriptor.relationActiveActions`, preserve
normalized modifier expressions, and make the generic frontend relation-action consumer
descriptor-only and fail-closed.

## Boundary

- Formal Product Layer: P0 platform kernel.
- Layer Target: Unified Page Contract V2 field semantics.
- Modules: `smart_core` and the generic frontend Contract V2 consumer.
- Standard vs user-specific: platform mechanism.
- Exclusions: server authorization, business state, relation create/edit executors,
  database migration, import lifecycle, and PR 1019 source mutation.

## Candidate

- Branch: `fix/p0-relation-active-actions-contract-20261127`
- Baseline: `bfc954c0b6fe2bbaa5a94c017ef8c69ec983d9a5`
- Worktree: `/home/lidefend/workspace/sce-backend-odoo-p0-relation-active-actions-20261127`

## Acceptance

- Every occurrence owns its own descriptor declaration.
- Boolean and normalized AST values survive producer, schema, decoder and consumer.
- Missing actions remain `null`; frontend never substitutes allow.
- `componentConfig.relationActiveActions` is not emitted and is ignored by consumption.
- A real assembler contract is decoded and consumed by the frontend integration test.

## Evidence

### Backend producer and schema

- `python3 addons/smart_core/tests/test_unified_page_contract_v2_mobile_compact.py`:
  153 tests passed.
- `python3 addons/smart_core/tests/test_native_view_parser_surfaces.py`:
  54 tests passed.
- `make verify.p0_contract_producer.p0a.unit`: 44 Python tests plus the
  TypeScript P0-A decoder/page-block checks passed.
- `make verify.unified_page_contract.v2.schema`: unified page schema guard and
  seven guard tests passed.
- `make verify.test.coverage.registry`: all declared test groups are gated or
  dispositioned.

### Real producer to frontend consumer

`make ci.local.iteration` ran the real assembler under the governed
`local.test` profile. The backend receipt recorded 3 passing ORM tests. The
assembler emitted 3 relation descriptors:

- many2one `create=false`, `write=true`;
- many2one `create` as a normalized field-comparison AST, without a fabricated
  `write`;
- many2many_tags `create=true`, without a fabricated `write`.

The Python schema validator accepted all three descriptors. The TypeScript
integration then decoded the exact same contract, exercised
`ContractV2FormFieldDescriptor`, and verified that the generic relation consumer
reads only `fieldDescriptor.relationActiveActions`. Conflicting old
`componentConfig.relationActiveActions` values were ignored, and missing
descriptor declarations returned `null`.

The producer integration also guards that no relation action declaration remains
under `componentConfig`, in either camelCase or snake_case.

The assembled contract cache fingerprint was re-pinned from
`ui-contract-v2-demand-driven-snapshot-v126` to `v127`, and the assembler guard
digest now covers the changed producer/handler inputs. Without this, a process
could continue serving the pre-fix contract from cache.

### Tooling repair

The recurring root-owned `artifacts/` permission failure is handled in
`p0_contract_producer_descriptor_evidence.py`: an unwritable output projection
falls back to `.runtime/p0-contract-producer-evidence` and reports the actual
written path. The descriptor and money decode entrypoints now consume explicit
`.runtime` outputs instead of hard-coded `artifacts/` imports. Two regression
tests cover writable and unwritable output projections.

### Exact head

The candidate is not yet frozen. `make ci.local.iteration` and remote required
CI must be rerun on the exact clean commit before handoff.

Dirty-candidate iteration passed with 37 executed targets, 18 test targets,
1,142 tests, nine static checks and zero unmapped paths. Receipt:
`.runtime/frontend-dev-validation/executions/20261127T065541Z-601303-847997708/receipt.json`.
