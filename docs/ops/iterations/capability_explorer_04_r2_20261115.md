# CAPABILITY-EXPLORER-04-R2

## Scope

This round only hardens incremental checkpoint evidence selection. Product
runtime, Explorer Handlers, Intents, permissions, browser behavior and Quick
policy are frozen.

## Baseline

- Branch: `audit/platform-capability-studio-01-20261115`
- Full SHA: `a6c3fc6711df993989a2ab94a27738d47fbfb35a`
- Previous independent review: checkpoint receipt closure is S2.

## Required Change

An incremental receipt may become a checkpoint only when:

- schema, mode, status and clean identity are valid;
- its commit is a descendant of the run baseline and ancestor of current HEAD;
- commit tree matches the receipt identity;
- `requiredTargets`, `targetResults` and `notRunTargets` close without gaps or duplicates;
- every target result passed with a verifiable log digest;
- the checkpoint chain does not cross an unverified commit.

Any failure returns planning to the registered `run.baseline_sha`.

## Verification

Implemented:

- incremental execution identity now records both commit tree and runtime tree;
- checkpoint receipts require the exact execution schema and mode;
- required targets, target order, result order and not-run targets must close;
- changed paths must equal the committed diff from the declared checkpoint;
- every target result must pass with a safe, matching log digest;
- checkpoint parents are recursively verified back to the R2 run baseline;
- empty, forged, incomplete, tree-mismatched and broken-chain receipts fall back
  to `run.baseline_sha`.

Checks:

- `verify.frontend.dev.incremental.unit`: PASS, 152 tests, including positive
  checkpoint tests and negative empty/result/forgery/not-run/broken-chain cases.
- `ci.local.iteration`: PASS, 3 affected targets.
- `ci.local.quick.full`: pending.
- Remote CI on the new SHA: pending.
