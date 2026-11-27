# CONTRACT-POLYMORPHIC-REFERENCE-01

Independent P0 defect fix on main `a92114f0efb6733253d827e3a9985af21ab96be6`. Backend producer, canonical descriptor schema and frontend decoder share one acceptance package. No database migration, business behavior change or unrelated frontend iteration.

Backend and frontend changes are separate commits. Real Odoo producer output, strict decode and stale-cache exclusion are required; handcrafted JSON alone is insufficient.

## P0-A baseline and evidence

Main a92114f0e. `_field_widget` owns native `model_field` projection; `_strict_field_descriptor` now retains only the assembled `componentConfig.referenceModelField` and rejects absent, malformed or self-referencing pointers. Fixed relation semantics are unchanged. All assembler source routes share `_upgrade_contract_v2_field_descriptors`.

Assembled cache identity is defined only in `handlers/ui_contract_v2.py` and raised v125 → v126. It gates shared assembled reads, assembled snapshot use and the runtime ETag shortcut. Persistent runtime-source assets store native `ui_data`/`ui_meta` before assembly, not the final strict descriptor; they remain valid reassembly inputs. Native parsed-view/source caches already retain model_field and need no schema migration or independent version bump.

Producer 25 and cache 57 pure tests pass. Real notification contract ORM: `.runtime/test-baseline/1795741565363974863/receipt.json`. Output `.runtime/polymorphic-reference/real-contract.json` contains full native notification contract plus native menu Reference descriptor/value. Final descriptors validated against the JSON schema. Synthetic test records live only in the disposable transactional test database; no persistent environment or business behavior changed.

## P0-B / P0-C acceptance

Backend commit: `410acc65c6e04337a5df4880557cd4218ff50b42` (includes the v126 assembler source-digest lock). Frontend changes retain referenceModelField, require it for many2one_reference, allow self-identifying reference without fixed relation, and keep relation required for many2one/one2many/many2many. Unknown descriptor keys remain rejected.

`make verify.contract.polymorphic_reference.integration` produces the full real notification contract through UiContractV2Handler plus a real native menu Reference descriptor/value, validates JSON Schema, and feeds the untouched contract into the TypeScript snapshot decoder. Deleting only the strict pointer from that real output must fail even while componentConfig still contains it. Model identity, record value and renderer binding are checked. The original project form conformance also remains covered.

Final affected local validation: 30 targets passed in `.runtime/frontend-dev-validation/executions/20261127T011724Z-1820823-777803942/receipt.json`; producer, cache, schema, strict TypeScript, lint, fixed relation regression and real producer-to-consumer tests all pass. The two integration decoder cases are non-skipped TAP tests. Reproduction package: `.runtime/polymorphic-reference/real-contract.json` and the integration target log within that execution directory.

The coverage registry identifies the explicit polymorphic ORM tag through literal TEST_TAGS wiring. The planner selects this chain for producer/schema/decoder changes and excludes unrelated payment changes. Remote exact-HEAD CI and independent review remain pending; no merge or deployment is authorized by this local result. The general frontend iteration is stopped awaiting this task's result.
