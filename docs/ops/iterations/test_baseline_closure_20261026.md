# Test baseline closure — 2026-10-26

P4 owns test execution, reproducibility and evidence. Baseline starts at b88abfe8f521791ea51f52d8ff4da0236d3a667e on codex/test-baseline-closure. One writer, existing worktree; no product semantics, persistent development/acceptance/production writes or new credential authority.

## Acceptance obligations

- Exact test profile identity before every write; fixed existing sc-local-test/sc_test, independent sc_local_test_* volumes, exact filter. Synthetic test data only, not a customer/control/catalog database.
- Fresh database and transient application state for each local ORM attempt; nonzero selected module-qualified executions and clean final result are mandatory. Failed attempts retained; no retry-to-green.
- Reproducibility must name its full declared case set, compare collected identities and outcomes across independent runs/orderings and fail missing/duplicate/zero/changed outcomes. A probe over a few governance tests is not repository-wide proof.
- Quarantine is explicit exact test identity, evidence, owner and expiry, with separate execution/reporting; it never silently converts failure into a pass.
- Reuse without authenticated complete inputs is RUN, never inferred complete from partial static scans. Baseline correctness does not require an unsafe reuse ratio.
- Freeze only after actual runtime and focused checks converge; exact-head Quick, independent review, external evidence, current remote CI, protected PR merge and main sync.

## Initial findings

Existing local.test starts services before validating MODULE; env-file and Make override injection can select foreign profiles. test.safe neither triggers module install/update nor guards nonzero executed tests. Fixed sc_test persists across attempts. These are P4 execution defects; correct before any runtime launch. Existing local.test env is already registered; do not print credentials or generate a second authority.

Current status: active, no baseline completion claim.

## Implementation and observed evidence

- P4 local.test now validates exact identity before writes, ignores foreign Make/environment overrides, serializes the fixed test database, resets only sc_test, and uses transient Odoo state. Shared ORM guard proves nonzero requested-module execution. Precise carrier cleanup and failure logs/receipts are mandatory. Original lifecycle plus new counterexamples passed (47 tests).
- First real two-tag run executed 6 tests; same-stage three-order run executed all 6 in each fresh database with verified method ordering and unchanged source. Original receipts: `.runtime/test-baseline/1792957048513459474/receipt.json`, `1792957071692411671/receipt.json`, `1792957091339905252/receipt.json`. These are iteration evidence; final candidate receipts must be collected after freeze.
- Actual zero-match Odoo invocation exited with no tests; shared result guard rejected it and wrote a failed receipt (`1792957180301743585`), proving exit0 cannot pass. No retry-to-green.
- Offline declared mechanisms passed three independent orders (254 cases before adding finalizer self-tests). Parent/children now bind source fingerprints; no old passed receipt survives either ordinary failure or preflight/manifest failure in ORM mode. Final manifest includes the finalizer self-tests too.
- Both ORM tag groups are now explicitly selected in remote backend_test_suite for smart_core; their stale unwired entries were removed. No unrelated group was marked covered.
- Static known-input closure was renamed separately; dynamic dependency completeness remains false. Ordinary ORM result reuse is deliberately unavailable, so missing authority cannot suppress execution.
- Independent review found timeout cleanup, source-binding and stale-receipt defects during iteration; all were corrected with negative tests before freeze. Runtime order proof is class-local, not a claim of module-order independence.
- Guard registry and coverage ledger passed after exact metadata repairs. Lane coverage found the new order driver reference and now-reachable local.test.test stale disposition; fixed real path wiring and removed only that stale disposition, without loosening the baseline.

Remaining finalization: focused audits, generated evidence, one frozen candidate, current-source three-order ORM and Quick/offline receipts, baseline.ready, independent review, archive, required CI, protected squash merge and main sync. No deployment or all-legacy-test-coverage claim.
