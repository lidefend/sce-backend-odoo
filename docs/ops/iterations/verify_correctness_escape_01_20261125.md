# Verification correctness and escaped dependency closure

## Identity

- Audit baseline: `main@032990188abea05a5d2ab81313136c431e5f89b3`
- Integrated candidate base: `main@487a3d8497cd89841e1954d164e0e11d79742d81`
- Candidate branch: `fix/verify-correctness-escape-01-20261125`
- Layer: P4 verification and CI control plane
- Environment: registered offline checks plus disposable `sc-local-test/sc_test`; no persistent database, deployment or remote mutation

## Objective

Deliver `VERIFY-CORRECTNESS-01` and `VERIFY-ESCAPE-02` as one independently
reviewable P4 result. The first batch makes diagnostic collection additive,
aligns shared-contract reuse with ordinary receipt reuse, and prevents a
zero-test target from passing. The second batch closes the dependencies exposed
by #996, #997 and #998 and moves cheap registry/plan checks ahead of ORM work.

## Result index

| Area | Required proof | Actual result |
| --- | --- | --- |
| Frontend incremental executor | `make verify.frontend.dev.incremental.unit` | PASS, 260 tests |
| CI workflow and planners | `make verify.ci.workflow.contract` | PASS, final attributable runner count 34 |
| Test coverage registry | `make verify.test.coverage.registry` | PASS, 21 tests |
| Merge/branch governance | `make verify.branch.governance.consistency` | PASS, 23 tests |
| Native parser | `make verify.native_advisory.unit` | PASS, 53 tests |
| Published sync | `make verify.workspace.branch.sync-github.unit` | PASS, 56 tests |
| Contract consumer | `make verify.unified_page_contract.v2.runtime` | PASS, 151 tests |
| Local affected iteration | `make ci.local.iteration` | PASS, 17 executed targets and 989 executed tests |
| V2.7 `smart_core` classes | registered disposable ORM entry | PASS, 97 tests |
| V2.7 bundle classes | registered disposable ORM entry | PASS, 16 tests |
| V2.7 industry classes | registered disposable ORM entry | PASS, 351 tests |
| Freeze preparation | `make ci.delivery.freeze.prepare` | PASS; generated evidence current |
| Remote PR integration | Four exact-head required checks | pending final metadata recovery HEAD; `91e1a30b2` had three success checks and a transient merge-policy API failure |
| Backend responsibility lanes | exact-head close receipt | PASS on `91e1a30b2` for product, demo and acceptance; final HEAD rerun required |

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

## Review follow-up

The #1003 REQUEST_CHANGES findings are closed at the tool boundary:

- Receipt invalidation now calls `select_iteration_targets()`, the same impact
  calculation used by execution. A production `execute_targets()` regression
  proves that changing `scripts/ci/backend_impact_plan.py` executes the registry
  audit, allows its injected failure to fail the run, and still reuses unrelated
  frontend targets.
- Test metrics read only the final attributable runner summary. True zero
  collection, all-skipped execution, naked `PASS`, and a successful nonzero
  result have distinct outcomes. The real zero-test negative test also passes
  when wrapped by an outer runner whose final summary is nonzero.
- Published synchronization no longer has a parser-test source auto-resolution
  special case. A parser-test conflict is unapproved and restores the original
  candidate; generated reports and the active-run index remain the only
  metadata conflict resolutions.
- `verify.changed_tests.orm` now emits one final aggregate summary containing
  the positive test counts from its actual or reused module receipts. The
  executor compares final summary positions from every supported runner, so an
  outer aggregate supersedes inner summaries without allowing a naked pass
  marker or zero execution to succeed.

The inherited V2.7 failures were migrated at their test callers: all UI contract
requests declare explicit version and client identity, report tests declare
pivot/graph rendering capabilities, component identity assertions use
`semanticType`, widget options use `widgetOptions`, explicit domains remain
`domain`, and form structure reads occur only after successful negotiation.
Original business, permission, state and native-view assertions were retained.

The first exact-class attempt remains as a failed observation:
`product_reports` required pivot and graph capabilities in addition to version
negotiation. After declaring those capabilities, the complete 25-class industry
set passed 351 tests.

A publish-preflight rerun then exposed the aggregate-summary gap above. After
adding the final `PASS tests=466 modules=3` summary,
`verify.changed_tests.orm` passed with 16 bundle, 353 industry and 97 smart-core
tests.

