# Formal surface runtime-audit contract binding (2026-10-05)

Run: `FORMAL-SURFACE-RUNTIME-AUDIT-CONTRACT-BINDING`
Branch: `fix/formal-surface-runtime-audit-contract-binding-v1`
Baseline: `main` `51afafd0fd7f41dd0d87a53d8a4eb4a105feae94` (after PR #579)

## Problem

The daily composite acceptance (`make -k release.daily_dev.acceptance.publish`)
passed its user-facing probes but still failed three runtime gates inside
`verify.user_confirmed.formal_surface.locked`:

1. `verify.user_formal_field.module_boundary.audit`
2. `verify.formal_action.runtime_drift.audit`
3. `verify.formal_entry_metadata.audit`

Each failure was reproduced on the authoritative daily runtime (`sc-root`,
`sc-backend-odoo-dev` / `sc_demo`) with the pre-fix script piped through the
governed Odoo shell, and re-measured with the fixed script on the same
environment.

## Root causes and owning-layer fixes

### A. Boundary audit used bare substring field matching

`user_formal_field_module_boundary_audit` decided a boundary field was present
with `field_name in blob`, so the generic contract name `name` matched the
external read-only customer module's own manifest key
`"name": "Smart Construction Custom Compatibility"`. This produced
`{'type': 'custom_business_field_leak', 'case': '报价单', 'field': 'name', 'path': 'smart_construction_custom/__manifest__.py'}`.

Fix (verifier only): presence is now proven by a real Python field declaration
(`^\s*<field>\s*=\s*fields\.`) or an XML view field reference
(`<field name="...">`), never a bare substring. The dead `core_blob` /
`core_static` branches were removed. Nothing was relaxed and the external
customer repository was not touched.

Evidence: pre-fix FAIL (1 failure, the manifest key) -> post-fix PASS
(`failure_count: 0`, `source_roots.custom=/mnt/customer-addons`).

### B. Locked action contract was stale against its own source view

`formal_action_runtime_drift_audit.EXPECTED_ACTION_CONTRACTS` still declared the
old `支付申请` name and the pre-PR-#392 tree fields for
`action_payment_request_user_payment_apply`, and pointed a key at the dead
xmlid `action_sc_payment_deposit_return`.

Fix (contract binding): the entry now matches the installed source view
(`付款申请`, field order `state, name, date_request, project_name_display,
payee_unit_display, payment_basis_type, payee_account_completeness,
legal_next_action_display, request_amount_display, ...`), and the dead key was
rebound to the real `action_tender_guarantee_formal_payment_deposit_return`.
Tests now bind every locked contract entry to repository source so the contract
cannot silently drift again.

Evidence: pre-fix FAIL (3 failures: `wrong_name`, `wrong_tree_fields`,
`empty_high_risk_formal_action_domain`) -> post-fix FAIL (1 failure, the 方单
data gap below). `wrong_name` and `wrong_tree_fields` are gone.

### C. Entry-metadata audit swept every user model instead of its contract

`formal_entry_metadata_audit.DEFAULT_REQUIRED_MODELS` was `("__all__",)`, so it
demanded entry metadata from all 125 user models. Only 24 of the resulting
failures were on models the declared contract (`FORMAL_ENTRY_METADATA_MODELS`,
92 models) ever claimed.

Fix (declaration consumption): the audit now consumes
`FORMAL_ENTRY_METADATA_MODELS`; `__all__` stays available as an explicit
`FORMAL_ENTRY_METADATA_REQUIRED_MODELS` override for diagnostics. A test locks
both the consumption (the binding must be that Name) and the declaration (92
models, frozen digest) so it cannot silently shrink.

Evidence: pre-fix FAIL (25 `required_failures` = 24 `metadata_pair_not_visible`
+ 1 `non_business_creator_nonzero`) -> post-fix FAIL (1 `required_failure`: the
`sc.settlement.order` data gap below).

## Residual failures were genuinely data, repaired through governed entries

### 1. `sc.settlement.order` legacy `source_created_by='admin'`

70 active records carry `source_created_by='admin'`. They are legacy-migrated
(`source_created_at` 2022/2024), and both `entry_user_id` and `create_uid` are
the migration operator (`OdooBot`), so the original business entry user is not
recoverable from the record. The generic `source_created_by` Char is added to
every declared formal-entry model by
`smart_construction_core/models/support/formal_entry_metadata_extensions.py`.

Repair: the declared P4 entry
`make formal_entry_metadata.non_business_creator.write` was extended to a
`(model, creator field, resolver)` registry and now also covers
`sc.settlement.order` / `source_created_by`, resolving to the same sanctioned
legacy label (`旧系统管理员`) already used for `sc.receipt.income`. No manual
SQL, no hand-assembled credentials.

### 2. Empty 方单 formal menu

`action_sc_labor_usage_ticket` (方单) filters `sc.labor.usage` by
`usage_type='ticket'`; the daily dataset has 9046 `sc.labor.usage` rows, all
`casual` (零星用工) and none `ticket`. The domain is correct product behaviour;
the acceptance dataset simply never populated 方单. The assertion was not
relaxed.

Repair: the declared acceptance-fixture builder
(`smart_construction_acceptance_fixture.tools.frontend_productization_fixture`)
now creates one deterministic, idempotent `FE-LABOR-TICKET-A` 方单 row for
project A, and the daily fixture entry declares its xmlid in `REQUIRED_XMLIDS`.

## Scope and boundaries

- Formal Product Layer: P4 ops delivery tool (verifiers, repair entry, fixture).
- No P0/P1/P2 product semantics changed; no ACL, field-permission or domain rule
  was overridden; no product-model special case was added.
- The three example affected commands that reported zero tests, or that were run
  against an unregistered profile, are not treated as gates.

## Verification

- Local unit: 5 (boundary) + 10 (drift) + 3 (entry-metadata) + 6
  (non-business-creator) pass; `make ci.local.iteration` L1 entry.
- Local runtime (sc-local-dev / sc_dev_demo): boundary audit PASS; drift audit
  only the local 方单 data gap; entry-metadata audit bound to 92 contract models.
- Authoritative daily (`sc_demo`), pre-fix vs post-fix readback, and the repair
  + fixture runs, are recorded in the run's evidence index.
