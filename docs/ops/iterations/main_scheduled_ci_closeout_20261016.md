# Main scheduled CI closure — 2026-10-16

## Scope and ownership

Formal Product Layer: P4. Layer Target: test fixtures and CI verification.
Module: frontend test scripts, smart_construction_core tests, demo tests, backend suite.
Standard vs User-Specific: generic verification; no customer-specific behavior.
Why Here: nightly failures must distinguish stale tests from actual product defects.
Why Not Elsewhere: do not weaken ACL, data-space or lifecycle guards to satisfy fixtures.
Blast Radius: affected frontend assertions and backend test classes; existing runtime behavior unchanged unless independently proven defective.
Excluded: dirty primary worktree, daily server, customer module, deployment, live data writes.

## Plan

1. Bind original schedule failures (10bf72ef) to current main41c7a9dd and classify exact failures.
2. Fix six frontend test lint errors and run affected behavioral scripts plus lint/type checks.
3. Repair confirmed stale backend setup/assertions using formal lifecycle/data-space declarations; validate targeted classes through existing governed test lanes. Escalate product defects to their source layer, never bypass guards.
4. Run affected CI lanes, independent review, freeze/Quick and protected PR integration. Restore scheduled coverage without skips or reduced test scope.

## Evidence and rollback

Original logs: /tmp/sce-ci-38818510036.log, /tmp/sce-ci-38811434965.log, /tmp/sce-ci-38811625754.log.
Release candidate failure is downstream of frontend gate. Backend core: 30 failures/59 errors of483 tests; demo:1 failure of11. These are original observations, not current candidate results.
Rollback: revert owned commits; ordinary tests rollback; independently committed race fixture cleanup and restoration required. Stop dependent validation on earlier failures; reuse independent results with unchanged inputs.

## Diagnosed product defect and refined boundary

P1 workspace dispatch was a real product failure, not a stale positive assertion.
The standard snapshot released both workspaces while their old standalone target
menus were absent from the released surface. Finance already declared the actions.
Use existing contextual action authority to bind each handling action to its released
workspace menu. Each workspace explicitly select their own carrier; the shared
ledger must not borrow the sibling workspace's route. No ACL, release filter or
visible navigation baseline is relaxed. Published integration tests move to the
industry bundle, which owns startup product identity; core-only installs do not.
All nine handling actions and both ledger buttons are asserted, replacing partial
continue-based observations. The first four bundle tests passed after this fix;
negative carrier tests and independent review remain pending.

Additional targeted results:54 transactional P1 funding/finance tests had53 passes
and one secondary-company context error, corrected in its fixture. Payment-domain
isolation6tests passed; normalized payment body assertion passed after removing
retired interaction fields and rebinding its exact edit field count. Core amount
matrix5tests passed. Runtime logs remain in /tmp/sce-scheduled-*.log; these are dirty
iteration observations, not frozen delivery receipts. Four independently committed
concurrency tests were excluded from this transactional run by AST call-graph analysis
(/tmp/sce-scheduled-p1-committed-exclusions.json), not from final CI coverage.

## Consolidated batch review

Three workspaces now bind contextual routes to their own carrier. Explicit grants
cover finance (11), project_member/pm (3 each) and exclusive business_full (14).
Published integration tests prove all actions, own-carrier refusal and exclusive role
behavior without increasing the 90 published menu baseline. Backend fixtures create
explicit synthetic customer companies and formal approval policies; platform bootstrap
data stays unchanged. Legacy-corruption negative fixtures are distinguished from
positive formal action flows. Demo assertions follow real approval-driver delegation.

Final uncovered run:13/13; separate ambiguity1/1 and legacy-identity1/1. P0 lifecycle79
passed and prior unchanged affected cases retained (single run evidence index).
Concurrent fixture setup now owns its independent company, uses bounded transactions,
and removes exact company dependencies after execution; prior failed-cleanup records
were restored through a bounded local.dev.test recovery and read back absent.

L1 iteration, role-surface16 + create-defaults4+5, scheduled guards and ORM31 negative/
positive cases passed. Independent dirty review found no blocker; this is permission
to freeze, not remote CI success. No daily/customer database changes or deployment.
Final exact-head Quick, independent frozen review and full isolated GitHub backend
suite remain required. Release/frontend schedule failures will be checked through
the affected candidate gates. All original logs are indexed in run.json.
