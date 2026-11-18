# Mainline scheduled CI closeout (2026-11-18)

## Boundary

- Formal Product Layer: P0/P4
- Layer Target: generic dialog state projection, guard-registry lifecycle and formal-release lane equivalence
- Module: frontend contract action dialog, `scripts/verify`, CI risk lanes, merge policy
- Standard vs User-Specific: platform engineering standard

The scheduled `professional_quality_gate` failed because the guard registry still
declared `test_design_token_system.py` as an orphan after the test was wired into
the incremental selection map for `verify.frontend.style_system.guard`, while that
target did not actually execute the test. The scheduled `frontend_release_gate`
first failed in the action-reason dialog browser contract because the caller's
`data-state="interactive"` attribute overrode the `ScDialog` primitive's
authoritative `open`/`closed` state through `$attrs`.

Why here: `ScDialog` owns observable overlay lifecycle state. A consumer may attach
purpose markers, but it must not replace primitive-owned state. The registry is the
P4 lifecycle declaration for verification scripts and must match its executable
Make/CI consumers.

The formal-release boundary also required a control-plane distinction. An explicit
`ci:candidate` forces the same full professional and frontend lanes used by the
scheduled audit, but ordinary PR merge eligibility remains on its risk-selected
standard lane. A standard merge result is not formal-release evidence, and a
formal-release result is not a prerequisite for ordinary integration.

All pull-request actions now share one concurrency group per PR. Adding the candidate
label supersedes the preceding synchronize run instead of scheduling a second
authoritative suite on the same SHA; push and schedule remain isolated event groups.
Ordinary synchronize runs keep their short standard lanes. Only the exact candidate
label switches to the full formal-release lanes required for candidate construction.
The CI acceptance entry and its guards are registered as non-runtime frontend
control-plane tooling, so an ordinary PR no longer escalates to backend/ORM suites
through an unknown-path fail-closed classification.

Successful scheduled and explicit-candidate aggregate runs now emit a machine-readable
`release-condition.json` bound to the exact head/tree and four authoritative run IDs.
It sets `candidate_build_eligible=true` and `deployment_ready=false`, preserving the
separation between code qualification, immutable candidate publication and deployment.

The first full candidate run also exposed a stale route in the CI acceptance facade:
`login-probe` existed in the local runtime but not in the CI operation entry. The
operation now executes the governed internal login probe, and the release-CI guard
requires that route to remain present.

Why not elsewhere:

- no backend contract, model, permission, action or customer behavior changes;
- no required-check context name, gate, browser assertion or workflow schedule is weakened;
- the browser test already detects the attribute collision and remains unchanged;
- no unrelated orphaned guard is retired or reclassified in this batch.

## Scope

- Keep descriptive action-reason dialog attributes without overriding dialog state.
- Execute the selected design-token test in the existing style-system target and
  reconcile the guard registry with that executable consumer.
- Force candidate and scheduled runs through the same full frontend/professional
  lanes while keeping ordinary PR merges on risk-selected standard lanes.
- Collapse pull-request synchronize and candidate-label events into one group.
- Execute `verify.guard.registry` in every professional quality lane.
- Allow the governed published-branch sync to resolve only the known generated
  component-driver inventory conflict, then require full regeneration.
- Validate the affected browser contract, registry audit, style system, lint,
  strict typecheck, CI workflow, merge-policy and published-sync contracts, and
  agent ledger.

## Exclusions

- Required-check context names, branch rulesets and workflow schedules;
- database, fixture, deployment and user-acceptance changes;
- unrelated guard-registry debt and generated frontend inventories.

## Acceptance

- The action-reason browser test performs its non-zero assertion set and passes.
- `verify.guard.registry` passes without weakening or bypassing the audit.
- Non-FAST ordinary PRs merge on risk-selected standard lanes without `ci:candidate`.
- Candidate and scheduled runs both use full frontend and professional lanes.
- Only one pull-request concurrency run remains authoritative for a source identity.
- A successful scheduled aggregate emits an exact-head/tree release condition artifact.
- The release condition explicitly does not authorize deployment.
- The affected frontend lint, strict typecheck and style-system targets pass.
- `make ci.local.iteration` executes the registered affected set with truthful
  per-target status and original logs.

