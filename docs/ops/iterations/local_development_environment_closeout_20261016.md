# Local development environment closeout — 2026-10-16

P4 / local development lifecycle and verification. Owner requested direct completion.
One independently acceptable result; isolated second worktree, main worktree remains owned by daily-runtime executor.
No overlapping product files or remote runtime writes. Separate rollback and local-only resources.

## Scope and stage

Base b966d66a0c4132e7b2c75e497fec5bf2207d44d6; iteration work, not frozen.
Required: existing sc-local-dev / sc_dev_demo feature environment. Optional: sc-local-clean / sc_clean clean installation and sc-local-sample / sc_dev_sample technical sample. No customer data import or mandatory always-on three-database replica.
P0/P1/P2 semantics unchanged; P4 owns environment readiness, not product correctness.

## Validation plan

L0 governed worktree/run; L1 syntax and iteration guard; L2 nonzero lifecycle/readiness tests; L3 existing local.dev health/authority and a bounded clean-install rehearsal if prerequisites pass. No broad browser matrix, customer migration, daily deployment or final Quick for inner-loop observations.
Independent B review before completion. Original result paths are indexed in run.json, not duplicated.

Initial observation: local.env.status exited 2 solely because optional sample/clean profiles were unprepared; persistent health passed. Keep the strict all-profile status entry intact; add a distinct developer readiness entry that explicitly reports optional absence, rejects orphan resources and errors, and never labels untested lanes passed.

## Runtime result and recovered authority

Both canonical feature and clean-install environments pass actual health, including exact database/filter/volumes, running services, frontend HTTP 200 and base installation. Clean health additionally verifies its configured default sc_norm_engine installation and empty project/norm business tables. No fresh install, rebuild or recovery drill is claimed in this batch.

The clean containers were already running; only their default env file was missing. The original private recovery archive was found under the existing workspace evidence authority. Its project/database/filter/three volumes/ports and isolated-rehearsal marker matched; DB and application secrets matched container values in memory without printing them. Restored original bytes to the original .env.local.clean path with exclusive creation and 0600, then read back health. No secret generation, database reset, new environment or customer import occurred. Receipt: .runtime/local-environment/env-recovery.json. To undo the file restoration, verify original-byte equality before removing only the restored env file; preserve archived authority and runtime volumes.

The first existing local.dev.verify_authority invocation unexpectedly recreated its DB dependency when invoked from this linked worktree. Persistent named data was retained, authority passed. The wrapper now uses --no-deps, with an actual shell-call regression test; subsequent authority and health passed without recreation. This is not a read-only-effect claim for the first invocation.

## Daily local operating guide

From this worktree, run `make local.env.readiness`. It inventories only the three registered profile resource sets, verifies literal credential-file identity, then delegates health to existing governed targets. It does not display credentials. Absent optional profiles remain not_prepared/health=not_run. Existing resources without credential authority, wrong profile, ambiguous identity or Docker errors fail closed. The existing `make local.env.status` remains a strict all-three-profile check and still fails if sample is absent; use it only when all three are intentionally required.

| Need | Existing entry | Environment responsibility |
| --- | --- | --- |
| Feature work | local.dev.ready / local.dev.health / local.dev.verify_authority | sc-local-dev / sc_dev_demo, existing persistent synthetic Demo |
| Focused backend tests | local.dev.test MODULE=<declared module> TEST_TAGS=<nonzero targeted tag> | Serialize DB mutation, inspect actual test count; not executed as an extra blanket ORM run here |
| Explicit module upgrade | local.dev.upgrade MODULE=<affected module> | Snapshot first when required, validate actual module/schema identity |
| Frontend development | local.dev.frontend / local.dev.frontend.watch | Uses local environment, not a mixed local frontend/remote acceptance setup |
| Clean installation need | local.clean.health; local.clean.prepare / local.clean.rebuild only with governed confirmations | Existing sc-local-clean / sc_clean, no Demo or customer source; do not rebuild merely to check health |
| Optional technical sample | local.sample.* | Currently NOT prepared; no implicit remote pull or real-customer copy. Existing tools remain subject to source authorization |
| Cross-database mechanism work | Existing registered isolated rehearsal lane when actually needed | Not a permanent local replica of daily three-duty topology |

Literal env parsing intentionally rejects executable shell config. Do not reduce credential strength to bypass syntax checks; extend safe literal parsing with tests if a future managed credential representation requires it.

For linked worktrees, these existing env variables point at the primary checkout's credential authority. Health is read-only; operations that reconfigure running services must explicitly account for source mounts. Primary checkout remains owned by the daily-runtime executor. Do not silently remount persistent local services to another candidate. Local health is not runtime deployment revision attestation or customer product acceptance.

## Verification and boundaries

13 readiness/actual authority wiring tests; 36 existing lifecycle tests; 30 incremental planner tests passed. L1 passed. B independent review closed both the wrong-profile success defect and whitespace-export parsing bypass, and verified dependency mapping. Exact commands/original logs live in the run index.

No remote deployment, customer data transfer, global cleanup or mandatory sample provisioning. No frozen Quick or whole browser matrix was needed for this local batch. Mainline integration remains pending; use the isolated branch until integrated. Daily server and customer module work continue independently.

## Authorized mainline integration

Owner requested protected mainline integration after local completion. Finalization exposed one historical ledger record pointing at an ignored .runtime/pr file absent from clean linked checkouts. The original file is preserved byte-for-byte as docs/ops/iterations/daily_acceptance_lane_selfconsistency_original_record.md and its completed run points there; no historical validation is invented or rerun. Generated reports, exact-head Quick, independent review and remote required checks follow. Earlier not_run statements describe the local iteration stage, not the selected integration lane. No further database or remote application mutation is needed.
