# Verification correctness and escaped dependency closure

## Identity

- Baseline: `main@032990188abea05a5d2ab81313136c431e5f89b3`
- Candidate branch: `fix/verify-correctness-escape-01-20261125`
- Layer: P4 verification and CI control plane
- Environment: offline; no database, deployment or remote mutation

## Objective

Deliver `VERIFY-CORRECTNESS-01` and `VERIFY-ESCAPE-02` as one independently
reviewable P4 result. The first batch makes diagnostic collection additive,
aligns shared-contract reuse with ordinary receipt reuse, and prevents a
zero-test target from passing. The second batch closes the dependencies exposed
by #996, #997 and #998 and moves cheap registry/plan checks ahead of ORM work.

## Result index

| Area | Required proof | Actual result |
| --- | --- | --- |
| Frontend incremental executor | `make verify.frontend.dev.incremental.unit` | PASS, 250 tests |
| CI workflow and planners | `make verify.ci.workflow.contract` | PASS, 520 tests |
| Test coverage registry | `make verify.test.coverage.registry` | PASS, 20 tests |
| Merge/branch governance | `make verify.branch.governance.consistency` | PASS, 90 tests |
| Native parser | `make verify.native_advisory.unit` | PASS, 69 tests |
| Contract consumer | `make verify.unified_page_contract.v2.runtime` | PASS, 179 tests |
| Local affected iteration | `make ci.local.iteration` | PASS after selector repair; full pass executed 12 required targets, final bookkeeping rerun executed 3 and reused 5 |
| Freeze preparation | `make ci.delivery.freeze.prepare` | PASS after installing the locked frontend workspace |
| Remote PR integration | Four exact-head required checks | pending, not run in this local-only batch |

## Change inputs

- Shared contract receipt validity must use the same dependency invalidation
  path as ordinary resume.
- `frontend_contract_diagnostic_required` is an additional duty, not a mode that
  replaces `standard` or `full`.
- Test targets need observed non-zero test execution; static guards do not
  invent a test count.
- #996 added `workflow_contract_platform`; the registry audit must own the
  declaration and the class must retain a real execution entry.
- #997 added a merge-entry branch read; the merge fake must model it and the
  branch-governance suite must be selected for `make/codex.mk`.
- #998 made `open_form` additive; the standalone parser and contract consumer
  tests must be selected from the parser source.

## Implemented controls

- `resumable_receipt_results()` now removes targets selected by paths changed
  after the source receipt. Shared-contract handoff and ordinary resume consume
  this one predicate; source ancestry, runtime tree, verifier authority,
  environment identity, complete target set and log hashes remain mandatory.
- `frontend_contract_diagnostic_required` no longer changes `frontend_mode`.
  A mixed change keeps `standard` (or `full` when selected) and runs the
  diagnostic as an additional duty. Backend-only contract-producer changes may
  keep `frontend_mode=skip` while still running the isolated diagnostic.
- Test targets record `executionKind`, observed test counts and execution
  evidence. `Ran 0 tests` or a test target with no observable test evidence is
  failed even when Make exits zero. Static guards remain static and do not
  fabricate a test count.
- Test declarations/import lists and selector inputs select
  `verify.test.coverage.registry`. `workflow_contract_platform` is dispositioned
  to its real `smart_core` class target.
- `make/codex.mk` and the branch-governance files select
  `verify.branch.governance.consistency`; the merge fake now models the live
  branch, remote, PR and tree reads used by the current preflight.
- Parser source selects `verify.native_advisory.unit` and
  `verify.unified_page_contract.v2.runtime`. The affected parser and consumer
  assertions now cover preserved object actions, the default `open_form`
  identity/trigger and `open_form_view="0"`.
- `professional_quality_gate` runs registry and backend-plan integrity checks
  before the expensive payment/ORM lane.

## Historical escape replay

| Original change | Replayed paths | Required newly selected target | Result |
| --- | --- | --- | --- |
| #996 merge `a5aff5c26` | 111 | `verify.test.coverage.registry` | PASS |
| #997 merge `11a6984c4` | 32 | `verify.branch.governance.consistency` | PASS |
| #998 merge `0b980ce0e` | 52 | `verify.native_advisory.unit` | PASS |

The replay used the merge commit's first-parent diff and the current selector.
It proves selection completeness for those path sets; it does not rewrite or
retroactively validate the historical CI conclusions.

The six registered checks produced six non-zero reusable receipts covering
1,128 executed test cases. `make ci.local.iteration` also ran the repository's
trusted scan selection and full affected planning chain successfully.

The first freeze-preparation attempt stopped because the managed frontend
workspace had not installed `node_modules/.bin/esbuild`. This was an environment
prerequisite only. `make fe.install` restored the lockfile-matched workspace;
the unchanged freeze-preparation entry then passed and refreshed only the
expected complexity and split-plan reports.

## Retained failure and recovery

The first `make ci.local.iteration` attempt stopped before execution because
`scripts/verify/test_branch_governance_consistency_guard.py` had no selector
owner and the standalone parser test was conservatively treated as an Odoo
changed-test. Both were validation-tool defects. The branch test is now owned by
its real target, the parser test has an explicit host-standalone classification,
and the unchanged local iteration entry passed with 12 required targets.

## Exclusions

Product contracts, Odoo models, databases, deployment, user acceptance,
checkpoint/fingerprint redesign, workflow consolidation and retirement of the
legacy merge-preparation entry are outside this batch.

## Next exact step

Review the candidate diff, commit it as one P4 result, publish the clean exact
HEAD through the governed PR lane, and wait for the four current required checks.
No remote, database, deployment or user-acceptance state has been mutated.
