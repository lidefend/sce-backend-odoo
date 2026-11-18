# Formal-release CI parity (2026-11-18)

## Boundary

- Formal Product Layer: P4
- Layer Target: exact-head formal-release CI aggregation
- Module: professional quality gate and nested backend suite
- Standard vs User-Specific: platform engineering standard

Nightly schedule, the governed `ci:candidate` label and an authorized operator
full audit are three ways to request one formal-release conclusion. They must not
produce different verification strength.

The schedule currently starts the nested backend test suite and the complete
registered offline baseline. Explicit candidate and operator full-audit runs do
not, even though they request the full professional quality lane. This creates a
weaker explicit condition and permits a formal-release artifact without the same
backend evidence used by the nightly mainline audit.

## Correction

All formal-release triggers must:

- run the nested backend test suite over complete module scope, not PR changed-module scope;
- run the complete registered offline baseline;
- prevent `professional_quality_gate` from succeeding if either producer fails;
- preserve ordinary PR changed-scope backend selection and standard-lane latency.

Scheduled runs additionally retain the cron slot identity. Explicit candidate and
operator runs remain distinct from a natural scheduled event in
`release-condition.json`; all three still emit `deployment_ready=false`.

## Exclusions

- Product code, contracts, database state, deployment and user acceptance.
- Required-check names, branch rulesets and ordinary PR standard-lane behavior.

## Rollback

Revert the formal-trigger routing and contract tests together. No runtime data
requires restoration.

## Execution log

- `verify.ci.workflow.contract`: PASS, 458 tests, including the formal backend
  truth table for schedule, candidate, operator audit and ordinary PR events.
- `verify.ci.scheduled_gates`: PASS, 97 tests.
- `verify.guard.registry`: PASS, 24 tests plus the 1633-script audit.
- `verify.agent.ledger.unit`: PASS, 18 tests plus ledger consistency.
- `make ci.local.iteration`: PASS on the affected CI contract set.

The operator full audit for the previous main head exposed this parity gap:
workflow-dispatch and label qualification selected the full frontend and
professional jobs, but did not inherit the schedule-only nested backend suite
and offline baseline. The corrected condition is shared by all three formal
release triggers.
