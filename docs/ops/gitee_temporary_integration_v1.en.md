# Temporary Gitee integration during the GitHub outage

[中文](gitee_temporary_integration_v1.md)

The owner's 2026-09-23 request authorizes this P4 workflow adjustment, not a permanent repository move.
Keep `origin` on GitHub and `gitee-mirror` at `git@gitee.com:leegege/sce-product-odoo.git`.
The older Gitee webhook document describes a historical deployment; verify its current operation separately.

## Observed baseline and order

GitHub returns HTTP 403 (account suspended). The `pr.status` wrapper's zero exit is not a pass.
Gitee main `b9e3e56a80c02c1eb277d2ac573e10286c4cd8e8` is 133 commits behind, and an ancestor of,
historical local main `de9a230d3faab18dd60a219f445f932a8af9d7f5`.
Header candidate `22390c84f7d2447e055b6e1c67a194778ce9a10a` and stability candidate
`baad61f12e6a7fff0e5b9953609be5f5d52fbdff` remain unmerged and share modified paths. Integrate serially.

1. Run inspection and catchup dry-run from an allowed controller branch.
2. Obtain owner authorization for the exact historical catchup, then fast-forward Gitee main.
3. Complete existing L0–L5, exact-head Quick, independent review and external evidence archival for new candidates.
4. Publish the candidate through `pr.push.gitee`, then open a same-repository Gitee PR with exact source/base SHAs.
5. Verify actual webhook/worker runs, exact SHA, nonzero tests and readable logs. Push-only public guards do not
   replace PR professional gates. Missing equivalents of required checks remain blockers.
6. After owner approval of the merge method, use the protected Gitee PR workflow. Recheck head/base immediately
   before merge. If the platform cannot bind the reviewed head, stop; do not use the historical fixed-head bot
   or direct push. Current merge capability is not yet accepted.

## Entries

```bash
make verify.gitee.integration.unit
make gitee.integration.inspect EXPECTED_HEAD=<full-head> GITEE_EXPECTED_MAIN=<live-main>
make main.gitee.catchup EXPECTED_HEAD=<full-head> GITEE_EXPECTED_MAIN=<live-main>
# Only after owner approval of this exact historical write:
# APPLY=1 GITEE_INTEGRATION_CONFIRM=FAST_FORWARD_HISTORICAL_GITEE_MAIN
make pr.push.gitee EXPECTED_HEAD=<frozen-head> GITEE_EXPECTED_MAIN=<aligned-live-main>
# After review and archival:
# APPLY=1 GITEE_INTEGRATION_CONFIRM=PUBLISH_EXACT_GITEE_CANDIDATE
```

Defaults do not write remotely. Catchup only publishes the fixed historical main, checks both local anchors,
proves ancestry, and creates/verifies a bundle under the common Git directory's
`codex-recovery/gitee-temporary-integration/`. This preserves an observed historical baseline; it does not
prove the current inaccessible GitHub state. Candidate publication requires clean exact HEAD, a valid Quick
receipt and read-only generated-evidence preflight. Ordinary server-side fast-forward checks remain enabled.
No force/lease, protection changes, branch deletion or deployment. A remote can still move between checks and
push: the server rejects non-fast-forwards and success requires readback. Inspect before retrying a failed push.

## Exit and recovery

After GitHub recovers, inspect both live main identities and review the Gitee additions before authorized,
governed synchronization. Divergence requires a separate decision; never automatically overwrite either side.
Disable this lane after recovery. Existing reverse-mirror services were not changed and must be inspected before
an actual cutover. Product rollback uses a separately reviewed revert PR; historical catchup never rewrites history.

Local tool tests do not prove catchup, publication, Gitee CI, merge, GitHub recovery, deployment or user acceptance.
Record these independently. This tool deliberately has no general PR merge or remote rollback action.


## Acceptance correction (2026-09-23)

The channel remains blocked. The installed reverse-mirror timer is enabled and runs every minute;
its script still targets `Leedefend/sce-product-odoo`, unlike the locally disabled script.
Before any remote write, resolve automation side effects and establish a governed single-writer window.
Ordinary fast-forward push is not compare-and-swap against the previously observed remote SHA:
an intermediate ancestor advancement can still be accepted. Never relax branch protection.
Push errors or readback failures now return `status=uncertain`, `retry_allowed=false`, exit 3.
Inspect the remote before recovery; do not retry blindly. Recovery bundles must contain the exact historical main.
Formal PR merge requires atomic binding of both reviewed source HEAD and target main, or a proven equivalent lock.
The existing bot and the documented public merge endpoint do not provide that proof.
See the living batch record for the gate mapping, read-only automation audit and remaining blockers.
No remote writes, service changes, catchup, merge or deployment were performed in this acceptance step.


Current bounded verdict: **not implementable with available evidence**. Defer complete CI migration.
Gitee is provisionally for historical mirroring/candidate storage, with writes still blocked pending
complete automation isolation and publication safeguards. The living batch record contains the exact
isolation execution sheet and recovery plan. Service changes and remote writes require separate
reviewed authorization; historical catchup remains paused.


Automatic CI preparation is now independent of formal merge feasibility. Use the existing worker
for first minimal acceptance; the full gate migration remains separate. Platform side effects must
be resolved before any push. Historical main catchup is not a checkout dependency, but current
publication enforces it; an explicit governed CI-only mode must be implemented and tested in the
same entrypoint before independent publication. No bypass or remote write is authorized here.


## Implemented local CI-only mode; remote writes remain disabled

Explicit GITEE_CI_MODE=ci-only routes the existing receiver/worker to an independent acceptance table.
Only the fixed repository, candidate branch and full Push SHA are accepted. Legacy remains the default.
The server-owned checker runs the same unittest suite as verify.gitee.integration.unit, collecting
actual testsRun minus skipped, rather than invoking candidate-controlled Make recipes or hardcoding a count.
The parent checks out exact SHA, then bubblewrap isolates network, PID and filesystem with no credential,
mirror or deployment mounts. Missing sandbox capability is an environment error, never an unsandboxed fallback.
Timeout/cancellation kills and waits for processes, including detached sandbox descendants. Workspaces are
removed before identity-bound receipts are persisted. Query terminal state by exact SHA; duplicate jobs
are not rerun, and old results never become new-SHA results. This does not certify malicious test assertions;
the same-repository candidate and its tests still require review.

pr.push.gitee accepts GITEE_PUBLICATION_PURPOSE=ci-only for read-only previews without historical main catchup.
It reports all commits and paths relative to observed main, possible additional visible code, and exclusion
of dirty changes. Apply remains hard-denied pending real platform isolation evidence; no boolean bypass.
Default integration constraints are unchanged. Installation packaging includes new modules but does not
enable the mode. No online installation or configuration was performed.
