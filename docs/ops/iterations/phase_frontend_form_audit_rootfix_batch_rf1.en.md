# Runtime Form Editability Audit Root Fix — Batch-RF1

## 1. Changes

- Goal: fix the form auditor's false claim that `wutao` had no edit or save capability in the daily development database.
- Completed:
  - Discover action/menu identities from the current `system.init` navigation instead of pinning database IDs.
  - Read model, domain, context, and ordering from the runtime `ui.contract.v2` action contract.
  - Request real form contracts for candidate records and accept editability only when `statusContract.globalStatus.pageAuth=edit`, retaining trace evidence.
  - Recognize the runtime save labels “保存”, “保存修改”, and “保存草稿”.
  - Replace global `networkidle` readiness with explicit form mode, canvas, and target-state readiness.
  - Add a negative fixture proving discovery succeeds when the default list head contains only locked records.
- Not completed: the 11 visual/state failures found by the full form audit belong to the subsequent P0 frontend batch. This P4 tool fix is not an overall visual candidate.

## 2. Impact

- Formal Product Layer: P4 operations delivery tool.
- Layer Target: runtime form acceptance under `scripts/verify`.
- Module: form auditor, editable-record discovery helper, negative fixture, and acceptance environment guard.
- Standard vs User-Specific: generic verification only; no `sc_demo` model, record, action, menu, state, or user preference is encoded.
- Why Here: the false result came from audit sampling and locator behavior while the product contract already expressed workflow locks and draft editability correctly.
- Why Not Elsewhere: P0/P1/P2 permissions, workflows, APIs, and business data must not be changed to satisfy a faulty auditor.
- Blast Radius: read-only intent calls, browser route discovery, and local acceptance artifacts.
- Startup chain, contract/schema, default route, and public intents: unchanged.

## 3. Root-Cause Evidence

- The runtime role surface for `wutao` includes `business_config_admin`; the general-contract list contract has `pageAuth=edit`.
- Records at the head of the daily list are legacy-confirmed and their form contracts correctly return `pageAuth=read` under workflow policy.
- Runtime discovery finds a draft whose form contract returns `pageAuth=edit`; the real page exposes 30 editable controls and the “保存修改” action.
- Save was not clicked, and no `sc_demo` data, permission, or state was changed.

## 4. Verification

- `make verify.frontend.acceptance.environment.guard`: PASS.
- `node scripts/verify/frontend_form_editability_discovery_test.mjs`: PASS, including the locked-list-head negative fixture.
- Daily real-browser read-only probe: PASS; runtime-discovered editable general contract, 30 editable controls, visible “保存修改”, and zero console errors.
- `pnpm -C frontend gate` through the restricted gate: PASS, including lint, strict typecheck, and production build.
- `make verify.restricted`: FAIL because the isolated acceptance environment's secondary company snapshot failed and only 1/2 profiles succeeded. No database write, company creation, or user creation was used to bypass it.
- Full daily form audit: completed with 110/121 PASS, 11 FAIL, and zero runtime errors. Existing text clipping, sticky-anchor, and loading-state failures remain in the JSON/HTML evidence.
- `git diff --check`: PASS.

## 5. Artifacts

- `.runtime/final-acceptance/wutao-edit-save-root-fix.png`
- `.runtime/final-acceptance/form-audit.json`
- `.runtime/final-acceptance/form-audit.html`
- `artifacts/backend/scene_company_snapshot_collect_report.json`

## 6. Risk and Rollback

- P0: the overall form visual audit still has ten P0 failures, so this batch must not be presented as a professional-product candidate.
- P1: one explicit loading-state assertion still fails.
- P2: discovery samples 40 records under each of three runtime orderings; absence fails closed with inspection evidence and never falls back to a hardcoded record.
- Rollback: revert this batch commit; no database rollback, module upgrade, or data recovery is required.

## 7. Next Batch

- Single goal: close the reported text clipping, sticky-anchor, and loading-state defects in the P0 shared frontend renderer, then rerun the five-viewport form audit.
- Status: the audit-tool root fix is complete; product fixes and the supervisor's final visual decision remain pending.
