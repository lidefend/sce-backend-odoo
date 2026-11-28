# R2-C archival retirement

Owner authorized 同意归档退役 on 2026-11-28. P4 standard delivery tooling only. No product, database, scan policy, merge or deployment changes. R2-B work preserved in stash before this separate branch. Original PR and failed history remain recoverable.

Local: focused nonzero governance tests. Remote: exact candidate checks pending. Main full qualification: deferred R3, not proved by this operation.

## Executed archival retirement

- PR #1022 CLOSED (unmerged Draft history retained); replacement #1024 merged into exact main `d79dd2caa58f7e2aa7ab17a88fa80df2fc3e266c`.
- Only `fix/verify-system-closeout-01-r2a-20261127` retired, both local and origin refs.
- Original HEAD `7be328ae0fb987fc3a23c91bf49440ee12b71bbc`; original blob `1582beb6a28df0d8f550a87ebff8f24c41b4d70f`.
- Recovery bundle: `.runtime/verify-system-closeout-resume-20261128/pr-1022-recovery.bundle`, SHA-256 `51c9e710978dbbc94b42bf6e4928206ec004613f5861f41322e6907d22e3c0d8`. Keep this bundle; do not include it in public Git history or generic runtime cleanup.
- Recovery proved by fetching the archived ref into an independent bare repository and reading the exact original evidence blob identity.
- 4 close-identity/order tests and 30 existing historical retirement tests passed.
- No scan exceptions, rule changes, force push, merge or deployment. This is not full mainline CI qualification.

## Evidence index

- `.runtime/verify-system-closeout-resume-20261128/retire-1022.json` SHA-256 `6d4190dfca858b0b6300d53361241d7c70ec8272730b479f268f7e84aab614e2`
- `.runtime/verify-system-closeout-resume-20261128/close-1022-dry-run.json` SHA-256 `e64ca2d4fc2e554a0893337b16a17e0e1cfb2f387d9196301a9f7684b3459148`
- `.runtime/verify-system-closeout-resume-20261128/close-1022-applied.json` SHA-256 `6e228e720807b97fe1dcc90a0453cd9d2493b6b534d2c32777e8bc2fd42f35d4`
- `.runtime/verify-system-closeout-resume-20261128/retire-1022-applied.json` SHA-256 `2d280b59e362e19066b54c533fae8b756cdb4380a7bcc1102e22b2d5038a07b1`
- `.runtime/verify-system-closeout-resume-20261128/recovery-proof.json` SHA-256 `763db83feaf6333d8adac621939fcca395716e57589b2e4c8cfbfd36d65fe2ce`

## Remaining verification boundary

The post-retirement `make verify.repository.clean_history` stopped in `security.trusted_scan_group.unit`: `WorkerBudgetTests.test_unknown_memory_keeps_only_the_cpu_bound` expected 2 workers but got 1. Full public-ref scan was not reached; do not claim RH018/global scan PASS. Failure log: `.runtime/verify-system-closeout-resume-20261128/history-after-retirement.log`. Classify and repair separately in CI tooling scope.

The initial local iteration correctly rejected a new unreferenced operator target. The close target is now invoked by `branch.retire.historical CLOSE_SUPERSEDED_PR=1`; its tests and historical retirement tests are selected from their actual sources. Removed the now-stale retirement-test disposition. Coverage check passed without baseline expansion.

Preserved R2-B stash: `d5f038c09b0e497552268678399fa2bd6b2402f4`; apply on its own branch, do not pop or merge indiscriminately.

Final local iteration: PASS, log `.runtime/verify-system-closeout-resume-20261128/r2c-local-wired.log`. Includes nonzero close, retirement, executor and coverage regressions. No remote candidate CI claimed.
