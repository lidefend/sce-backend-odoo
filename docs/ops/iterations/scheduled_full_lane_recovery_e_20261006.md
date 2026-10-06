# Scheduled full-lane recovery E (2026-10-06)

## Objective

Restore the scheduled `frontend_release_gate` full lane that `#594` (main
`90484d88`) left red, on main, via the protected PR flow.

## Why "PR green" was not "schedule green"

`scripts/ci/ci_risk_classifier.py` classifies `config/frontend/**` as
`unknown_path_fail_closed`, so `frontend_full_required=False` and the PR lane never
runs the full lane. The schedule forces `mode=full`
(`frontend_release_gate.yml`, "Resolve effective frontend lane"), so the two lanes
exercise different gate sets; `release_candidate_gate`'s schedule failures are a
cascade of this gate failing, not an independent defect.

## Three owning-layer fixes (no assertion relaxation)

1. **P0 frontend source typing** — `frontend/apps/web/scripts/contract_form_dirty_semantics_test.ts`
   replaced every `any` in the local harness with a concrete or `unknown`-based type
   and an explicit `as unknown as Parameters<...>[0]` cast. Assertions are unchanged.
2. **P0 platform guard review text** — `scripts/verify/frontend_scene_component_bridge_guard.py`
   re-registers the reviewed collaboration panel gate on the contract-derived
   `collaborationPanelVisible`, and re-points its self-check samples at the new
   contract-aware flag. The legacy delegation block is now an expected-negative,
   because the reviewed flag is the declaration-aware predicate rather than the raw
   delegation call.
3. **P1 construction product release projection** — `config/frontend/authoritative_navigation.json`
   adds the already-released project-ledger leaf
   (`menu_sc_project_project|action_sc_project_list|project.project`) to the
   `project_a_member` and `owner` browser projections and raises their
   `browser_expected_count` to 5 and 3. The leaf is already inside each role's
   `leaf_keys` and inside `ROLE_SURFACE_OVERRIDES`
   (`project_member`/`owner`/`pm` primary menus), so this converges the browser
   declaration on the released surface instead of relaxing any check.

## Evidence (this workspace, 2026-10-06)

| Layer | Command | Result |
| --- | --- | --- |
| L1 | `node --test scripts/verify/frontend_navigation_audit.test.mjs` | passed (1) |
| L1 | `make verify.frontend.page_identity` | passed (assertions 23/24, writers 1) |
| L1 | `make verify.frontend.release_navigation_policy.guard` | PASS roles=4 released_leaf_identities=84 |
| L1 | `make verify.frontend.scene_component_bridge.guard` | PASS checks=129 collaboration_self_check=266 |
| L1 | `make verify.frontend.release.unit` | passed |
| L1 | `scripts/verify/frontend_static_release_audit.py` | PASS (static.json) |
| L4 | `make verify.frontend.page_identity.browser` | pass=true surfaces=30 failed=0; navigation expected==actual (15/5/7/3) |
| L4 | `make verify.frontend.delivery_hardening.release.browser` | see run.json |

## Environment note

The first browser attempt was denied by the governed runtime check
(`DENY untracked listener owns port=5175`). The stray listener exited on its own;
the run was retried only after the port was provably free, and the governed
`frontend.acceptance.up` entry then passed. No audit was relaxed and no container
was manipulated directly.

## Mainline integration and remote proof (2026-10-06)

| Step | Result |
| --- | --- |
| Source head | `f9fdf2a862beb89f29a3772e342a3b4630b13bda` |
| Pull request | **#595** — public_guard / merge_policy_gate / professional_quality_gate / frontend_release_gate / release_candidate_gate all `success` on `f9fdf2a8` |
| Merge | squash → main `fda3fe4bcdd31324ec5ee20a54af8e4c980f9e5c` |
| Local quick | exact-head `ci.local.quick` receipt verified and reused by `pr.merge.local_quick_gate` |
| Push lanes on main | `frontend_release_gate` / `public_guard` / `merge_policy_gate` / `professional_quality_gate` = success |
| Full lane on main | `frontend_release_gate` **workflow_dispatch run 37475951901** = success; `pnpm test:release` PASS with `gate-result.json` `git_sha=fda3fe4b`, aggregate audit seven sections PASS, `navigation-report` 30/30 (finance 15, project_a_member 5, pm 7, owner 3) |

The branch `fix/scheduled-full-lane-recovery-e` was deleted after merge per the
repository convention, and this batch returns `.agent/active-runs.json` to its
empty terminal state so no index entry points at a deleted branch.

## Open, separate from this batch

- The paired cron (`frontend_release_gate` + `release_candidate_gate`, `30 18 * * *`)
  is confirmed only at the next occurrence. `release_candidate_gate` polls the
  scheduled `frontend_release_gate` for at most 30 minutes, while a cold-runner full
  lane measured ~35 minutes here; that margin is a standing risk not introduced or
  closed by this batch.
- `make verify.frontend.fixture.guard` still fails with `KeyError 'project.project'`
  on main (inherited from run D, untouched here).
