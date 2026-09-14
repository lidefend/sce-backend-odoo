# Draft PR: Normalize Income and Expense Contract Settlement Handling Pages

Chinese: [contract_settlement_handling_page_normalization_pr_draft_20260914.md](contract_settlement_handling_page_normalization_pr_draft_20260914.md)

## Summary

This PR makes the formal income- and expense-settlement entries present project/counterparty, settlement basis, lines and amounts, and handling notes through their authoritative business sections. Parent-dependent columns and repeated relation occurrences now consume the existing contract semantics consistently.

It does not change settlement calculations, amounts, save, approval, permissions, historical snapshots, or business data, and introduces no settlement special case, new contract carrier, upload capability, or fixture.

## User-visible improvements

- Income uses “Project and Client”; expense uses “Project and Supplier/Subcontractor”, without crossing category defaults.
- Settlement lines and amounts remain one region; name, quantity, unit price, and amount precede source contracts.
- Standard-contract and general-contract columns react to the current parent type, including unsaved parent-value changes.
- Handling Notes contains the existing description, note, and attachment field; execution/trace sections remain collapsed and accessible.
- Navigation targets the actually visible occurrence while preserving the same field when it belongs to distinct valid business regions.

## Architecture Impact

- Formal Product Layer: P1 industry-standard settlement declarations; P0 generic contract propagation and shared-renderer consumption; P4 validation and delivery evidence.
- Standard vs user-specific: all product declarations are construction-standard behavior; no P2 customer preference or P3 runtime configuration is introduced.
- P0 accepts a container only when its explicit anchor, explicit structure group, and single descendant identity agree; it does not infer from model names, field names, or presentation modes.
- The frontend reuses the existing modifier evaluator and public renderer API and scopes relation occurrence selection by business region, with no settlement-model branch.
- Blast radius: the shared settlement view, native forms consuming explicit structure groups, parent-dependent one2many columns, and relation navigation. An income-contract counterexample and non-zero generic tests prove containment.

## Layer Target

- P1: `smart_construction_core` settlement form policy, native form view, and focused profile tests.
- P0 backend: explicit container-role propagation in the `smart_core` unified page contract V2 assembler.
- P0 frontend: dynamic one2many visible columns and native-section relation occurrence selection.
- P4: bilingual iteration report/PR draft, generated evidence, and exact-head gates.

## Affected Modules

- `smart_construction_core`
- `smart_core`
- `frontend/apps/web`
- `docs/ops/iterations`

## Verification

- `make ci.local.iteration`: PASS, 16 tests.
- Native-section navigation, collection semantics, and strict type checking: PASS, including parent false/true/value-change, same-region, identical-field-semantics across explicit business anchors, distinct unanchored semantic child regions, all-hidden, and collapsed counterexamples; root traversal cannot receive extra `forEach` arguments.
- `TestPaymentSettlementComponentProfile`: PASS, nine tests; focused P0 contract tests also passed with non-zero coverage.
- Governed `local.dev` incremental upgrade and health: PASS.
- The a99 income/expense light, mobile, and focus samples completed human product review, but lack runtime before/after full-fingerprint binding and are retained only as human-review/diagnostic material.
- Final product source `e0d844cd…` has bound expense dark create/read-only runs at 1088×791 and 390×844: create has five targets per viewport; read-only has 11 desktop and 12 mobile targets, all unique and stably below sticky surfaces. Before/after fingerprints match, summary/screenshot hashes are bound, and writes/errors are zero.
- Freeze preparation, the single Quick run, and independent review are recorded by off-repository receipts for the final clean HEAD; this draft will not mutate the candidate to backfill a SHA.

## Evidence

- Iteration report: `docs/ops/iterations/contract_settlement_handling_page_normalization_20260914.en.md`
- Final-product-source expense create dark: `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-settlement-final-e0d844cd-create-dark/evidence-binding.json`
- Final-product-source expense read-only navigation: `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-settlement-final-e0d844cd-navigation/evidence-binding.json`
- a99 light, income click-position, and focus summaries are human-review/diagnostic material only, not the final L4 gate.

## Not included

- Expense draft edit, real save, approval, all-role, historical-snapshot, or amount-calculation acceptance.
- Primary-amount semantics, empty-period repair, formal attachment-authorization expansion, or business-data correction.
- Contract changes, payment, invoicing, the general workbench, low-code, deployment, release, or database operations.

## Risk and rollback

- Shared risk is constrained by explicit unambiguous identity and existing modifier semantics; ambiguity fails closed.
- Roll back P0 navigation/dynamic columns, then P0 assembler propagation, then P1 view/policy. No data rollback is required.

## Delivery status

`READY_FOR_REMOTE_DELIVERY_DECISION_AFTER_EXACT_HEAD_GATES`. Remote push, PR creation, Ready, merge, deployment, and release each require authorization; stop on HEAD drift, conflict, or a new blocker.
