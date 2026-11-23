# REMOTE-CI-PRECISION-20261124

## Identity

- Base: `7a41b86b073e0f062a1ee7f38aa628d375587954`
- Branch: `feature/remote-ci-precision-20261124`
- Formal product layer: P4 verification tooling

## Findings

PR #988 changed only P4 tooling and documentation, but frontend ownership marked
those files as `frontend=true`, causing the complete frontend runtime lane to
run for about three minutes.

PR #985 requested backend `scope_mode=focused`, but the planner returned a full
module plan. This made changed-test selectors ineffective for test-only backend
changes.

## Objective

- Separate frontend runtime changes from frontend tooling changes.
- Skip frontend runtime commands when only tooling changed.
- Preserve standard/full frontend gates for actual frontend runtime changes.
- Use exact changed-test selectors remotely when every impacted module change
  is test-only.
- Retain full impacted module coverage for production backend changes.

No product code, ACL, Record Rule, workflow, database or required gate is
removed.

## Implementation

- Added `frontend_runtime` to the shared path-ownership registry.
- Added `frontend_runtime_changed` to CI risk, Gitee gate plans and professional
  gate outputs.
- Frontend runtime commands now require actual runtime ownership, not tooling.
- Added exact local-iteration Make recipe proof for `make/ci.mk`.
- Backend focused plans now return `scope_mode=focused` and exact selectors only
  for all-test-only module changes.
- Production code, helpers, deleted tests, mixed changes and incomplete
  selectors retain the full impacted-module plan.

## Replays and validation

- PR #988 real change set: `frontend_changed=true`,
  `frontend_runtime_changed=false`, `frontend_mode=skip`,
  reason contains `make_ci_local_iteration_only_exact_git_scope`.
- `verify.ci.workflow.contract`: 487 tests PASS.
- Path ownership: 23 tests PASS.
- Risk classifier: 45 tests PASS.
- Backend suite planner: 58 tests PASS.
- CI workflow contract: 29 tests PASS.
- Gitee gate plan: 18 tests PASS.
- Complete local iteration: PASS, 7.43s.

No product runtime or module baseline was removed.
