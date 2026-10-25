# Quick incremental execution

Formal Product Layer / Layer Target: P4 standard delivery tooling. Module: local Quick runner and input declarations. No P0–P3 semantics or database/deployment changes.

Owner explicitly assigned all four inherited dirty files on 2026-10-25. The previous P4 classification candidate 1d58ebf228b786e62752d5341a63de1126e8cfe0 already merged via PR #729. This continuation retains that branch and registers a distinct result.

Inherited defects: unverified ancestor receipt, incomplete inferred inputs, current recipes used for historical fingerprints, absent scan handshake, incompatible receipt keys, linked-worktree authority bypass, primary sharded entry not using the planner.

Validation starts at L1/L2: focused input-scope and receipt tests, existing runner regression tests, iteration guards. Runtime L3/L4 journeys are excluded because this changes offline validation only. Final Quick and publication checks remain required. Unknown input scopes stay executable; inferred script references alone never authorize reuse.

Rollback: revert only this batch and retain original evidence; no runtime data changes. Status: active, not integrated or deployed.

## Implementation and first validation

The common evidence_scope planner receives only complete reviewed units. Initially, two offline tool-test targets may reuse; unknown scopes still run. Their inputs include all scripts and Make fragments, the Makefile, tracked path existence, Python executable/version and a non-disclosing environment digest. Historical fingerprints read historical Git blobs. Source receipts require exact schema/suite/producer/tree, valid scan coverage, ancestry, and a receipt-bound scope sidecar captured by the original successful runner. Legacy receipts still verify normally but cannot supply target reuse without that sidecar.

Incremental runs retain all scan proofs, clean-head checks, generated-evidence preflight, serial Make ordering and governed local.dev authority. Primary and linked entrypoints use the same planner. Standard receipt schema remains unchanged; optimization metadata is separate and cannot replace a receipt.

L1 ci.local.iteration passed. Initial scoped tests: 6 input-scope + 12 receipt tests passed. Existing wrapper regression exposed a pre-existing stale string assertion: HEAD already includes shard/compose targets between Quick and generated preflight in .NOTPARALLEL. Updated the test to assert both required memberships, without changing the Make behavior. Original failure: .runtime/quick-incremental-execution/regression.log.

## Final scoped validation

- Input scopes: 6 tests; incremental execution/receipt/shard composition: 13 tests.
- Existing atomic Quick regression: 63 tests; branch governance: 23 tests.
- Registered local.dev wrapper: 15 tests, including subset injection refusal and preserved authority.
- Logs: `.runtime/quick-incremental-execution/sharded-regression.log`, `wrapper-regression-fixed.log`, `iteration.log`.
- Primary execution retains bounded concurrent shards. Part receipts cover only actually executed targets; composition independently revalidates the source receipt and exact reused set before requiring executed + reused = full manifest. Losing a reuse proof blocks composition.
- Complete input declarations currently cover two tool tests. There is no claim of 128-target reuse or measured whole-lane speedup. Other targets retain original execution and scanner-level governed reuse.
- Governed generated test inventory adds one file; subsequent stable sequential row IDs shift. No manual inventory edits.

Implementation and scoped tests complete; exact-head Quick and independent review remain final gates. No external publication or product deployment has occurred.

## Independent review and squash-history normalization

Candidate 31f840e3aadc4ecb681df6730916976fb6d2789d passed full Quick and independent read-only review with no S0–S2 findings. Publication preflight found the prior squash history left a conflict in the run index. A new delivery branch `fix/quick-incremental-execution` preserves the original source branch and uses the existing `workspace.branch.sync-main` dependency mode, bound to merged PR #729 and main 0efb7533120580fe180bc20ee6f952332cea1bf3. The governed tool verified a recovery bundle, responsibility patch identity and a byte-identical tree before/after replay; no product/tool implementation changed.

The run baseline is now the actual main ancestor. Unchanged scoped tests and review findings are retained with their original logs. Final Quick and final review identity are bound to the normalized candidate before publication; original receipts are not copied or relabelled. See `.runtime/quick-incremental-execution/sync-main.log` and final handoff for actual outcomes.
