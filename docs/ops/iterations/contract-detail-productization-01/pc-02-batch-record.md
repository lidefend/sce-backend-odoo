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

Status and evidence are recorded here as the run proceeds. Income evidence was
first produced at `142efc0ea`; the final frozen candidate binds both directions to
one exact HEAD after the P4 output-path separation and expense target are committed.

Exclusions: no amount compute, ACL, record rule, approval, navigation or business
data changes. No push, merge, or deployment.
