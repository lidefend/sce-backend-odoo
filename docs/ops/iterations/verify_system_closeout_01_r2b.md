# R2-B: execution and coverage integrity

Baseline `d79dd2caa58f7e2aa7ab17a88fa80df2fc3e266c`. Owner resumed CI closeout after business lines completed. P4 only; no deployment.

#1027 post-merge four workflows all succeeded at `0d17e91e7190e1a293e4e6ac969c39738a87218f`; this is historical regression closure, not current-main qualification.

F04 and F05 remain in current source. R2-C historic asset/producer debt stays separate. R3 cannot yet succeed while retained #1022 history is included in the all-ref audit; current RH018 reproduction preserved under `.runtime/verify-system-closeout-resume-20261128/history-blocker.txt`. No rule exception or history deletion is authorized.

## Current repair and limits

Real Node TAP repro: two independent runner failures (plain command and pipeline) were hidden before repair; both now fail the Make target. Explicitly handled negative runner remains legal; existing nested unittest/TAP summaries retain their authority. Executor uses the repository's Bash errexit/nounset/pipefail policy even for isolated Makefiles and recursive Make. This proves recipe/pipeline exit propagation; arbitrary child programs which intentionally suppress their own errors still require their owning runner contract. No generic log-word scanning was added.

Route-lease producer and core dependency now select the existing native Make test. The regression executes that real Make target. Environment recovery fixture now declares the absent optional block flag as 0 under nounset; no assertion removed.

The historical 84 unselected edges were re-evaluated at current source: 3 directly selected, 81 not proven by static Make closure. This is a bounded unresolved coverage inventory, not 81 proven missed product tests; actual ownership/dynamic aggregation belongs to continued R2-B coverage review and R2-C debt disposition. Raw comparison remains in `.runtime/verify-system-closeout-resume-20261128/coverage84.json`. No broad ORM/browser selection was introduced.

## Current owner-trace result

All 84 original producer paths still exist and have actual Make recipes. They map to 77 distinct owners, including existing aggregates. The planner now declares their original owners; the broad release aggregate delegates its unchanged tool-test recipe to `verify.frontend.release_tools.unit`, preserving complete-lane coverage without dragging its full prerequisite graph into local tool-only changes. Fifteen zero-reference dispositions became stale after genuine wiring and were removed without baseline expansion.

The actual 77-owner execution found six failed targets. One is the known scan-memory fixture fixed in #1037. The remaining issues were Node's default non-TAP reporter, extensionless TypeScript imports in the raw Node harness, a new real ScRichText SFC dependency plus missing float digits in the layout fixture, a copied old lane-name list, and old canonical policy call sites in a static guard. These were corrected in test/tool ownership; production business code is unchanged. The broad release aggregate recheck was interrupted once its excessive prerequisite scope was confirmed; it is not marked PASS. Its original tool-test recipe passed through the new focused target.

Final executor regression: 298 tests passed (`.runtime/verify-system-closeout-resume-20261128/r2b-final-unit.log`). Earlier failed logs and the interrupted aggregate remain intact.

Owner's latest instruction: keep #1037 Draft and close this topic within that PR. Transfer this independently scoped commit to the #1037 branch, retain separate evidence, then validate the combined candidate. No merge, deployment, or R3 main qualification is authorized by a PR-green status.
