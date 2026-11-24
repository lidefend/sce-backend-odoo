# REMOTE-CI-PRECISION-20261124

## Identity

- Initial base: `7a41b86b073e0f062a1ee7f38aa628d375587954`
- Current base after mainline sync: `49eaed0281f733d08e1f891324fa0d08cf03fa33`
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
- Test-only execution is narrowed to the modules that own directly changed
  test files. Dependency consumers are not rerun when only tests changed.
- Focused pure-Python backend modules now run only their exact changed
  `tests/test*.py` files through the existing structured-result runner. They no
  longer discover every test in the module.
- Per-module selector and file lookups consume the frozen plan digest directly.
  The measured lookup fell from tens of seconds of repeated Git impact analysis
  to about `0.07s`.
- Production code, helpers, deleted tests, mixed changes and incomplete
  selectors retain the full impacted-module plan.

## Replays and validation

- PR #988 real change set: `frontend_changed=true`,
  `frontend_runtime_changed=false`, `frontend_mode=skip`,
  reason contains `make_ci_local_iteration_only_exact_git_scope`.
- `verify.ci.workflow.contract`: 497 tests PASS.
- `verify.ci.scheduled_gates`: 105 tests PASS.
- Path ownership: 23 tests PASS.
- Risk classifier: 45 tests PASS.
- Backend suite planner: 64 tests PASS.
- Backend dispatch workflow contract: 29 tests PASS.
- Gitee gate plan: 18 tests PASS.
- Frontend incremental planner and lane routing: 237 tests PASS.
- Generated report guard: PASS after regenerating the content-bound complexity report.

No product runtime or module baseline was removed.

Historical exact-diff replays:

- PR #988-style P4 tooling: frontend mode `skip`, runtime changed `false`.
- `26ec4bac` smart_core pure-Python test change: focused `smart_core` only,
  exact file selected, with no Odoo-module execution.
- `78c64123` smart_construction_core ORM test change: focused module only,
  40 exact method selectors.
- `eeb282c8` mixed ORM plus pure-Python test change: one ORM selector and one
  exact pure-Python file, without duplicating the pure file in both lanes.

## Full-path audit

| Changed path | Remote execution |
| --- | --- |
| frontend runtime source | standard/full frontend lane |
| frontend tooling or documentation | tool checks; frontend runtime skipped |
| `make/ci.mk` local iteration recipes only | exact Git-tree proof; frontend runtime skipped |
| unrelated `make/ci.mk` change | full frontend lane retained |
| backend production source | full impacted modules |
| backend ORM test-only source | owning module and exact changed ORM selectors |
| backend pure-Python test-only source | owning module and exact changed files |
| unaffected dependency consumers of test-only changes | not executed |
| helper, deleted test or mixed production/test change | full impacted modules |
| unknown path | fail closed |

The focused-file lookup consumes the frozen plan and its digest. A missing
exact Python file selection fails the module instead of falling back to whole
directory discovery. The same frozen-plan path is shared by ORM selectors,
ORM files and pure-Python files, so each module lookup does not rebuild or
reinterpret the Git impact plan.

## Validation-lane boundary

| Lane | Identity and purpose | Grants | Does not grant |
| --- | --- | --- | --- |
| local targeted | current HEAD plus explicit dirty scope; affected static/contract/non-zero tests | local diff confidence | PR integration, all-module baseline, release |
| ordinary PR integration | exact PR HEAD against current target base; risk-selected checks | merge gate when all current required checks pass | scheduled release qualification |
| explicit full candidate | `ci:candidate` or owner `workflow_dispatch`; full candidate checks | exact candidate-build eligibility | ordinary PR substitution or scheduled mainline result |
| scheduled release | one `18:00 UTC` slot on exact main head/tree | `candidate_build_eligible`, with `deployment_ready=false` | PR merge acceptance or deployment authorization |

The scheduled lane covers five exact workflows: `public_guard`,
`professional_quality_gate`, `frontend_release_gate`, `merge_policy_gate` and
`release_candidate_gate`. The professional workflow nests
`backend_test_suite` with `scope_mode=full`; backend tests enumerate every
runnable module without a PR base. `release_candidate_gate` only aggregates
the four producer workflows from the same exact head and scheduled slot.

Local planner routing was also corrected: changes to those five workflows,
`release_condition.py`, `scheduled_validation.py`, authoritative-run selection
and their owning tests now select `verify.ci.scheduled_gates` in addition to
the general CI contract where applicable.

Final local iteration executed 8 affected targets, including both CI contract
owners and frontend incremental routing. Raw output:
`.runtime/remote-ci-precision-20261124/final-iteration.log`.
