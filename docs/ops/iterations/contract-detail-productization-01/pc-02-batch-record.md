# PC-02 Contract Detail Productization — Batch Record

Branch: `feature/contract-detail-productization-01`

Product target: `sc.general.contract` via the released contract-center entry
`menu_sc_p1_daily_contract` / `action_sc_general_contract`.

## Layer declaration

- Formal Product Layer: P1 construction industry standard product
- Layer Target: `smart_construction_core` `view_sc_general_contract_form`
- Module: `smart_construction_core`
- Standard vs User-Specific: standard construction form presentation

## Frozen product mapping

- Identity: `contract_name` (title), `contract_no`, `contract_direction`, `contract_type`, `name`
- Lifecycle: `state` statusbar; `validation_status` independent
- Amount: `amount_untaxed` / `tax_id` / `tax_rate` / `amount_total`,
  `change_amount_total` / `change_rate`, `settlement_amount`
- Fulfillment: income = invoice/received; expense = paid

## Frozen business boundaries (NOT_VERIFIED)

1. change amount aggregation
2. settlement over final amount
3. historical vs new-system payment boundary

## Committed product work

- `6a66074d9` sc.general.contract model/field fact audit
- `80fa254ce` P1/P2 identity + amount band on `view_sc_general_contract_form`
- `4045a7b5c` static quality report
- `38efc931c` native presentation allows `sc.general.contract`

## Runtime acceptance (TASK-03.5)

Frozen candidate `07105ab451d99158a088c9fc609df3d4e1a7997f` on the candidate
profile (`sc-fe-candidate-770` / `sc_frontend_acceptance_candidate`).

- Income `contract` (`fe_general_contract_a`, GC2600001): PASS, 4 viewports, no
  overflow / console error / pageerror / 5xx.
- Expense `general_contract_expense` (`fe_general_contract_b`, GC2600002): PASS,
  4 viewports, no overflow / console error / pageerror / 5xx.

Evidence: `pc-02-general-contract-runtime-acceptance.md`,
`pc-02-general-contract-runtime-evidence.json`, and the per-direction summary and
screenshots under `.runtime/final-acceptance/contract-form-presentation/`.

The earlier income evidence at `142efc0ea` is preserved under
`.runtime/final-acceptance/contract-form-presentation/legacy-142efc0ea/`; the
final frozen candidate re-collected both directions at `07105ab45` because the
browser probe was hardened to assert business surface instead of inline pixel
geometry (a decrease-only vendor-coupling guard), and the new acceptance target
was registered in the verification lane baseline.

Exclusions: no amount compute, ACL, record rule, approval, navigation or business
data changes. No push, merge, or deployment.
