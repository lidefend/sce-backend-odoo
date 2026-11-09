# Daily published-face action target projection

Status: verification_pending

The daily runtime was partially deployed from `c819daff496deab474bf97b84031bfd50db148bc`
to `9086ddab6cd19b0ee30e6f6dae149c0df83ededd`. Code sync, frontend build,
duty refresh and both source-revision alignments passed. Published-face
convergence then stopped at `RELEASE_PREFLIGHT_BLOCKED`.

Read-only runtime evidence identified five action pages in each maintained
product policy that carried both a native action route (`/a/...`) and a
`target_scene_key`. The release-page projection converted that association into
`scene_key`, and the target-integrity guard correctly reported
`ACTION_MENU_HAS_SCENE_KEY`.

The defect is in the P0 release-page projection. `target_scene_key` is the
target identity only for a declared scene route (`/s/...`). It remains a scene
association, not a target replacement, on a native action route. The focused
fix preserves both paths and adds positive and negative projection tests. The
tests are wired into a daily executable target consumed by the existing
published product-menu release gate; no candidate-only release lane is used for
inner-loop validation.

The final P0/P4 delta was verified at `9086ddab6cd19b0ee30e6f6dae149c0df83ededd`
plus the explicit dirty scope:

- `verify.daily.published_face.target.unit`: 4 tests, PASS.
- `verify.frontend.dev.incremental.unit`: 95 tests, PASS.
- `verify.agent.resume.unit`: 56 tests, PASS.
- `verify.agent.ledger.unit`: 18 tests plus ledger guard, PASS.
- `verify.guard.registry`: 24 tests plus registry audit, PASS.
- `make ci.local.iteration`: PASS with five executed targets and zero failures.

No product-policy row, frontend code, ACL, native action or production runtime
is changed by this batch.
