# BACKEND-ITERATION-LANE-CLOSURE-20261124

## Identity

- Base main: `a5aff5c2684ef015a9462d836e29d82d970a4971`
- Branch: `fix/backend-iteration-lane-closure-20261124`
- Layer: P4 verification and delivery tooling

## Problem

The prior backend closure required separate manual product, demo and acceptance
dispatches. Product was repeated even though the required PR professional gate
already owned a product backend run. Run identifiers, suite names and frozen
plans had to be reconciled by hand, so the remote chain was feasible but not
itself a governed, efficient or merge-blocking deliverable.

## Required result

One exact-head backend iteration close must:

1. reuse an already-full product plan from `professional_quality_gate`;
2. dispatch only missing demo and acceptance suites;
3. bind every run and plan to the same head, base and suite;
4. wait once for all outstanding lanes and fail on any non-success;
5. emit one receipt that merge preflight can verify live;
6. reject CI-harness changes that lack this three-lane receipt.

The implementation must not add another test executor or change product
semantics, ACL, Record Rules, database structure or deployment state.

## Local implementation evidence

- `verify.backend_iteration_lanes.unit`: 7 PASS.
- `verify.frontend.dev.incremental.unit`: 240 PASS.
- `verify.ci.workflow.contract` via `ci.local.iteration`: PASS.
- `make ci.local.iteration`: PASS, ten affected targets executed.
- `make verify.ci.scheduled_gates`: PASS.

The local negative coverage includes exact head/base/suite/membership mismatch,
plan digest and origin drift, closure-surface routing, missing receipt rejection
and unrelated-path non-requirement.

## Real iteration evidence

The first real PR attempt (`6f4e1101e`) dispatched only demo and acceptance, as
intended, but the required professional gate skipped `backend_impact_suite`.
The path registry classified backend CI harness files as generic
non-backend control-plane. That made a separate product dispatch necessary and
violated the requested efficiency target.

The registry now has an exact `backend_ci_harness` category:

- `backend=true`;
- `backend_runtime=false`;
- `control_plane=true`;
- `backend_tooling=true`.

The risk classifier emits `backend_tooling_changed`. For that flag the required
professional gate runs an unbounded-base **full product** backend plan, so the
iteration close can consume it directly instead of launching a duplicate
product run. Focused backend business changes retain their existing bounded
selection.

Local evidence after this correction:

- `test_ci_risk_classifier`: 48 PASS.
- `test_ci_risk_workflow_contract`: 31 PASS.
- `test_backend_test_suite_dispatch_contract`: 34 PASS.
- `verify.ci.path_ownership.unit`: 23 PASS.
- `verify.frontend.dev.incremental.unit`: 240 PASS.
- `make ci.local.iteration`: PASS, eleven affected targets executed.

The superseded direct demo/acceptance runs were cancelled. A new exact PR head
must now prove the corrected chain.

After main PR #996, the contract reviewer group changed to
`group_sc_cap_contract_user`. The demo fixture already owned the matching user
`user_sc_contract_user_cap`, but its approval-seat map did not name that user.
The exact-head demo suite therefore failed during registry seed with
`no demo seat declared`. The fix declares only that demo role-to-user mapping;
the product approval model, groups, workflows and business code remain
unchanged.

While the iteration was running, main advanced from `27d0e2ae6` to
`a5aff5c26`. The latest main was merged into the published PR branch; the
generated reports were regenerated from the merged source, and the run baseline
was rebound before any new exact-head evidence was accepted.
