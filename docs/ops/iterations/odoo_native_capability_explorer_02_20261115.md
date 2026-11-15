# ODOO-NATIVE-CAPABILITY-EXPLORER-02

## Candidate

- Baseline: `3639f35b1cf80b11c2c62766ba53839be3440952`
- Branch: `audit/platform-capability-studio-01-20261115`
- Stage: classification and read-only API design complete

## Scope

- Classify native entries using existing scene bindings, release-policy groups and
  native menu centers.
- Mark entries without authoritative business-domain evidence as `unclassified`.
- Design list, detail and diagnose read contracts.

## Exclusions

- Product runtime code.
- Capability browser or scene editor UI.
- New persistent registry or write endpoint.
- Deployment or merge.

## Verification

- `verify.odoo_native_capability_explorer.unit`: PASS, 10 tests.
- Read-only `sc_demo` classification probe: PASS.
- `verify.agent.ledger.unit`: PASS, 18 tests.
- `make ci.local.iteration`: PASS with the classification and ledger targets.
- 282 native entries have a stable native center.
- 75 entries have an authoritative business domain from existing product-scenario
  bindings.
- 207 entries are explicitly `unclassified`; no Chinese-label or model-prefix
  guessing was used.
- 0 entries have ambiguous scene bindings.
- Raw runtime log:
  `.runtime/agent-runs/ODOO-NATIVE-CAPABILITY-EXPLORER-02/runtime-classification.log`,
  SHA256 `646a98626a2f8ba423396d591cf12d8d179ddafc740a65a20517078af715efcd`.

## Design Deliverables

- `docs/architecture/odoo_native_capability_explorer_api_contract_v1.md`
- `docs/architecture/odoo_native_capability_explorer_api_contract_v1.en.md`
- `docs/architecture/odoo_native_capability_explorer_api_contract_v1.json`

The contract covers list/detail/diagnose read intents, pagination, search,
freshness, authorization and explicit non-goals. No handler, write endpoint,
persistent capability row or frontend page was added.
