# Difference Attribution

Status: `COMPLETE_FOR_OWNER_REVIEW`

## Classification Rules

An operation is attributed to `MODULE_UPGRADE` only when the table is
technical module/XML-backed state and the record evidence is consistent with
the observed same-version module reload. A business row is never assigned an
actor or cause from database content alone. Those row operations remain
`UNATTRIBUTED`, even when their insert/update/delete operation is known.

## Module Upgrade

- `ir_module_module` retained 677 rows. Module installation state and version
  changed for zero modules; 399 rows changed `write_date`.
- `smart_construction_core` was `installed / 17.0.0.182` before the rebuild and
  after the rebuild. Its `write_date` advanced from
  `2026-11-13 16:03:07.382295` to `2026-11-15 13:11:58.135614`.
- `smart_construction_demo` changed `description` and `write_date`.
- `ir_actions` gained 969 base rows. The current 969 IDs exactly cover the
  union of 744 window, 173 server, 9 client, 40 report, and 3 URL actions with
  zero unmatched IDs. This is an Odoo action-model table reconstruction, not
  969 new product entries.
- `ir_ui_menu` row count remained 720 and no menu identity relation, action,
  parent, sequence, active flag, or translated name changed. Forty-one rows
  changed only `write_date`.
- `ir_act_window` row count remained 744 and only `write_date` changed.
- `ir_act_window_view` retained the same 267 semantic
  `(act_window_id, view_id, view_mode, sequence, multi)` mappings. Its 141
  deleted/inserted IDs are technical primary-key rewrites with zero semantic
  mapping difference.
- `ir_act_server` changed actual activity-deadline fields on 100 actions and
  `write_date` on 101.
- `ir_ui_view` retained 2,110 rows. Seven hundred sixty-eight views changed
  only cache field `arch_prev` plus `write_date`; one base view changed
  `arch_db`: `base.user_groups_view`.
- Access rules, record rules, module metadata, capability/scenario metadata,
  business dictionaries and scene declarations otherwise changed only in
  reload timestamps except where itemized in the schema or record reports.
- `sc_product_scenario` remained 17 rows and
  `sc_product_scenario_entry` remained 78 rows, byte-for-byte unchanged.

## XML Declaration Change

One actual view body changed:

| View | Type | Snapshot SHA256 | Current SHA256 |
| --- | --- | --- | --- |
| `base.user_groups_view` | form | `2f1af0f67df680bebfb695258c5e96d1138323fb97141a9977b7aeaa69898663` | `359be8f469710f73419dc7fee26af1d73771893b2eba11ae634a887cd01d1f7a` |

The view is an Odoo base view, not a capability Registry or business model.

## Business and Identity Data

The conservative `BUSINESS_OR_IDENTITY_DATA_CHANGE` group contains 47 tables:

- 783 inserted rows
- 302 updated rows
- 18 deleted rows

Material examples include:

- `payment_request`: 28 inserted, 29 updated
- `project_cost_ledger`: 28 inserted, 13 updated
- `project_cost_period`: 9 inserted
- `construction_contract`: 14 inserted, 2 updated
- `construction_contract_expense`: 7 inserted
- `construction_contract_income`: 7 inserted
- `construction_contract_line`: 14 inserted
- `sc_receipt_income`: 7 inserted
- `sc_treasury_ledger`: 7 inserted
- `tier_review`: 126 inserted
- `res_users_tier_review_rel`: 532 inserted
- `project_project`: 24 updated

These operations are known from row comparison, but their actor, UI journey,
seed step, migration callback, or operator command is not proven by the
database alone. Source attribution is therefore `UNATTRIBUTED`.

Two deleted XMLIDs referenced demo invoices:

- `smart_construction_demo.sc_demo_invoice_s10_001`
- `smart_construction_demo.sc_demo_invoice_s10_002`

The corresponding two `account_move` rows and four `account_move_line` rows
were deleted. This is recorded as `BUSINESS_DATA_DELETE`; no actor or cause is
inferred.

## Runtime and Audit Data

The runtime/audit group contains 1,157 inserted, zero updated, and 14 deleted
rows. It includes chatter, notifications, followers, user logs and application
audit records. These prove activity after the snapshot; they do not identify
the originating operation.

## Filestore

The pre-rebuild filestore had 1,755 files and 52,733,406 bytes, identical to
the recovery point by relative path, size and SHA256. All 928 stored attachment
records matched their physical SHA1 checksums. No physical attachment was
added, modified or deleted before the owner-authorized rebuild.

## Sequences

Thirty sequence counters advanced while all 670 sequence definitions remained
present. The advances are consistent with inserted module/runtime/business
rows and are classified `SYSTEM_RUNTIME_CHANGE`.
