# CAPABILITY-EXPLORER-04-R3

## Scope

R3 only closes historical checkpoint identity. Product code, Explorer Handler,
Intents, frontend behavior, permissions and Quick target scope are frozen.

## Baseline

- Branch: `audit/platform-capability-studio-01-20261115`
- Full SHA: `304a754a39ff57f3df47ba9b600aa0164f330701`

## Required Change

Checkpoint validation must:

- recompute `runtimeTreeSha256` from the historical Git tree;
- recompute `authoritySha256` from historical Git blobs;
- evaluate target mapping through the recorded historical authority;
- reject replaced runtime, authority or mapping evidence even when PASS status,
  targetResults and logs remain self-consistent.

Unverifiable evidence falls back to `run.baseline_sha`.

## Verification

Implemented:

- `runtimeTreeSha256` is recomputed from the historical Git tree with the same
  ordering, mode and content algorithm used for the live runtime tree;
- `authoritySha256` is recomputed from historical blobs for the verifier,
  incremental executor and `make/frontend.mk`;
- the historical verifier source is loaded from Git and its own target mapping
  is used to validate `requiredTargets`;
- replaced runtime digest, replaced authority digest and changed historical
  mapping all fall back to the run baseline.

Checks:

- `verify.frontend.dev.incremental.unit`: PASS, 153 tests.
- `ci.local.iteration`: PASS, all registered affected targets executed.
- exact-head Quick: pending.
- remote CI: pending.

## Freeze Preparation

- `ci.delivery.freeze.prepare`: PASS.
- Generated complexity reports were refreshed for the two changed P4 Python
  tools and are included in the R3 scope.
- Product code, Explorer Handler and Intent contracts, frontend behavior,
  permissions, scenes, database state and Quick target scope are unchanged.

## Current State

Batch status is `verification_pending`: implementation and focused verification
are complete, while the exact-commit Quick receipt, PR #889 CI bound to that
commit, and final independent review remain pending. Mainline integration,
deployment and user acceptance have not been performed.
