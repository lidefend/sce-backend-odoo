# Release snapshot legacy fingerprint compatibility (2026-11-22)

## Result

Current main could authenticate a user successfully but then returned HTTP 500
from `system.init` with `PUBLISHED_PRODUCT_PAGES_FINGERPRINT_MISMATCH`. The
frontend consequently remained on `/login` and reported a generic login failure.

The defect is an upgrade compatibility break, not a credential or fixture
failure. Active released snapshots frozen before PR #945 carry the original
immutable fingerprint payload. PR #945 added `business_scene_composition` to
the current payload, so those unchanged snapshots no longer validated.

## Read-only evidence

- Runtime: `sc_frontend_acceptance`, source revision
  `594309dee5430d8f9e69b324ebc9aa53b73e00ba`.
- `login=200` returned the fixture principal and role closure.
- `system.init=500` trace
  `f87f3ce5-d487-44ec-b017-b11c6667c43f`.
- Active snapshots 54 (`construction.preview`) and 82
  (`construction.standard`) both matched the pre-#945 algorithm and did not
  match the current algorithm.
- No snapshot, fixture, database, or business data was written or rebuilt.

## Correction

`EditionReleaseSnapshotService._draft_fingerprint` now includes
`business_scene_composition` whenever the policy carries the field. A policy
that predates the field uses the preserved legacy payload. This distinction is
deterministic and keeps page, policy, schema, digest, and tamper checks intact.

## Validation

- `make verify.daily.published_face.target.unit`: 14 tests passed.
- `make ci.local.iteration`: passed; two affected targets executed.
- No full Quick, acceptance fixture reset, module reinstall, or migration.

## Remaining boundary

Real business handling remains pending until a new artifact containing this
change is served in the registered acceptance environment and the 46-scenario /
132-page user journey acceptance resumes.
