# Delivery Lane and Release Orchestration (2026-10-23)

## Batch boundary

- Batch objective: complete the presentation-only acceptance lane and the daily
  release command sequence.
- Formal product layer: P4 ops delivery tooling.
- Layer target: acceptance suite selection, presentation evidence and daily
  release orchestration.
- Excluded: product UI/contracts, backend models, ACL, permissions, customer
  configuration, databases and business data.

## Planned implementation

1. Declare a `frontend_presentation` evidence suite and a narrow set of
   presentation-owned frontend paths.
2. Add a declared project-form presentation target and expose one lightweight
   browser Make entry.
3. Add a fail-fast daily release orchestrator that invokes only existing governed
   Make targets in the required order.
4. Add non-zero unit tests for classification, evidence validation, command
   order, identity binding and stop-on-failure behavior.

## Implementation

- Added the `frontend_presentation` suite with a `presentation_header` evidence
  adapter. It requires a head-bound passing browser report, one or more declared
  targets, zero mutations, zero console/page/HTTP errors, one page header/title,
  no unresolved components and no mobile overflow.
- Added the explicit `frontend-presentation` first-match path rule. Only the
  declared shared presentation files use `frontend_contract + frontend_presentation`;
  other frontend runtime files continue to require `list_surface_structure`.
- Added `config/acceptance/frontend_presentation_targets.v1.json` and
  `make verify.frontend.presentation.browser`. The target resolves the declared
  `project.project` object from the role-home contract, waits for the exact
  record route, and records the semantic page/header result.
- Added a fail-fast daily release orchestrator. Both
  `make daily.runtime.main.release` and
  `make daily.runtime.candidate.release` run:
  `sync → frontend build → duty refresh → demo align → platform align → published face → entry verify`.
- Added `DAILY_RUNTIME_RELEASE_PLAN=1` to the same main/candidate release entry
  for read-only sequence inspection, without creating a second dead Make target.
- Fixed recursive-Make argument freezing exposed by the first live candidate
  release: the orchestrator now removes parent-expanded `*_FLAGS` builders
  before each child Make, so digest, duty and selection options are re-expanded
  from the exact step inputs instead of silently becoming empty.
- Wired the presentation unit lane into the frontend Quick gate and the release
  orchestration unit lane into delivery freeze preparation.

## Verification

- `make verify.frontend.presentation.lane.unit`: PASS, 42 tests plus the vendor
  coupling guard and JavaScript syntax check.
- `make verify.daily.runtime.release_orchestration.unit`: PASS, 7 tests covering
  main/candidate order, identity fields, fail-fast behavior, release-input
  propagation and Make wiring.
- `DAILY_RUNTIME_RELEASE_PLAN=1 make daily.runtime.candidate.release`: PASS and
  prints the complete main/candidate sequence without executing it.
- `make audit.verification.lane_coverage.check`: PASS. The former dead-surface
  disposition for `daily.runtime.database.duty.refresh` was removed because the
  release orchestrator now references and executes it.
- `make verify.frontend.presentation.browser`: PASS against daily
  `804e793d…`; one project-form target, zero mutations, zero console/page/HTTP
  errors and no mobile overflow.
- Presentation evidence was consumed by the new adapter:
  targets=1, mutations=0, runtime_errors=0.
- First live candidate release: bundle sync and frontend build PASS; duty refresh
  failed closed because the parent Make had exported empty recursive argument
  builders. The failure was classified as a P4 validation-tool defect; the
  release-input propagation fix and regression test own the correction.
- Second live candidate release: sync, frontend build, duty refresh, both source
  revision alignments PASS. Published-face verification exposed a stale direct-
  prerequisite assertion in its coupling test. The assertion now verifies that
  the single release entry owns the orchestration unit and that the executable
  sequence preserves both code and published faces in order.
- Third live candidate release: all seven steps PASS. Receipt review found the
  frontend-build result still written to the legacy default path because its
  derived report alias was frozen by the parent Make. The step now names both
  the receipt and report path explicitly, and the regression lane guards their
  candidate-scoped equality.

## Risk and rollback

The main risk is misclassifying a semantic frontend change as presentation-only.
The lane therefore uses an explicit path allowlist rather than `frontend/**`.
Revert this P4 topic to restore the previous full-list evidence requirement and
manual release sequence.

## Next exact step

Freeze the candidate, run exact-head Quick, publish the P4 PR and verify the
new orchestration entry through the normal protected merge/deployment path.