The required backend-iteration close lane then found three inherited demo tests
that still read the old object-shaped `SystemInitHandler` response. The tests
now unpack either the canonical dict response or the legacy object, declare the
same explicit V2.7 client identity, and retain their response-equivalence and
SQL-count assertions. A local execution is intentionally `not_run`: the demo
module's own guard rejects the disposable `sc_test` database and requires an
authorized demo environment. The exact-head remote demo lane is the owning
proof.

On exact HEAD `91e1a30b2`, `public_guard`, `frontend_release_gate` and
`professional_quality_gate` passed. The `merge_policy_gate` waiting job failed
with GitHub API `HTTP 502` before it could read authoritative dependency runs;
no repository assertion failed. The close entry then passed product, demo and
acceptance, proving the demo V2.7 migration. Repository publication rules do not
provide a direct workflow-rerun Make entry, so the recovery fact is committed as
new metadata and the new exact HEAD must rerun all four required checks and the
backend close.

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

## Mainline synchronization

After the first candidate commit `bffa24cdeec6b04d2e336d1ef4527d9469458f9f`,
`origin/main` advanced from the audit baseline to
`e940285aed4a9747931c26ec0a52283b5d296d14` through PR #1002. The governed
`workspace.branch.sync-main` entry rebased the responsibility commit onto that
mainline and rebuilt generated evidence in
`d1b9a9fc995d11598fa77111e5270ca6fff70188`.

Mainline PR #1002 also changes native-widget contract selection and the
semantic registry, so all validation whose declared inputs intersect those
files must be rerun against the new candidate. The previous receipts remain
historical evidence and are not asserted as current.

The first post-sync local iteration then found a new instance of the same
escaped-dependency class: PR #1002 declared
`p0_contract_descriptor_conformance_evidence` without a coverage-registry
disposition. The new selector correctly surfaced it before publication. The
tag is now bound to
`make verify.p0_contract_producer.p0a.descriptor_conformance`; that target's
real isolated ORM run passed one test with `ORM_RESULT_GUARD=PASS`, followed by
the real-contract decoder check with 45 strict descriptors. The complete local
iteration then passed all 13 required targets.

PR #1003 then exposed one additional validation-tool defect in its first remote
frontend run: the standard lint, strict typecheck, unit tests and static
convergence steps passed, but the result-recording shell branch incorrectly
required `frontend_mode=skip` when no diagnostic was requested. The branch is
now a no-op after the already-validated standard outcome, and a focused workflow
contract test executes the real recording script for that exact case.

