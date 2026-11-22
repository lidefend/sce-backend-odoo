# P0-CONTRACT-PRODUCER-01-P0A Implementation

## Batch identity

- Base main: `dbee64518ba9b35099408c91758c1c85d6d3a62f`
- Base tree: `ab1d9a0b3a838d59b061fcdea56f89c93fade69c`
- Branch: `feature/p0-contract-producer-01-p0a-implementation-20261123`
- Result index: `.agent/runs/P0-CONTRACT-PRODUCER-01-P0A/run.json`

## Ownership

- Formal product layer: P0 platform contract runtime.
- Layer target: Contract V2 2.6, Page Orchestration 2.1,
  `page-block-data.v1`, and existing semantic/component registries.
- Modules: `smart_core`, `smart_construction_core`, `frontend/apps/web`.
- Standard vs user-specific: platform standard.

## Objective

Implement P0-A in four ordered stages:

1. strict consumer decoding and Widget registry resolution;
2. accepted-version negotiation and complete legacy fallback;
3. faithful Page Block data production;
4. real ORM, Contract V2, Chromium and responsive acceptance.

## Exclusions

- No P0-B attachment-fact product implementation.
- No P0-C action/feedback product implementation.
- No second runtime, Renderer Registry, Bundle or field vocabulary.
- No Odoo ACL, record-rule, workflow, file-authorization or database-shape change.
- No deployment and no FCF-02-2 unlock.

## Progress

- Batch registered from the approved PR #973 merge.
- P0-A-1 consumer decoding is implemented:
  - Contract V2 accepts negotiated `2.6.0`;
  - Page Orchestration accepts `2.1.0`;
  - one `decodeContractV2FieldDescriptor()` validates structure, semantic scope,
    native Widget status and Registry resolution;
  - Widget fallback reason metadata is returned outside the descriptor.
- P0-A-2 negotiation is implemented:
  - every intent carries `accepted_contract_versions` and declared capabilities;
  - `ui.contract.v2`, `system.init`, workspace and dashboard entry points use
    one exact negotiation core;
  - unknown clients and no-common-version requests fail with
    `CONTRACT_VERSION_UNSUPPORTED`;
  - 2.6 without P0-A capability receives the complete 2.5/2.0 projection.
- P0-A-3 production is implemented:
  - `dashboard.company.enter` and `workspace.home.enter` can emit
    `page-block-data.v1`;
  - only `page_block_data.v1` is enabled;
  - attachment and action carriers remain recognized but disabled.
- P0-A-4 evidence:
  - real ORM tag `p0_contract_producer_p0a`: 6 tests PASS;
  - Chromium 1440 and 390: page-block-data rendering, compatibility matrix,
    no console/page errors and no horizontal overflow PASS;
  - real Contract V2 2.6 response: strict decode PASS with 13 Widget
    Descriptors;
  - artifacts:
    `artifacts/p0_contract_producer_01/company-dashboard-1440.png`,
    `artifacts/p0_contract_producer_01/company-dashboard-390.png`,
    `artifacts/p0_contract_producer_01/p0a_browser_acceptance.json`.

## Validation responsibility

| Gate | Owner target | Result |
| --- | --- | --- |
| strict Descriptor, Registry and Page Block data | `verify.p0_contract_producer.p0a.unit` | PASS: 36 Python tests, 9 backend unit tests and both TypeScript suites |
| version negotiation and old projection | focused unit plus browser matrix | PASS: known old, 2.5, 2.6-without-capability, current, no-common-version and unknown-client cases |
| Page Block producer | real ORM tag `p0_contract_producer_p0a` | PASS: 6 non-zero tests |
| owning-module ORM baseline | `make local.test.baseline` | PASS: 6 cases x 3 fresh orders |
| deterministic offline baseline | `make verify.test.baseline` | PASS: 366 cases x 3 independent orders, quarantine 0 |
| frontend lint | `verify.frontend.lint.src` | PASS: 0 errors; 3 existing warnings outside this scope |
| strict typecheck | `verify.frontend.typecheck.strict` | PASS |
| frontend production build | `verify.frontend.build` | PASS |
| Semantic Registry | `verify.semantic.registry.lint` | PASS: 28 semantics, 33 components |
| Page contract guards | orchestration/action/data-source | PASS: 19 pages each |
| Contract V2 architecture guards | action/runtime/status/assembler/web | PASS |
| compatibility and ledger | compatibility unit plus Agent ledger | PASS: 31 compatibility tests, 18 ledger tests |
| frontend decision authority | `verify.frontend.decision_authority.unit` | PASS: 21 tests, unclassified 0 |
| affected incremental execution | `make ci.local.iteration` | PASS: 34 required targets, 0 not-run, 0 failed |
| real runtime and decoder | `make verify.p0_contract_producer.p0a.browser` | PASS at 1440/390; 13 strict Descriptors |

## Contract fidelity regressions covered

- Widget-backed fields use the same strict Descriptor vocabulary as non-Widget
  Page Block facts; compatibility defaults such as `char` and `float` do not leak
  into the strict contract.
- Selection contracts normalize both pair and object declaration forms while
  preserving the original storage keys.
- Page-block-data overlay removes a stale legacy value when the authoritative
  row omits the slot; zero, false, null and missing remain distinct.
- Currency labels resolve only from declared row/context identity. The frontend
  no longer guesses the first available currency.
- Carrier decoding accepts only complete 2.5/2.0 legacy or 2.6/2.1 P0-A
  projections. Attachment and action carriers remain disabled.
- An intermediate real decode exposed compatibility-default `char`/`float`
  Widget tokens and empty Selection declarations. The response was regenerated
  after the owning producer fix; the original failure is retained in
  `artifacts/p0_contract_producer_01/p0a_browser_acceptance_failure.json`.

## Exclusions and rollback

No ACL, Record Rule, workflow, file-service authorization, database schema or
business data change is included. P0-B `attachment_fact.v1` and P0-C
`page-block-action.v1` remain unproduced. Rollback is a protected revert of the
P0-A pull request; no database migration is required.
