# Batch-1 Project Profile Delivery Record

[中文](business_entry_surface_normalization_batch_1_20260913.md)

## 1. Changes

- Objective: close the formal entry, real-save, and network-failure recovery chains for project profile maintenance.
- P1: project fields, date range, description, responsibilities, and the separation between profile saving and lifecycle actions.
- P0: localize the shared raw browser `Failed to fetch` error without adding a project-model special case.
- P4: governed local.dev fixture lifecycle, formal-menu journey, one-shot write blocking, separated failure/retry reporting, actual-control snapshots, and authoritative project/responsibility reads.
- Incomplete: the browser denied-role counterexample remains uncovered because no registered credential is usable; Batch-2 has not started.

## 2. Impact Scope

- Modules: `smart_construction_core`, the shared contract-form frontend, `scripts/verify`, and `make/dev.mk`.
- Bootstrap: restores the runtime projection of an already-authorized project-manager menu; authentication and company context are unchanged.
- Contract/schema: no schema addition or bypass; the flow consumes `ui.contract.v2` and `api.data op=write`.
- Route: the formal entry uses `menu 681/action 861`; a hand-built route is not treated as authorization evidence.
- Data: only a governed dedicated batch in `sc-local-dev/sc_dev_demo`; projects 2 and 8 were not modified.

## 3. Risks and Boundaries

- P0: network-error wording is shared frontend behavior and a targeted test prevents raw browser text from leaking.
- P1: profile saving does not advance lifecycle; the authoritative result remained `draft`.
- P4: normal-save and recovery expectations are separate. Recovery PASS requires equal actual-control values and detail operations before/after failure, unchanged project and responsibility contents, and a truly visible error element. Of two browser write attempts, only the allowed retry reached the backend and succeeded.
- Uncovered: browser denied-role counterexample. Existing backend permission evidence is reused but does not replace this browser gap.

## 4. Verification

- `python3 -m unittest scripts.verify.test_local_dev_project_profile_write_fixture`: PASS, 13 tests.
- Existing repository esbuild execution of `create_record_user_journey_test.ts`: PASS.
- Governed recovery: PASS. The first request was blocked and the visible error-summary element has a locator-bound screenshot. Name, both dates, description, and responsibility control snapshots matched before/after failure, including create/update/delete detail operations. All involved project fields and responsibility role/user/note facts matched initialization. The same-session retry returned business success and the complete authoritative read matched refresh.
- Pre-closeout `make ci.local.quick`: all preceding guards passed and the generated-report guard then failed as expected because the new test made the inventory stale. `make refresh.generated_reports` aligned it. The frozen exact-head Quick result is recorded by its governed receipt and independent-review package, not predeclared here.

## 5. Artifacts

- Browser summary: `/tmp/p4-recovery-evidence-0913/summary.json`.
- Visible error-element screenshot: `/tmp/p4-recovery-evidence-0913/failure-feedback-visible.png`.
- Full-page failure screenshot: `/tmp/p4-recovery-evidence-0913/failure-before-retry.png`.
- Successful refresh screenshot: `/tmp/p4-recovery-evidence-0913/recovery-after-refresh.png`.
- Summary SHA-256: `e27df862a76c680f5be2b1016b6ba0ed2888fb4889520bd1760556cd4e91a0ce`.

## 6. Data Disposal and Rollback

- Batch: `recovery-evidence-0913`; project 374.
- Cleanup: PASS. The governed entry deleted the project and responsibilities `[24,25]`; `clean=true`; a subsequent inspect confirmed that the batch no longer exists.
- Rollback: revert the P4 runner, P0 localization, and P1 entry/page commits at their commit boundaries. No business-database rollback is required.

## 7. Next Step

- Batch-1 is archived. PR #465 ended at
  `73842d9248867599a54f9ce4647381b2ab59ea28`; after the initial delivery
  candidate it added three review corrections: shared-field/P4 runner closure,
  component-takeover inventory refresh, and separation of login-role and
  business-role detection.
- `frontend_release_gate`, `merge_policy_gate`, `professional_quality_gate`,
  `public_guard`, and `release_candidate_gate` all succeeded on the final PR
  HEAD. GitHub records no human review; independent code review and CI evidence
  must not be represented as a GitHub human approval.
- The squash merge is
  `dbf1e171281bd920c39099be7085718c892b10f4`. The final PR HEAD and merge commit
  both have tree `2f52649c86587c94e9dfbc1e318538eca41741e2`, proving product-content identity.
- Batch-2 proceeds separately; the Batch-1 browser save chain is not rerun.
