# CI-RISK-TIERING-01

Status: implementation validation in progress.

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

Remote cold/warm cache timings and lane reduction measurements will be taken
from SHA-bound GitHub Actions runs before final acceptance.
