# Batch-1 Project Profile Delivery Record

[中文](business_entry_surface_normalization_batch_1_20260913.md)

## 1. Changes

- Objective: close the formal entry, real-save, and network-failure recovery chains for project profile maintenance.
- P1: project fields, date range, description, responsibilities, and the separation between profile saving and lifecycle actions.
- P0: localize the shared raw browser `Failed to fetch` error without adding a project-model special case.
- P4: governed local.dev fixture lifecycle, formal-menu journey, one-shot write blocking, separated failure/retry reporting, and authoritative reads.
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
- P4: normal-save and recovery expectations are separate; of two browser write attempts, only the allowed retry reached the backend and succeeded.
- Uncovered: browser denied-role counterexample. Existing backend permission evidence is reused but does not replace this browser gap.

## 4. Verification

- `python3 -m unittest scripts.verify.test_local_dev_project_profile_write_fixture`: PASS, 10 tests.
- Existing repository esbuild execution of `create_record_user_journey_test.ts`: PASS.
- Governed recovery: PASS. The first request was blocked; feedback was visible, busy cleared, draft remained, and backend facts were unchanged. A same-session retry matched the authoritative read and browser refresh.
- Pre-closeout `make ci.local.quick`: all preceding guards passed and the generated-report guard then failed as expected because the new test made the inventory stale. `make refresh.generated_reports` aligned it. The frozen exact-head Quick result is recorded by its governed receipt and independent-review package, not predeclared here.

## 5. Artifacts

- Browser summary: `/tmp/p4-recovery-proof-0913-final/summary.json`.
- Failure screenshot: `/tmp/p4-recovery-proof-0913-final/failure-before-retry.png`.
- Successful refresh screenshot: `/tmp/p4-recovery-proof-0913-final/normal-save.png`.
- Summary SHA-256: `638e8dcabd253dab28366cf40a546f248cd28ef19c7bde1796f25d992ab694d6`.

## 6. Data Disposal and Rollback

- Batch: `recovery-proof-0913`; project 373.
- Cleanup: PASS. The governed entry deleted the project and responsibilities `[21,22]`; `clean=true`.
- Rollback: revert the P4 runner, P0 localization, and P1 entry/page commits at their commit boundaries. No business-database rollback is required.

## 7. Next Step

- Freeze the final HEAD including generated reports and run one exact-head Quick.
- Prepare the independent-review package without automatically pushing, creating a PR, or merging.
- Schedule Batch-2 only after independent review of Batch-1.
