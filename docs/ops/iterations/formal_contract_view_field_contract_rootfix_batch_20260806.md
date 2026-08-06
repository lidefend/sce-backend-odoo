# Formal Contract View Field Contract Root Fix — Batch-FA-RD-RF2

## 1. Root cause and change

- The construction-contract formal tree introduced `legacy_document_no` and
  `legacy_contract_no` after those legacy aliases had been deliberately removed
  from the P1 product field contract.
- Odoo therefore rejected the view while upgrading `smart_construction_core`.
  The same tree also sorted on `legacy_acceptance_sort_id`, which is not part of
  `construction.contract.income`.
- Architecture 2.0 has one formal identifier for this model: `name` (platform
  document number). The tree now exposes that field once as `单据编号`; it does
  not duplicate the value under a second `合同编号` label. Ordering now uses
  `date_contract desc, id desc`.
- The module version advances from `17.0.0.78` to `17.0.0.80` so governed
  daily upgrade replays the corrected XML.

## 2. Architecture boundary

- Formal Product Layer: P1 construction industry standard product.
- Layer Target / Module: native formal list view contract in
  `smart_construction_core`.
- Standard vs User-Specific: construction product standard; no customer ID,
  database ID, runtime configuration, permission, or frontend special case.
- Why Here: the module owns installable view and field references for both fresh
  tenants and repeatable upgrades.
- Why Not Elsewhere: reintroducing legacy aliases would violate the formal field
  architecture; a frontend label substitution or database patch would leave the
  native Odoo view invalid.
- Blast Radius: the construction-contract formal list and its runtime drift
  audit only. No API, ACL, workflow, public route, or business-record mutation.

## 3. Validation and rollback

- Source regression:
  `python3 -m unittest scripts.verify.test_formal_action_runtime_drift_audit`.
- Architecture guards:
  `make verify.formal_product_field_purity architecture.module_dependency_map`.
- Runtime proof: governed module upgrade on the paired-backup-protected daily
  `sc_demo`, followed by `make verify.user_confirmed.formal_surface.locked`.
- The stale post-install feedback test is updated to assert the single-number
  contract and absence of the removed aliases. A source-level regression is
  part of the always-run formal-action unit gate because the default smoke gate
  does not execute the full `user_feedback` post-install class.
- Rollback: restore the verified paired database/filestore backup, then sync the
  daily runtime repository to its preceding exact SHA. Do not attempt an Odoo
  module-version downgrade. No data migration is introduced by this batch.

## 4. Environment and loader-chain audit

- Daily source before RF2: manifest `17.0.0.78` at exact runtime-repository SHA
  `a514e0ca406d948006dbed26aa204c762777db19`.
- Daily `sc_demo` after the rejected upgrade reported module state `installed`,
  `installed_version=17.0.0.78`, and stale `latest_version=17.0.0.77`. The
  installed formal tree remained the pre-upgrade 18-field version. This proves
  a module-metadata/view split after the failed registry load; it does not prove
  an unsynchronized server checkout.
- `models/__init__.py` imports `support`; `support/__init__.py` imports
  `contract_center`, `contract_professional`, and `contract_business`.
  `construction.contract.income` is registered by `contract_professional` with
  `_inherits = {"construction.contract": "contract_id"}` and
  `_inherit = "construction.contract.professional.mixin"`. Daily runtime and
  `ir.model.fields` both exposed the same 140 fields, including `contract_id`
  and all non-legacy fields used by the corrected tree. The loader chain is not
  missing an extension.
- The complete pre-fix source tree comparison found exactly three invalid
  references: fields `legacy_document_no`, `legacy_contract_no`, and sort field
  `legacy_acceptance_sort_id`. Every other visible field exists in both the
  runtime registry and daily `ir.model.fields`.
- Architecture split commit `d269abbd5adcdc7a4c6f0425c08c68106bf6c946`
  deliberately removed product legacy aliases and introduced the `17.0.0.76`
  cleanup migration. Commit `2a6759fa3d0019dfd6a6461e1e371eceb445e0a8`
  later reintroduced those names only in the formal view/audit expectation,
  without a model extension or migration. The defect is therefore a post-split
  view-contract regression, not an omitted import or daily source sync.

## 5. Runtime evidence

- The rejected daily upgrade produced a deterministic Odoo `ParseError` at the
  formal income-contract tree. The installed view stayed unchanged.
- A post-failure governed continuity baseline performed zero writes and matched
  the protected baseline: 12,671 construction contracts, 609,258 attachments,
  34,897 payment requests, 923 projects, 500 filestore files and 10,732,629
  bytes. This confirms business-data and filestore continuity after rollback.
- Fresh install on isolated database `sc_test_formal_contract_rf2` loaded all 69
  modules and the corrected formal view. The corrected post-install feedback
  test passed with `0 failed, 0 error(s)`.
- A second governed `make mod.upgrade` against the same isolated database loaded
  `smart_construction_core` and the formal view again and exited zero, proving
  the repeat upgrade path rather than element-presence only.

## 6. Post-deploy formal-action root extension

- The first daily runtime audit proved the contract tree itself clean, then
  exposed three material actions with zero rows. Their target records were not
  missing: daily runtime contained 13,184 inbound, 166 rental-in, and 37
  rental-return projections.
- The actions encoded the invented source identity
  `online_old_legacy_direct:direct_acceptance_fact`, while the actual lineage
  is customer-specific. Encoding the observed customer identity in P1 would
  repeat the boundary violation.
- The three actions now filter by the P1-owned semantic projection field
  `legacy_acceptance_label`. The runtime gate compares each action domain and
  count with the generic label projection, without importing an archived
  customer carrier model or requiring fixture rows.

## 7. Full-surface label closure

- The post-upgrade full formal-surface gate found the engineering-progress
  income tree labeling `legacy_contract_no` as generic `合同编号`, while this
  relationship denotes the construction-management contract for the receipt.
- The tree now uses `施工管理合同`, matching the locked runtime contract. The
  source regression asserts both the required semantic label and absence of
  the generic label. The module advances to `17.0.0.81` for XML replay.