## Rollback

Revert the dialog state-marker correction, guard-registry repair, and formal lane
routing/tests together. No data or runtime state requires restoration.

## Execution log

- Baseline: `main@129df3827f4e8cffbc8302d626ec590ff63c14d9`,
  clean source with only this batch's governance metadata dirty.
- `verify.frontend.contract_reason_dialog.browser`: failed at the unchanged
  `section[role="dialog"][data-state="open"]` wait; original log retained under
  `.runtime/agent-runs/MAINLINE-SCHEDULED-CI-CLOSEOUT-20261118/logs/`.
- `verify.guard.registry`: unit tests passed 24/24, then the audit rejected the
  stale orphan acknowledgement for the already-wired design-token test; original
  log retained in the same runtime evidence directory.
- `make guard.registry.seed` removed the stale orphan entry but then failed closed
  because no Make target actually executed the test. The selected target was
  repaired rather than accepting a file-consumed disposition as execution proof.
- `verify.frontend.contract_reason_dialog.browser`: PASS, 21 checks, zero console
  errors.
- `verify.guard.registry`: PASS, 24 unit tests plus the 1633-script audit.
- `verify.frontend.style_system.guard`: PASS, 8 inline-style tests, 12 design-token
  tests and the guard audit.
- `verify.frontend.lint.src`: PASS, zero errors; four existing warnings remain.
- `verify.frontend.typecheck.strict`: PASS.
- `verify.agent.ledger.unit`: PASS, 18 tests plus ledger consistency.
- `verify.ci.workflow.contract`: PASS, 458 tests covering risk classification,
  candidate/full lane selection, ordinary merge eligibility without a candidate
  dispatch, workflow wiring and exact-head release-condition materialization.
- `release_condition`: PASS, 4 tests covering exact SHA/tree, workflow set,
  scheduled slot, candidate mode and fail-closed identity rejection.
- `verify.ci.scheduled_gates`: PASS, 97 tests including the CI login-probe route,
  shared internal-entry identity and release-CI guard wiring.
- The same exact head produced both an ordinary standard run and an explicit
  candidate run. The ordinary frontend lane completed in about 6 minutes and the
  full candidate frontend lane in about 30 minutes. The ordinary `merge_policy_gate`
  failed only because this branch temporarily required `ci:candidate`; that coupling
  has been removed and the matching merge-policy tests now cover both outcomes.
- `verify.guard.registry`: PASS again after the workflow policy correction,
  24 tests plus the 1633-script audit.
- `verify.agent.ledger.unit`: PASS, 18 tests plus ledger consistency.
- `make ci.local.iteration` after the merge-policy correction: PASS; the planner
  executed the affected workflow-contract, scheduled-gate and agent-ledger checks.
- `verify.workspace.branch.sync-github.unit`: PASS, 53 tests covering the exact
  published-branch sync, generated-report conflict handling and recovery paths.
- `make ci.local.iteration`: PASS, 16 affected targets executed on the final
  pre-commit working set.
- `make ci.delivery.freeze.prepare`: PASS; refreshed the complexity report, split
  queue and component-driver input digest affected by the source delta.
- `make ci.generated_evidence.preflight`: PASS.
- Published-branch sync appended reviewed main `9821a9c6` without rewrite or
  force-push. The governed conflict path accepted only the known generated
  component-driver inventory, recorded recovery bundle
  `e18bff8b40601a5acaf34f200c5a7a60600cb840aac90ac04529b01229725ec5`,
  and produced merge head `e9750af33285cb579b24ca4aa960f0b794e7b521`.
- `make ci.delivery.freeze.prepare` after that merge regenerated the conflicted
  inventory from the synchronized source tree and passed.
- The run's validation baseline advanced from the failing origin `129df382` to
  synchronized main `9821a9c6`; the original failing SHA remains recorded as the
  investigation anchor rather than being treated as candidate-owned diff.

Not run locally: full Quick, ORM and database acceptance. They are not required
for this ordinary candidate's local gate and the remote required checks remain
the integration authority.
