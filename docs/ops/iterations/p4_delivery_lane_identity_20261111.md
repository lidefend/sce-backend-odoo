# P4 delivery lane identity reconciliation — 2026-11-11

## Boundary

- Formal Product Layer: P4 ops delivery tool
- Layer Target: registered frontend acceptance contract receipt and browser prerequisite orchestration
- Module: `make/frontend.mk` and frontend acceptance runtime profile tooling
- Baseline: `cbe509f08085d9ac65bf70a352af50898a3511fa`
- Excluded: backend scene menu, contracts, ACL, database writes, frontend product changes, push, PR and merge

## Problem

The clean frontend candidate was `cbe509f08`, but `backend.acceptance.up` and
`acceptance.runtime.contract_receipt` remained bound to the parent backend
`fe2f8ba17`. The list and presentation lanes then correctly rejected the stale
receipt (`contract_receipt_stale`) instead of accepting evidence from a different
source identity.

## Decision

The established Runbook order now has one explicit integration front door:
preview build, preview switch, governed backend replacement/reuse, contract
receipt, then the presentation, list and relation browser suites. That entry is
the only place the shared acceptance backend is replaced. The resolver refuses to
write a receipt unless the served backend revision equals the clean candidate
HEAD. Ordinary browser targets consume and verify the receipt but cannot mutate
another iteration's backend as a hidden prerequisite.

Persistent `local.dev` is the normal iteration and read-only page-validation
database. Frozen-candidate merge evidence uses the isolated `candidate` profile
with its own database, backend, preview and fixture scope. A shared acceptance
carrier is only used for coordinated whole-product acceptance; if an independent
iteration changes its source revision, that carrier is not a stable evidence
authority for the current candidate.

## Final evidence

- Final P4 candidate: `fix/p4-delivery-lane-identity-20261111` at this commit
- Backend container and runtime API: bound to this commit
- Resolver and contract receipt: bound to this commit
- List-surface and presentation receipts: bound to this commit
- Classification: `environment_defect`
- No GitHub push, PR, merge, deployment or business-database write performed by this batch

## Validation

- `make verify.frontend.standard_preview.unit`: PASS at the code-identical
  pre-document candidate, 135 Python tests and 42 Node tests, original log
  `.runtime/p4-delivery-lane-identity/orchestration-unit-dependency-projection.log`.
- `make verify.frontend.list_surface_structure.browser`: PASS, 18 rows, 0 failures,
  plus 23 static contract tests.
- `make verify.frontend.presentation.local.browser`: PASS, one header target,
  0 mutations and 0 errors.
- The final acceptance integration entry and its ordering are covered by the
  focused orchestration unit before the final clean-candidate run.
- First `make ci.local.iteration` correctly stopped at verification-lane coverage:
  the explicit integration entry made two previously zero-reference preview
  targets live, leaving their old dispositions stale. The governed
  `--unregister-target` operations removed only those two stale entries; the
  73-test coverage unit and audited lane check then passed.
- A second integration attempt exposed residual coupling: static preview
  build/up still validated the existing backend artifact first, so a stale
  backend blocked its own repair path. The preview lifecycle now performs only
  its profile preflight; backend-dependent browser operations retain the exact
  artifact identity gate.
- Candidate fixture execution now derives its declared fixture scope from the
  selected runtime profile (`local→acceptance`, `candidate→candidate`) unless
  the caller explicitly supplies one, preventing a candidate run from writing
  the shared acceptance database.
- Linked worktrees had inherited absolute `node_modules` symlinks from the
  primary worktree, so Vite read `@sc/ui` source from another branch even while
  building the candidate app. The cached dependency entry now removes only
  repository-owned primary projections and restores a worktree-local offline
  install; foreign symlinks still fail closed. Preview build identity now also
  fingerprints the resolved dependency projections, so switching projections
  invalidates a bundle that was built from another worktree.
- The repository commit hook refreshed `complexity_budget_report.md` and
  `split_plan_queue.md`; both generated files are included explicitly in the P4 scope.
- The run declares a runtime environment, so its offline receipt is reported as `stale`
  by the existing run evaluator rather than automatically reusable. The recorded result
  is still truthful and was not relabelled as runtime evidence. Documentation-only
  changes do not alter the 133-test inputs, so that result is carried forward.
- Runtime reuse is keyed by a stable backend environment readback. The browser report
  remains a produced result and is not incorrectly declared as an input readback.
- The contract prerequisite intentionally rejects a dirty tree; runtime evidence is
  therefore collected only after the final clean candidate is committed.
