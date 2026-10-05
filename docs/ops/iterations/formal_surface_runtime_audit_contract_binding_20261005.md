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

## Delivery lane and CI (2026-10-05, post-commit)

Candidate: branch `fix/formal-surface-runtime-audit-contract-binding-v1`,
integration PR #580 against `main` `51afafd0`.

Guarded-publication findings, each closed at its owning layer before merge:

1. `make pr.push` preflight repelled the first attempt (`ci.generated_reports.guard`,
   stale test inventory) because two new verifier unit tests were added. Fixed by
   `make ci.delivery.freeze.prepare` and committing only the regenerated tracked
   evidence: `test_inventory.csv`, `test_inventory_summary.md` (1460 -> 1462
   assets), `complexity_budget_report.md`.
2. `professional_quality_gate` failed `verify.guard.registry` with
   `orphan script 'test_formal_entry_metadata_audit.py' is not acknowledged in
   registry.yaml`. Fixed by `make guard.registry.seed` (+1 acknowledgement in
   `scripts/verify/registry.yaml`, same acknowledged-orphan policy as the sibling
   audit unit tests), then re-syncing the dependent generated reports
   (`complexity_budget_report.md`, `split_plan_queue.md`).
3. `make ci.local.iteration` then reported the new evidence/registry paths as
   `outside_scope`; the run scope and the `verify.guard.registry` /
   `ci.generated_evidence.preflight` checks were declared in `run.json`.

These are gate-declaration and generated-evidence updates only; no verifier,
fixture, product, ACL or data-repair semantics changed after the audited commit
`dcf41cd0`.

Remaining delivery steps (this PR is integration finalization only, not
deployment or product delivery):

- merge #580 once the four required checks are green on the final head;
- sync the daily runtime to `main` (`make daily.runtime.main.bundle_sync` +
  `daily.runtime.source_revision.align`), upgrading the managed backend only if
  the backend module set actually changed;
- run the declared repair entry `make formal_entry_metadata.non_business_creator.write`
  and the acceptance-fixture entry once on `sc_demo`, then re-run
  `make -k release.daily_dev.acceptance.publish` to show the three gates PASS and
  re-check the list range.

## Closeout (2026-10-06)

This run is closed. The closeout changes only `.agent/` metadata and this
document; no product, verifier, fixture or data semantics change.

### Mainline integration

- PR #580 (verifier contract binding, root causes A/B/C) merged as `b4fc523e`.
- PR #581 (governed provenance-SQL channel) merged (squash) as
  `239af48b62c83f54a79cb2586c662264d95c26c6` on `main`; PR head
  `369f62db985f3745a35dc951e5f22e6589d755c1`, four required checks success.
- PR: https://github.com/lidefend/sce-backend-odoo/pull/581

### Closeout L1 re-verification (this HEAD)

- Offline units re-run at this candidate HEAD and all pass: 5
  (user_formal_field module boundary) + 10 (formal_action runtime drift) + 3
  (formal_entry_metadata audit) + 8 (non-business-creator write) + 21
  (acceptance fixture) = 47.
- `make verify.guard.registry` PASS (`1387 scripts, 88/88 orphans
  acknowledged`).
- `make ci.local.iteration` PASS `change_state=dirty coverage=L1_only` with
  `outside_scope=[]` (log
  `.runtime/agent-runs/FORMAL-SURFACE-RUNTIME-AUDIT-CONTRACT-BINDING/logs/closeout-iteration.log`).
- Risk-selected L2: no runtime or product layer is touched by this docs/.agent
  closeout, so no additional L2/L3/L4 target is required; the merged PRs'
  runtime evidence is unchanged and reused.

### Daily acceptance (authoritative `sc-root` / `sc_demo`)

- Repo `/opt/projects/repos/sce-product-odoo` on branch `main` at `239af48b`
  (clean); `daily.runtime.main.bundle_sync` (`b4fc523e -> 239af48b`) and
  `daily.runtime.source_revision.align`; `/api/runtime-version` serves
  `source_revision = git_sha = 239af48b`, database `sc_demo`, environment `dev`.
  No backend module set or frontend source changed, so no module upgrade or
  frontend rebuild was required.
- `make formal_entry_metadata.non_business_creator.write` repaired
  `sc.settlement.order/source_created_by` from the non-business `admin` login to
  the sanctioned legacy label through the governed `provenance_sql` channel
  (70 rows; before-sample taken prior to the UPDATE; `state` untouched).
  Post-fix readback: `non_business_creator=0`, `raw_non_business_creator=0`,
  `state=ok_visible`.
- `daily.dev.acceptance_fixture.ensure` ensured
  `smart_construction_acceptance_fixture.fe_labor_usage_ticket_a` (方单);
  `daily.dev.acceptance_contract.resolve` rebound
  `artifacts/backend/acceptance_record_identity.json` to the served `239af48b`.
- `make -k release.daily_dev.acceptance.publish` EXIT=0 with:
  `USER_FORMAL_FIELD_MODULE_BOUNDARY_AUDIT failure_count=0`,
  `FORMAL_ACTION_RUNTIME_DRIFT_AUDIT failure_count=0`,
  `FORMAL_ENTRY_METADATA_AUDIT required_failures=[] errors=[]
  contract_required_models=92`, `dev_acceptance_release_probe status=PASS`
  (`login=wutao`, `runtime_identity expected_sha = served_sha = 239af48b`), and
  `[release.daily_dev.acceptance.publish] PASS head=239af48b`
  (log `sc-root:/tmp/daily_composite3.log`).
- Fixed dev password `wutao` / `123456` is confined to the existing isolated
  daily fixture; it does not change the daily login defaults, and the acceptance
  env guard still requires a bound `daily-readonly-credential-confirmation.v1`
  envelope (<=10 min). The fixture-ensure password stays the existing default
  `scdevpass`.

### List range and environment boundaries

- List range is reused, not re-run. Owner accepted the existing nonzero evidence
  `artifacts/frontend-web-fix-20260928/resume-20261001/list.json` -> 108/108 gated
  checks, 5/5 detected negative fixtures each `baseline_ok=true`, zero runtime
  errors; no list/render/CSS/probe input changed in this closeout or the two
  merged PRs.
- The environment DENY is retained as a standalone conclusion for the
  rebuild/snapshot lane only (the two mounters belong to one project and do not
  prove exclusive occupancy; the non-current mounter waits on the existing
  governed entry, the in-use 18082 is preserved, the audit is not relaxed and
  containers are not touched directly). It is not generalised into an
  environment-all-pass. The `rendering_detail_state` exclusion keeps its existing
  evidence and adjudication and is not re-proved here.

### Four-layer status

- Batch acceptance: passed (both owned PRs delivered; local units and
  `verify.guard.registry` pass; exact-head `ci.local.quick` receipt
  `369f62db…`).
- Mainline integration: passed (`main` `239af48b`).
- Version release: not claimed (no version deployed for this run; the daily
  runtime is the persistent dev environment).
- Product delivery: not claimed; requires its own target-environment acceptance.

### Index and freeze order

As in the earlier `ACTIVE-RUN-INDEX-CLOSEOUT` precedent, the index stayed bound
to the closeout branch while the L1 receipts were recorded, and the final commit
retires the binding for the merged `fix/settlement-provenance-entry-creator-v1`
branch instead of leaving a dangling mapping. The frozen HEAD then runs one
`ci.local.quick` (Quick does not depend on the run binding). After freezing,
`make ci.local.iteration` reports `unregistered`, which is the same accepted
behaviour documented by that precedent. The four other pre-existing
`active-runs.json` bindings are untouched by this closeout.
