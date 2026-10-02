# Contract Batches Mainline Integration — L4 Closure + SLO Telemetry (single PR)

Run: `.agent/runs/CONTRACT-BATCHES-MAINLINE-INTEGRATION/run.json`
Branch: `codex/contract-batches-integration` (from `fix/contract-slo-telemetry` head `aec885fac`, merged with `main`)
Baseline: `b1d8ff7acc85a8c93fea6746a701b0a2d1a766e7` (the merge commit)
Date: 2026-10-02

## Purpose

Two contract batches were complete but publication-held by the owner:

- **BACKEND-CONTRACT-L4-CLOSURE** (`fix/backend-contract-l4`, 5 commits): offline
  governance closure of the lifecycle runtime evidence. Its runtime lane was
  truthfully `not_run` because the registered isolated profile was absent at
  batch time.
- **BACKEND-CONTRACT-SLO-TELEMETRY** (`fix/contract-slo-telemetry`, 35 commits
  ahead of main, **containing the L4 branch entirely** — its baseline is the L4
  head `c2410190f`): SLO core, emission boundary, durable store, enforced
  retention cron, trend read model, published-version keying (owner topic b),
  catalog completeness (topic a) and snapshot seed/fixture hygiene (topic d),
  all closed with reusable receipts on the owner-authorized isolated profiles.

The owner released publication on 2026-10-02 and chose (AskUserQuestion, this
session): integrate **after the sibling session went still**, as a **single PR
covering both batches**, **re-running the L4 runtime lane inside this closeout**.

The sibling session finished topics a/b/d and parked on head `aec885fac`
(worktree clean, HEAD stable 3+ minutes; its remaining topics are explicitly
"owner authorization needed", i.e. parked awaiting the owner, not mid-work).

## Integration structure

- `codex/contract-batches-integration` created from `aec885fac` in a dedicated
  worktree (isolated from the sibling session's checkout), then `main` merged
  in. The only conflict was `.agent/active-runs.json`, resolved as the union of
  both sides' branch bindings. Everything else (64 files) auto-merged.
- The integration carries **no cherry-picking**: the PR diff is exactly the
  two batches plus this batch's realignment and records.

## L4 runtime lane re-run on the restored isolated profile

The registered profile `sc-contract-lifecycle-v1` (database
`sc_contract_lifecycle`, env file `.env.local.contract-lifecycle`) was stood up
by the SLO batch and was healthy at integration time. The lane was re-run at
the integration head with `ACCEPTANCE_TARGET_SHA=<head>`:

- probe: **14/14 assertions PASS** on `sc_contract_lifecycle`;
- schema guard: PASS with the artifact bound — `moduleVersion =
  manifestVersion = 17.0.1.1.14`, `sourceRevision` = the integration head,
  `database = sc_contract_lifecycle`;
- log `logs/contract_lifecycle_runtime_lane.log`, receipt
  `.runtime/agent-runs/CONTRACT-BATCHES-MAINLINE-INTEGRATION/lifecycle_runtime.json`.

### Evidence-chain disclosures

- The probe, the guard and the guard unit test are **byte-identical** to the L4
  batch's versions except for the realignment below; `ui_business.config.contract`
  is unchanged since the L4 head.
- `contract_lifecycle.py` differs from the L4 head only by the SLO topic (b)
  additive `publishedVersionRef` keying (19+/8−), which the authority gate
  re-verified at the integration head (score 100, `L4_governed_production_ready`).
- The container's mounted `addons/smart_core` is **identical** between the
  sibling worktree tree (`aec885fac`) and the integration head, so the exercised
  code is exactly the code under review.

## Lane identity realignment (the red the lane would not have survived)

The first lane run failed `module_version_current`: the probe and guard pinned
the expected module version as a frozen literal `17.0.1.1.9`, which silently
rotted when the SLO batch legitimately upgraded `smart_core` to `17.0.1.1.14`
(the installed DB and the manifest agree; only the pin lagged). A second latent
defect: the probe's `sourceRevision` fallback chain accepted the compose
placeholder `SC_SOURCE_REVISION=unknown`, so the guard would reject its own
artifact even with a correct head available.

Fix (commit `cb9fd5a86`), deriving every identity from its source of truth
instead of hand-synced literals:

- **probe** — expected module version is read from the mounted smart_core
  manifest on the Odoo addons path; `module_version_current` now means
  "installed == mounted source"; the artifact carries `manifestVersion` beside
  `moduleVersion` and moves to schema `1.1.0`; `sourceRevision` accepts only a
  full 40-hex SHA from its candidate chain, skipping placeholders.
- **guard** — `EXPECTED_MODULE_VERSION` is replaced by a manifest-derived
  value (fail-closed when the manifest is unreadable/versionless); the guard
  requires three-way agreement (artifact `moduleVersion` == artifact
  `manifestVersion` == validating tree's manifest).
- **unit suite** — fixtures derive from the same helper; new negatives:
  `manifestVersion` mismatch; the module/schema markers are dynamic.
- **make** — the lane target injects `CANDIDATE_GIT_HEAD=$(git rev-parse HEAD)`
  (whitelisted by `odoo_shell_exec.sh`) so the artifact binds to the head under
  test without caller setup.

Post-fix verification at the fixed head: guard unit suite **13 tests OK**
(including the new negatives), authority gate **PASS** (score 100,
`L4_governed_production_ready`, bundled suites), lane **14/14 + guard PASS**.

## Publication release

- The SLO batch's standing "Publication is on hold by owner instruction" is
  released: the owner instructed mainline integration on 2026-10-02 (this
  session). The L4 batch's "Publication is held by the owner; the remaining
  gate is the runtime lane re-run" is satisfied by the re-run above.
- Deployment, version release and the Gitee candidate dispatch remain separate,
  unauthorized steps (the RC6 candidate flow needs its own manifest and target);
  this integration only merges the code and evidence into `main`.

## Remaining (recorded, not blocking this PR)

- SLO topic (b)-residual: the runtime-attribution probe extension (publish one
  `ui.business.config.contract` row → deliver → assert attribution → restore);
  needs its own owner authorization and new fixture authority.
- SLO topic (c): signature-level supply-chain provenance and N-1/N+1
  compatibility drills (L5 items beyond this workstream).
- The 119 pre-existing snapshot-matrix reference diffs (staleness vs the
  2026-08-24 regeneration) remain an owner decision, unchanged by topic (b).

## Status

- Integration branch frozen at the lane-fixed head; exact-head quick gate and
  the PR workflow results are recorded in the run completion once merged.
