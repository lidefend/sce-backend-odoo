# Remote CI efficiency — 2026-10-17

Owner now authorizes one independent CI optimization PR through integration.
Protected squash is selected following the existing integration convention. All other tasks are paused.
Baseline: 42b19e0ba3141e54c3d8f5a949a08add0b93330f; transferred from a98fdc09, with identical
tracked trees before this CI delta. No additional worktree is created.

## Implementation and validation

Owner requested implementation in the existing PR, with no separate PR. P4 owns
workflow scheduling, build caches and test-plan reporting; no P0–P3 product, ACL,
contract, database or deployment changes are included in this addition. Stage
identity: a98fdc0983b7f4c1a0d7612b2a1dc46fb3a8ddd9 plus the declared dirty CI files.

Observed run 39027570048: standalone ORM 341 seconds, standard backend static
checks 64 seconds; the separate module suite was still running at observation.
The existing renderer change affects Odoo addons_path, so it remains runtime
impact. Unknown tool paths still fail closed; there is no whole-directory skip.

Implemented scope:
- The exact-tree backend plan is partitioned into at most four nonempty shards.
  Current 14 modules partition 4/4/3/3, disjoint with an identical union. Workers
  recompute from exact base/head; fail-fast is disabled and every shard must pass.
- BuildKit frontend layers are restored through the existing pinned cache action.
  Current Dockerfile/context are evaluated on every run and frontend output SHA
  is checked even on cache hits. This caches build work, not test success or DBs.
- Runner-local builders and Compose projects include the run/shard identity.
  Cleanup only accepts an exact run and index 0–3; nightly/dispatch retain the
  former manifest-plus-tests-directory discovery, including Python-only modules.
- Selection reasons, complete partition and executed/planned counts are printed
  into job summaries. Cache-key hits are observations, not test receipts.

Validation: verify.ci.workflow.contract 15+8+8 tests; risk workflow 17 tests;
GitHub security 18 tests; all pass (66 total). Ten workflow shell steps parse.
ci.local.iteration passed before the final cleanup/discovery fixes; final
freeze/Quick/remote results are recorded in the existing run index. No browser
or local database run is required for this CI-only delta. Existing product
evidence remains referenced, not rerun. Remote execution must still prove the
Buildx/Compose runner compatibility and actual time saved; no speedup percentage
is claimed before observation. First use is a cold cache. More runners can
reduce elapsed time but do not imply fewer total runner-minutes.

Cross-run ORM success reuse is deliberately not enabled: historical environment
readback is insufficient. Rollback is to revert this CI-only change, restoring
serial execution without changing product data or test assertions.

Integration update: PR #670 merged at 2026-10-17T11:33:27Z from
a98fdc0983b7f4c1a0d7612b2a1dc46fb3a8ddd9 as
42b19e0ba3141e54c3d8f5a949a08add0b93330f. The above CI optimization
was still uncommitted and was NOT included. Final iteration and freeze
preparation passed; no Quick, commit, push or new PR was performed for this
delta. Changes are preserved pending the owner's publication destination.