The second mainline update was `fe1573b21c15c67d388eb7e1064561b41334b5c2`
(PR #1004, Contract V2.7). The published-candidate sync preserved history in
merge commit `1f106acefc2fe66e7b28e03fdc3b373bf965250e`. The only semantic
conflict was the standalone parser test: this batch adds the additive
`open_form` regression, while main adds ORM field-capability projection and V2.7
semantic identity. The committed union retains both. Generated-report conflicts
remain invalidated until the final freeze preparation rebuilds them.

Mainline then advanced to
`487a3d8497cd89841e1954d164e0e11d79742d81`. The governed published-branch sync
created `fe57c5b977c79160579b5cffa5144636c62fd369` with no conflicts; its
recovery bundle is stored outside the worktree. The synchronized candidate
reran all affected offline and ORM sets before this record was updated.

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

Record the exact-HEAD GitHub API 502 recovery, publish the new metadata
candidate through the governed PR lane, rerun the four required checks against
main `487a3d8497cd89841e1954d164e0e11d79742d81`, and close the backend iteration
chain on the new HEAD. No persistent database, deployment or user-acceptance
state has been mutated.

## Sole-executor closeout on 2026-11-26

The owner assigned sole execution and requested closure of the CI line. Readback
confirmed all four required PR #1003 checks passed on
`c68acbc2aefc4f03760f0c0e02dc6b043f1807a2`, base
`487a3d8497cd89841e1954d164e0e11d79742d81`. The matching backend close receipt
also passed: product reused professional CI; demo run 45690039143 and acceptance
run 45690103242 were independently read back as successful at that exact HEAD.
These results supersede the historical pending narrative above for that candidate.

Closeout inspection then reproduced a remaining false pass: a zero-exit Make
test emitting only `Ran 5 tests in ...` received an unknown summary status but
was still accepted. P4 now requires a successful final summary as well as a
positive execution count. The new real-Make regression failed before the fix;
all 261 executor unit tests passed after it. Original log:
`.runtime/agent-runs/VERIFY-CORRECTNESS-01/unknown-summary-unit.log`.

This delta changes only the verification executor, its regression and this run's
bookkeeping. No product code, ORM test, runtime profile, workflow or scan rule
changes. Local responsibility is the affected executor and workflow/registry
consumer checks plus source/diff identity. Existing product/demo/acceptance runs
remain historical exact-head evidence; new PR integration is pending. Scheduled
release, deployment and persistent database writes remain excluded. Rollback is
the bounded follow-up commit; the previous candidate remains recoverable.

## REQUEST_CHANGES remediation: TAP and existing frontend producers

The independent review at `f12d636827ab7bd6a3300c43ab11a5b1374959fe`
identified two remaining defects. TAP is now parsed separately from generic
success markers: tests/suites/pass/fail/cancelled/skipped/todo and the terminal
duration must all be present once, and outcome counters must reconcile. Actual
execution excludes skipped, todo and cancelled tests. Failure/cancellation,
all-skipped/all-todo, inconsistent counters and incomplete summaries cannot pass.
A trailing incomplete TAP count cannot inherit an earlier unittest success.

The two named producers retain their original assertions inside actual Node test
cases. Their Make entries explicitly select TAP. A bounded inventory of other
standalone frontend test producers found 28 additional targets with bare or
nonstandard summaries. Their existing assertion scripts now execute under the
Node TAP runner through the same Make entries; compiler and syntax-check commands
remain unchanged. No fabricated count or acceptance of bare PASS was introduced.

Verification: 267 executor unit tests passed, including real Node all-skipped,
positive/mixed-todo and failure cases, incomplete/cancelled-counter regressions,
and a real repository frontend Make target through the executor. Both named
producers plus the 28 inventoried targets passed through the executor with
nonzero attributable results. Original per-target logs and reconciliation are in
`.runtime/agent-runs/VERIFY-CORRECTNESS-01/review-producer-reconciled-results.json`;
unit log is `review-tap-verified.log` in the same directory. Initial wiring attempts
and failures are retained separately; only the final per-target results are used.

P4 owns the parser, tests and Make reporting changes. There is no production
frontend/ORM change. Local validation is limited to these producers and affected
executor/workflow/registry checks; exact-head remote CI and independent re-review
are still required. No full local ORM or browser matrix is introduced. The reviewer
identified two coverage-registry collisions with #1006; reconcile them against the
actual registered entrypoints after #1003 integrates and #1006 is governably synced.
Do not merge either old REQUEST_CHANGES candidate on green CI alone.

The additional activation-form producer exposed a pre-existing whitespace-sensitive
fixture: both the original direct Node command and the TAP command found zero
rules because the shipped template now places attributes on separate lines.
Its regex now accepts whitespace while retaining exactly three required rules and
all behavioral assertions. Both novalidate assertions likewise accept whitespace.
The final activation producer passed, completing 30/30 reconciled target results.
The failed original/direct and first adapted runs are retained as diagnostic logs.

### Follow-up: public history fixture registration

Exact candidate 58024e373 failed public_guard run 45703420008 on RH018 for payment permission fixture blob ed8f1aaa4953693e9d502bce2871a038524791a5. Trusted-base history covers public refs, including the product branch; this is not a new business-data value in the CI diff. Compared to registered blob 578ab14089ea852ce60f7fa96da3f27eec3f4b96, its only change replaces the p02 entry group reference with its capability scope. Synthetic fixture values are unchanged. Register the same exact path/rule/blob exception already present in #1006; no wildcard exemption or scanner weakening. Original failed remote log: `.runtime/agent-runs/VERIFY-CORRECTNESS-01/review-public-guard-failure.log`. New remote exact-head checks remain required.

Follow-up validation passed: 18 parallel scanner tests, 9 personal-data tests, 37 history-guard tests; explicit trusted-base history scan passed (9,524 blobs, no sensitive values recorded). Logs: `review-fixture-unit.log`, `review-fixture-history.log` under the same runtime run directory. Registration-only delta leaves the previously verified executor/producer inputs unchanged.
