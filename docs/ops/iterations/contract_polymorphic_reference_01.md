# CONTRACT-POLYMORPHIC-REFERENCE-01

Independent P0 defect fix on main `a92114f0efb6733253d827e3a9985af21ab96be6`. Backend producer, canonical descriptor schema and frontend decoder share one acceptance package. No database migration, business behavior change or unrelated frontend iteration.

Backend and frontend changes are separate commits. Real Odoo producer output, strict decode and stale-cache exclusion are required; handcrafted JSON alone is insufficient.

## P0-A baseline and evidence

Main a92114f0e. `_field_widget` owns native `model_field` projection; `_strict_field_descriptor` now retains only the assembled `componentConfig.referenceModelField` and rejects absent, malformed or self-referencing pointers. Fixed relation semantics are unchanged. All assembler source routes share `_upgrade_contract_v2_field_descriptors`.

Assembled cache identity is defined only in `handlers/ui_contract_v2.py` and raised v125 → v126. It gates shared assembled reads, assembled snapshot use and the runtime ETag shortcut. Persistent runtime-source assets store native `ui_data`/`ui_meta` before assembly, not the final strict descriptor; they remain valid reassembly inputs. Native parsed-view/source caches already retain model_field and need no schema migration or independent version bump.

Producer 25 and cache 57 pure tests pass. Real notification contract ORM: `.runtime/test-baseline/1795741565363974863/receipt.json`. Output `.runtime/polymorphic-reference/real-contract.json` contains full native notification contract plus native menu Reference descriptor/value. Final descriptors validated against the JSON schema. Synthetic test records live only in the disposable transactional test database; no persistent environment or business behavior changed.
