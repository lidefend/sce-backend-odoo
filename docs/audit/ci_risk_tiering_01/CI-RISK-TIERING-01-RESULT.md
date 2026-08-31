# CI-RISK-TIERING-01

Status: PASS.

## Migration note

This record captures the pre-split required-check model that existed when this
audit was run. As of August 31, 2026, merge eligibility and publication
eligibility are governed separately:

- `merge_policy_gate` is the only required branch-protection status for
  ordinary merges into `main`.
- `release_candidate_gate` is the explicit exact-head publication
  qualification gate.

Historical mentions of "required checks" in this document should therefore be
read as period-specific evidence, not as the current repository policy.

## Scope

This change is limited to CI classification, required-check orchestration,
content-addressed caches, and deterministic generated-report pre-push refresh.
It does not modify product behavior, importer permissions, release identities,
production data, or production services.

## Baseline

- Sample: 10 recent successful pull-request heads with all required contexts.
- Median required-check wall time: 983.5 seconds.
- P90 required-check wall time: 1030.5 seconds.
- Dominant job: `frontend_release_gate`, 861–1035 seconds.
- Configured dependency cache before this task: none.

## Fail-closed design

- Documentation-only changes use `FAST`.
- Ordinary frontend/backend changes use `STANDARD`.
- Security, ACL, tenant, importer, migration, deployment, release, Docker,
  Odoo configuration, identity, signing, workflow, and lockfile changes use
  `HIGH_RISK`.
- Manual release validation and tag refs use `RELEASE`.
- Empty, malformed, mixed-risk, or unknown change sets use `HIGH_RISK`.
- All fixed required-check names still produce an explicit conclusion in every
  lane; workflow trigger path filters are forbidden.
- `HIGH_RISK` and `RELEASE` retain the full existing professional and frontend
  release commands.

## Local validation

- Risk-classifier positive and negative tests: PASS.
- Required-check workflow contract tests: PASS.
- GitHub Actions security guard: PASS.
- Frontend release CI authority guard: PASS.
- Standard frontend lint/typecheck/unit/build path: PASS.
- Generated-report automatic pre-push refresh self-test: PASS.
- `git diff --check`: PASS.

## Remote cold-cache validation

SHA `bd0e8b20a76d00e3a62ee6e0c2a7eded596bb52a` changed CI workflows and was
therefore correctly classified as `HIGH_RISK`.

- `public_guard`: PASS, 115 seconds workflow wall time.
- `professional_authorization`: PASS, 3 minutes 34 seconds.
- `professional_quality_gate`: PASS, 2 minutes 13 seconds job time.
- `frontend_release_gate`: PASS, 17 minutes 45 seconds.
- pnpm cache: cold miss, then saved by the first completing workflow.
- Playwright cache: cold miss, then saved successfully.
- Required checks with no conclusion: 0.

## Remote warm-cache validation

SHA `73cd5f1a3bae1a2a4a1f44255e5b36968d719404` retained the same high-risk
implementation and validated the warm-cache path.

- pnpm primary cache key: HIT and restored successfully.
- Playwright primary cache key: HIT and restored successfully.
- `public_guard`: PASS, 114 seconds workflow wall time.
- `professional_authorization`: PASS, 3 minutes 34 seconds.
- `professional_quality_gate`: PASS, 2 minutes 10 seconds job time.
- `frontend_release_gate`: PASS, 27 minutes 10 seconds.
- Required checks with no conclusion: 0.

The warm-cache run confirms correctness but also proves that dependency
downloads are not the dominant full-release bottleneck: environment/image
construction and browser acceptance dominate and remain intentionally present
for `HIGH_RISK` and `RELEASE`.

## Merge

- CI implementation PR: `#62`.
- Optimized main SHA: `80d857a8a367e2807007b5c69946a364d856a016`.
- Optimized main tree: `2a94e7370cbcc063f1b653b3458ba03bc2bb30fb`.

## Lane timing validation

FAST validation SHA `e660fc9b220e760eb3c7c012df5acaa493339782`:

- Total required-check wall time: 107 seconds.
- `frontend_release_gate`: PASS, 9 seconds.
- `professional_authorization`: PASS, 7 seconds.
- `professional_quality_gate`: PASS, 9 seconds.
- `public_guard`: PASS, 1 minute 47 seconds.
- Reduction from the 983.5-second baseline median: 89.1%.

STANDARD frontend validation SHA `5b5b823bb03fe6fa22873be2d3b1a1740b3915e6`:

- Total required-check wall time: 109 seconds.
- `frontend_release_gate`: PASS, 37 seconds.
- `professional_authorization`: PASS, 7 seconds.
- `professional_quality_gate`: PASS, 9 seconds.
- `public_guard`: PASS, 1 minute 49 seconds.
- Reduction from the 983.5-second baseline median: 88.9%.

The STANDARD probe file was removed before merge and does not enter `main`.

## Final judgment

```text
CI_RISK_TIERING_01_RESULT=PASS
CI_RISK_CLASSIFIER=PASS
FAST_LANE=PASS
STANDARD_LANE=PASS
HIGH_RISK_LANE=PASS
RELEASE_LANE=PASS
UNKNOWN_PATH_FAIL_SAFE=PASS
STALE_RUN_CANCELLATION=PASS
CACHE_COLD_RUN=PASS
CACHE_WARM_RUN=PASS
SECURITY_CHECKS_REMOVED=0
RELEASE_CHECKS_REMOVED=0
FALSE_SKIP_CASES=0
REQUIRED_CHECKS_PENDING_FOREVER=0
BASELINE_MEDIAN_DURATION_SECONDS=983.5
OPTIMIZED_STANDARD_DURATION_SECONDS=109
STANDARD_MEDIAN_REDUCTION_PERCENT=88.9
OPTIMIZED_FAST_DURATION_SECONDS=107
FAST_MEDIAN_REDUCTION_PERCENT=89.1
PRODUCTION_DATABASE_WRITES=0
PRODUCTION_DEPLOYED=false
RC8_UNCHANGED=true
RC9_CREATED=false
NEXT_TASK=RELEASE-TOOLING-P0-NARROW-IMPORTER-GROUP-03
```
