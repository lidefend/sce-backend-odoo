# VERIFY-SYSTEM-CLOSEOUT-01 / R2-A

P4 standard CI/verification tooling. Baseline `bfc954c0b6fe2bbaa5a94c017ef8c69ec983d9a5`. Owner authorized F02 → F01 → F03 only; no product changes, database writes, R2-B/C, main full dispatch, merge or deployment.

R1 failure evidence remains immutable in Draft PR #1020. Local scope: unit + real CLI/Make negative and recovery tests. PR scope: new exact HEAD required checks. R3 full main qualification excluded until separate review.

## Implementation boundaries

- F02 authenticates the current authoritative dispatch run, attempt jobs and artifact bytes. It compares the formal release condition with the manifest, derives full suite responsibility from the exact source, verifies each shard's receipt/log/count and mandatory runner kind, and rechecks main immediately before issuing PASS. Missing proof denies qualification; it does not dispatch replacement workflows.
- F01 uses one environment identity contract for aggregate and individual recovery. The default producer observes local executable bytes, installed dependency manifests and Python package records. Governed runtime checks additionally bind their declared environment and readback bytes. Host identity is not a database or browser-state witness; existing non-reusable-target controls remain. Ordinary content reuse may cross runs, while channel handoff remains bound to its run and channel. The aggregate index schema changes to 3; old evidence is retained but cannot authorize new aggregate reuse.
- F03 prints all six observed states and gives terminal failure precedence over pending. Only pending runs are polled again, while final provenance verification re-reads every run to detect reruns. Waiting budgets are unchanged.

SELECTED, DISPATCHED, EXECUTED, PASSED and REUSABLE remain distinct. The planner report is selection evidence only. Real CLI tests use controlled GitHub transports and isolated artifact fixtures, not a dispatched main audit; real Make/SIGINT recovery uses disposable local test producers, not mixed ORM/browser execution.

## Preserved pre-fix evidence

R1 original evidence commit: `83cc97f93bdf17757e744109fbac1e2e3b88db7c`; reviewed scope corrections: `da210fed05739d9565f5ad1be84ab113cd62cde9`, PR #1020. Its immutable `docs/audit/verify_system_closeout_01/evidence/` and matrices remain on the audit branch. This repair branch does not rewrite or copy those results into new successful receipts.

## Local validation

The affected planner selects seven local tool/registry checks and no local ORM or full browser matrix. New CLI coverage is registered through the existing scheduled-gate target; environment regression is part of the existing incremental executor unit target. The generated coverage snapshot is updated through `make test.coverage.registry.export`, with no baseline relaxation. Initial failed/obsolete development runs are retained under `.runtime/verify-system-closeout-01-r2a/` and are not passing evidence.

New exact-HEAD PR CI remains required. Mainline qualification, product acceptance and deployment qualification remain NOT_VERIFIED by this batch. R2-B/F04/F05, R2-C historical debt and R3 dispatch remain outside authorization.

`make ci.local.iteration` PASSED: seven selected targets executed, zero reused. The executor suite ran 286 tests; the qualification CLI suite ran four tests containing 16 independently asserted denial cases, a full evidence positive, main advancement, pending completion, and terminal-failure precedence. Immutable raw target logs, receipt and tested-input hashes: [evidence manifest](../../audit/verify_system_closeout_01_r2a/evidence.json). Nested runner counts remain in raw logs and are not inflated into a fabricated aggregate. Remote PR CI is still pending publication.


## F02 execution-fact follow-up

The first repair candidate `196673db5422a7e2d852dd51bf420c89d67c0524` still accepted an authenticated full plan whose ORM receipt selected only `sc_smoke/<module>`. The real CLI replay of that exact verifier returned PASS; preserved [counterexample](../../audit/verify_system_closeout_01_r2a/execution_facts_before.json) and original output are not superseded by its green CI checks. This is a qualification-tool defect, not an observed product test failure.

The follow-up requires the actual full-module selector without exclusions, the exact test-source blob inventory and whole-tree binding, Python observation matching its recorded environment, and content-bound runtime images/services (or the existing isolated-Python authority). New negative fixtures retain valid outer artifact and inner file hashes, so refusal must come from the missing execution facts rather than a trivial digest mismatch. All checks continue to use the native receipt producer and runner responsibilities.

The registered offline task now names its actual aggregate owner `verify.ci.scheduled_gates`; its real CLI tests are reached through Make dependencies. This permits valid same-input reuse after committing, while preserving unknown/runtime target refusal. Remote PR closure remains the existing repository policy, including full product/demo/acceptance suites for `make/ci.mk` changes; no remote scope policy is changed here.

Follow-up `make ci.local.iteration` PASSED with seven targets executed and no reuse. The CLI suite now has five tests with 20 independently asserted denial cases; the executor remains 286 tests. [Follow-up evidence](../../audit/verify_system_closeout_01_r2a/execution_facts_followup.json) preserves all new logs without overwriting the first run. Ten actual ORM receipts from PR run `45944804108` also pass the execution-fact validator; that bounded producer-format readback is explicitly not a current-main qualification.

## PR #1022 independent-review corrections

The reviewed source is `7be328ae0fb987fc3a23c91bf49440ee12b71bbc`. Changes remain limited to RH018 evidence encoding and F02-01 operator source identity. Dispatch and verification both require the exact local HEAD/tree, a clean checkout and the expected remote main; dispatch rechecks before each external dispatch and verification rechecks before signing. Existing qualification, environment and terminal-failure protections remain intact.

The real CLI test uses a disposable clean Git checkout of the current tracked implementation. A distinct clean commit with the same tree is denied by both CLI entrypoints; an untracked source modification is also denied. Git HEAD/tree/status are real; only GitHub/remote transport is controlled. This is isolated tool verification, not mainline workflow dispatch.

RH018 matched ten `results[].artifact_id` fields (three distinct technical identifiers), not personal information. Technical IDs now use reversible `0x` encoding; the original serialization and source SHA-256 allow exact byte reconstruction. Artifact digests and historical result identities remain unchanged. The unmodified scanner also confirms the original blob remains reachable in candidate history. Appending a correction cannot clear that historical hit. Repository delivery rules prohibit force pushes, so publication awaits a decision on a clean replacement candidate while preserving #1022 and its failed runs. No scanner exception or history rewrite was performed.

[Correction evidence](../../audit/verify_system_closeout_01_r2a/review_corrections.json) records input hashes, the original blob, affected fields and validation status. New exact-HEAD CI and R3 mainline qualification remain unverified.

## Authorized clean replacement

Owner approved a new Draft PR from authoritative `origin/main`, preserving #1022 unchanged. Baseline remains `bfc954c0b6fe2bbaa5a94c017ef8c69ec983d9a5`; replacement branch is `fix/verify-system-closeout-01-r2a-clean-20261127`. The prior corrected working tree was preserved in stash `217ed271f1719a1470b33b9c723441b78e07cae9`; file content is transplanted, not historical commits. No scanner rules, exemptions or Git history are rewritten. The source comparison records exact hashes of the final #1022 implementation, including its reviewed corrections. Historical logs remain historical evidence; the replacement must earn its own tests, exact-HEAD local receipt and remote CI. Full history scanning is performed in an isolated non-shallow checkout of only the replacement branch so preserved unrelated branches are not confused with candidate ancestry.
