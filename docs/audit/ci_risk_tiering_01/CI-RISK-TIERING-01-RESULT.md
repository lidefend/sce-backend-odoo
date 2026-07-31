# CI-RISK-TIERING-01

Status: remote warm-cache and lane timing validation in progress.

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

The next SHA-bound run validates warm-cache restoration without changing the
CI implementation.
