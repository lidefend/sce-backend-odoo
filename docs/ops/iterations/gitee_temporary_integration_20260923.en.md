# Workspace takeover and temporary Gitee integration result index

[中文](gitee_temporary_integration_20260923.md)

## Desktop execution update

Quick at `2f7d58fb` stopped on duplicate customer identifiers in the publication scanner (P4 tool defect,
not leaked customer payload). The scanner now imports authoritative `CUSTOMER_IDENTITY_TOKENS`, without
adding exemptions. Focused scan tests (5) and boundary tests (10+11) pass. The final publication scope is
rescanned with the updated rule source; unchanged online executor modules are not reinstalled.

Incremental installation at `1feb780b95e910c905fb4d95ed7447f40db7ef0b` succeeded after the
bounded upstream AppArmor profile repair. Backup: `incremental-s0g_x39h`; receiver/worker active
in CI-only mode. The user saved the new webhook signing secret; the governed server rotation
succeeded with backup `secret-rotation-itahha8l`. No secret values enter source or evidence.
The CI-only publication change binds a reviewed one-hour platform receipt to candidate/main,
public-scope evidence hashes and current online files/isolation. Clean, Quick, generated evidence
and remote readback remain mandatory. Targeted publication/receipt tests passed: 42 + 10.
The trusted online harness executes the same unittest module directly, not the Make wrapper;
do not claim the wrapper ran. Clone and execution share 120 seconds. Final frozen receipts and
actual CI results belong in existing artifacts. Main catchup, merge and product deployment stay excluded.

Controller: `fix/gitee-temporary-integration-v1`, HEAD/base
`de9a230d3faab18dd60a219f445f932a8af9d7f5`. This is dirty development work, not a frozen candidate.
Owner authorized workspace takeover, closure before iteration, and adjustment for restricted GitHub access.
P4 owns Git publication/catchup tooling, Make entries and governance records. No P0–P3 semantics, database,
environment, origin URL, forced push, automatic merge or deployment changes. Remote APPLY is high-risk and
requires exact identity, clean state, ancestry, recovery and readback. Existing publication/sync entries retain semantics.

## Preserved state

- Original main was clean; its ref remains unchanged after creating the controller branch.
- Stability worktree `sce-backend-odoo-uc4-g10-engineering-process-native-v1` remains clean at
  `baad61f12e6a7fff0e5b9953609be5f5d52fbdff`, 123 commits beyond main.
- Header topic `22390c84f7d2447e055b6e1c67a194778ce9a10a` has 29 commits beyond main. Historical PR #522
  cannot currently be verified remotely. Both topics share four paths and require serial integration.
- 31 local branches retained, no stash ref or Git lock observed. No blanket deletion or claim all are merged.
- Persistent/sample/clean environments passed governed health checks and remain running.
- Orphan candidate process 709450, old material worktree SHA `25cb3cd106ead9dd09b3f2b68ed152fbd413da0f`,
  was stopped through governed down after supplying exact controller SHA and confirmation. Initial missing-input
  refusal made no change; the subsequent process identity check passed. PID file removed, no database mutation.

## Results and original evidence

- GitHub `make pr.status`: HTTP 403 account suspended; wrapper exit zero is not success.
- Stability exact-head Quick receipt verified, not rerun. L1 style/bridge/navigation targets passed at baad61f1:
  129 bridge checks, 262 self-checks, 85 navigation leaves across four roles. Original log is
  `artifacts/workspace-takeover-20260923/l1.log` in that worktree. No independent/runtime acceptance claim.
- New lane `make ci.local.iteration`: passed, 16 policy tests, dirty L1-only result;
  `artifacts/gitee-temporary-integration/l1.log`.
- First L2: 27 tests, one failure; missing remote ref after push lacked explicit readback-stage context. Fixed in P4.
  Second L2: three fixture errors because a boolean shadowed the new method; fixture renamed.
- Final `make verify.gitee.integration.unit`: passed, 27 tests;
  `artifacts/gitee-temporary-integration/l2.log`. Covers zero-write refusals, exact refspec, bundle check and failed readback.
- Live inspect: passed, zero writes, Gitee main b9e3e56a, 133 commits ahead; `inspect.json` in the same directory.
- Historical catchup dry-run: fixed target de9a230d, `catchup-plan.json`; not authorization to execute.
- Gitee CI server status: receiver/worker active, health ok, systemd reports disk configuration differs from loaded units;
  `gitee-ci-status.log`. No restart/reload, candidate check equivalence not established.

The readback fix only changes the new script and fixture; targeted tests plus syntax/diff checks cover it.
Policy, Make recipes and environment inputs remain unchanged, so carry forward their L1 result.
No module/runtime load change requires L3 upgrade. No product page change requires an L4 browser matrix.
L5 remains not_run: uncommitted candidate, no independent review, final Quick, archive or publication.

## Next boundary

Review the exact historical catchup b9e3e56a→de9a230d (133 commits, proven ancestry) and obtain owner approval;
recheck identity at execution. It includes neither unmerged topic nor this uncommitted tooling.
Verify Gitee gate equivalence, protected exact-head PR merge and reverse-mirror service state before actual cutover.
Do not reuse the fixed historical PR bot. GitHub recovery synchronization and local main synchronization from Gitee
require governed closure; existing `main.sync` still uses GitHub.

Batch verification_pending; mainline integration, deployment and user acceptance not_run.
The 89-entry objective remains queued; 86/89 historical report associations are not business acceptance.
Rollback uncommitted owned files only. Preserve frozen topics. A completed historical fast-forward is not reversed
by rewriting remote history; retain its recovery bundle and use reviewed PRs for product rollback.


## Acceptance steps 1–3, 2026-09-23

Same baseline and owned dirty scope; no remote write, service mutation, commit or freeze.
The detailed gate-by-gate mapping is maintained in the [Chinese section of this same record](gitee_temporary_integration_20260923.md).
Raw evidence remains under `artifacts/gitee-temporary-integration/`, with no second reporting system.

| Requirement | Observed Gitee behavior / evidence | Remaining gap |
| --- | --- | --- |
| Public Guard | Installed runner matches local code; two history/security test suites and legacy scans | Missing current risk/workflow/merge/candidate/evidence checks |
| Professional Quality | PR runs unlocked dependency install and legacy `make ci`; Push skips | Not equivalent to current risk-routed workflow or governed module shards |
| Frontend Release | No separate current release workflow execution | Toolchain, locked install, lint/typecheck/test/build/release coverage unproven |
| Merge Policy | No equivalent aggregation or check-runs reporting | Missing |
| Failure / zero tests | Nonzero exit fails queue; zero exit alone passes | Zero-test rejection absent |
| Timeout / cancellation | No subprocess timeout, service runtime infinite, no cancellation protocol | Terminal-state behavior unproven |
| Evidence integrity | PASS file written before mirror handoff; stale file not cleared | File can outlive a failed execution; cannot authorize merge |
| Candidate binding | Exact detached SHA checked; queue keyed by SHA | No base/latest PR head binding or old-result invalidation |
| Protected main | SSH cannot show enforcement; no registered read-only API credential supplied | Required checks, bypasses and platform hooks unproven |
| Frozen local delivery | Local publication checks Quick/generated evidence | Current dirty candidate has no L5 evidence |

`live-audit.json` captured UTC 03:30:47: receiver PID 2309968 and worker PID 2309973 started
July 20; installed scripts match repository scripts, but installation has no Git metadata and
no in-memory code attestation was performed. `live-queue-automation.json` records safe process
configuration and read-only SQLite facts. Owner `leegege` is accepted for Push/PR, with PR also
allowing `sce-ci-bot`. Current remote main's historical Push job failed with exit 2; historical
successes are not candidate evidence.

`automation-state.log` confirms the reverse timer enabled/active every minute and the old
GitHub Actions runner enabled/running. The installed mirror targets `Leedefend/sce-product-odoo`;
local source is disabled, installed source is not. The worker hands successful main Push jobs
to the mirror source repository. A failed recent mirror invocation is not deactivation.
Scoped host scanning found no separate merge/deploy service, but platform-side automation remains
unknown. Proposed governed pause: preserve selected nonsecret configuration, stop/disable the exact
mirror timer and stop its service, verify inactive/disabled/no live writer, retain CI/data, then
resolve platform writers and reserve a single-writer window. Re-enable only after reconciling
source and both remote SHAs under separate authorization. Nothing was stopped or reloaded.

Exact merge is blocked: the old bot performs GET then PUT without source/base CAS. Official
[Open API 5.4.93](https://gitee.com/api/v5/swagger_doc), saved as `api-swagger_doc.json`, exposes
no expected source/base parameters on PUT merge. This is absence of proof for the inspected
mechanisms, not a claim about every Gitee product. No equivalent lock has been validated.

P4 changes distinguish attempted-push uncertainty (exit 3, retry_allowed=false), verify the
bundle's historical SHA and recheck controller branch identity. Targeted tests now pass **36**
cases (`l2-acceptance.log`, 0.180s test body, about 2s command), including actual local Git proving
that intermediate fast-forward drift may be accepted while divergence is rejected, existing
branch publication, main drift after preflight, accepted-write timeout and read-only recovery.
Prior L1 policy results carry forward because their inputs are unchanged; syntax and whitespace
checks pass for the revised scripts. No module/browser scope: L3/L4 skipped. Known integration
blockers keep L5 preparation, Quick and freezing not_run.

Latest read-only catchup preview (`catchup-plan-acceptance.json`) still targets exactly
b9e3e56a→de9a230d, applied=false. Clean controller, verified recovery bundle, automation isolation
and precise execution authorization are not all available. Two product topics remain untouched.
Batch verification_pending; mainline integration, deployment and user acceptance not performed.


## Isolation preparation and bounded merge feasibility decision

Verdict: **currently not implementable with the available mechanisms and evidence**.
Native merge has no proven atomic source/base conditions; equivalent locking lacks both remote
configuration covering all writers (including administrator bypass) and race/recovery validation.
This closes this investigation; no further interface search or full CI rebuild is scheduled.
Gitee is provisionally a historical mirror/candidate storage channel, still blocked from writes
until automation isolation and publication safeguards are satisfied.

The [same record's Chinese execution sheet](gitee_temporary_integration_20260923.md) identifies
exact objects, impact, pause/verify/restore requirements and unknown platform paths. New raw evidence
`isolation-readonly.json` was captured at 2026-09-23 03:39:03 UTC. Its initial read-only parser failed
on the runner registration BOM; decoding with utf-8-sig resolved that tooling issue without mutation.
The mirror timer remains enabled; mirror service PID is 0 at sampling. The CI queue has no pending
or running jobs; mirror source main is aaad9e06d5e0d70d92041b65b8a4ae9003fb7cda.
Runner agentId 2, ci-1-95-2-123, pool Default is registered to
https://github.com/Leedefend/sce-product-odoo, rooted at /opt/actions-runner.
No Runner.Worker process was observed, but that does not prove no queued jobs or authorize stopping it.
It remains untouched. Platform hook IDs, other integrations, permissions, bypasses and deployment
jobs remain unknown without registered read-only platform access, and block all remote writes.

No safe pause/restore Make entry exists yet. The proposed bounded P4 extension must capture original
configuration, bind exact host/unit/hook, refuse active or unknown tasks, verify no remaining writers
and restore only its own changes after checking queued work and exact remote SHAs. Existing install,
seed, run and repository.configure commands are not isolation substitutes. Candidate CI can execute
repository code; isolate admission and worker too unless its external-write capability is proven absent.
Do not stop the old GitHub runner without confirming ownership, active/queued tasks and separate authorization.

Prepared but unexecuted merge validation covers source/base drift during the merge window, every
writer class, partial lock failure, crash/timeout and safe restoration. Remote mutation authorization
is separate. Remaining P4 design covers governed isolation tools and publication prerequisites;
CI design covers structured nonzero test counts, bounded attempts/cancellation, terminal receipts,
complete required-check reporting, stale source/base invalidation, and uniform checkout/log/result identity.
Each has negative tests and closure conditions in the execution sheet. Legacy make ci is not equivalence proof.

This iteration changed documentation/goal only. Original 36 tests are retained, not rerun; source and
Make inputs are unchanged. Documentation whitespace validation applies; no runtime/browser/freeze/Quick.
Candidate stays dirty; both product topics are unchanged. Batch verification_pending; no mainline
integration, deployment or user acceptance. Historical catchup remains paused with separate exact-range authorization.


## Automatic CI preparation: separate from formal merge

The latest scope removes exact merge feasibility from CI prerequisites. Local work may continue;
remote pushes await complete side-effect evidence; formal merge remains blocked; deployment is excluded.
The detailed four-part preparation is in the same Chinese batch record, not a second report.

1. **Push side effects remain incomplete.** Registered read-only Gitee credentials/configuration exports
were requested. Missing evidence: all hook IDs/events/enabled state/target purpose, Go pipelines and
triggers/running jobs, members and inherited/admin bypass permissions, writable keys, bots/apps,
deployment integrations. Do not infer absence from lack of access. Existing receiver accepts Push
without a ref restriction; runner handoff depends on SHA equalling live main, not the branch name.
PR invokes legacy make ci; tag delivery cannot be excluded by local configuration intent. Mirror and
old runner disposition stay unchanged. No secret values or sensitive URL parameters are reported.
2. **Choose the existing worker for the first minimal acceptance.** Gitee Go activation, repository
permissions, quotas/concurrency/timeouts, execution images and credential isolation are unknown.
Public official descriptions are not tenant evidence, so lower integration cost is unproven.
Read-only `ci-executor-readonly.json` confirms host Python 3.12.3, Git 2.43.0 and Make 4.3, sufficient
for the chosen pure tests; additional Node/pnpm/Docker CLI availability does not prove worker access
or full gate compatibility. No Go pipeline creation, run or purchase; no duplicate implementation.
3. **Concrete first acceptance:** real Push WebHook on the single registered P4 candidate branch,
full frozen H, runs `ENV=test make verify.gitee.integration.unit` (currently 36 tests using mocks and
local temporary Git repositories, no business data). Governed server-owned acceptance cases separately
exercise deliberate unittest failure, empty suite rejection, timeout, exact-attempt cancellation and
H2 not inheriting H1 success. Use structured test counts, independent attempts/logs/receipts and trusted
status generation. Expected negative-case failures remain failures; only the acceptance summary may
pass. Readable governed status plus original logs can validate this first chain, not required-check
merge enforcement. Normal deadline proposed at 120s with 5s termination grace; negative timeout case
uses a short controlled deadline. No product source sabotage, PR creation or main/tag push.
4. **Remaining changes and recovery:** retain one worker, add bounded acceptance mode/ref filters,
attempt/count/terminal states and isolate candidate execution from receiver/status secrets and mirror
writes. All online installation/isolation changes require separately reviewed authorization and exact
configuration backups. Platform IDs remain unknown, so no executable hook/Go changes can yet be issued.
Keep queues/logs on failure; block admission, do not blindly downgrade incompatible queue schema or
restore external automation. Clean only exact completed attempt directories; do not auto-delete branches.

Historical catchup is not technically required for clone/fetch/detach H, but current pr.push.gitee
explicitly requires de9a to be an ancestor of remote main; candidate.mirror.gitee requires matching
GitHub state. No governed independent publication path currently exists. Design an explicit CI-only
purpose within the existing entrypoint, preserving default integration restrictions and clean/Quick/
review/archive/FF/readback safeguards. Bind branch/H/observed main/isolation configuration and deny
main/tag, missing isolation and drift. Do not remove the assertion or push directly. This mode is not
implemented; history catchup remains paused and off the CI critical path.

Only documentation/goal changed this turn; executor selection needed no source revision. Original
36 tests retained without rerun. Candidate stays dirty, unfrozen; no remote writes, service changes,
CI jobs, merge or deployment. Both product topics untouched. Automatic CI acceptance remains not_run.


## Local CI-only implementation and consolidated behavioral review

P4 implementation now exists: existing receiver/worker mode routing and cancellation; new
scripts/ci/gitee_ci_acceptance.py for fixed scope, separate queue, exact checkout, sandbox, timeout,
cleanup and receipts; server-owned gitee_ci_acceptance_check.py for actual unittest counts;
publication purpose/scope preview; behavior tests; installation packaging and Make entrypoints.
Default legacy and ordinary publication behavior remain. No product or database changes.

Validation at de9a230d plus owned dirty scope:
- L1 make ci.local.iteration passed: l1-ci-only.log; focused syntax and shell syntax checks passed.
- Acceptance tests: 11 initial, 14 expanded, **16 final passed** (1.624s), l2-ci-only-reviewed.log.
  Tests use real bubblewrap, local Git checkout, cancellation and detached child cleanup. One test runs
  the current publication suite inside the actual sandbox, using dynamic nonzero count.
- Publication tests: **39 passed** (0.251s), l2-publication-ci-only.log. Shared publication behavior changed,
  so this small original 36-case suite was rerun with three new cases.
- Default receiver/worker regression: **18 passed** (0.497s), l2-worker-legacy.log; carried forward after
  acceptance-only exception handling changes. No unrelated product tests, final Quick or freeze.

Consolidated local review fixed cancellation/completion races, symlink/nonregular report rejection,
missing installation packaging and initialization-error terminal state. Assertions verify real process
absence, workspace cleanup, hidden credential paths/environment, denied network, identity and stale-SHA
isolation, not just status names. This is not independent final delivery review or online attestation.
Online bwrap/kernel/service permissions remain unverified; no fallback to an unsafe executor.

Actual read-only preview ci-only-preview.json: observed main b9e3e56a… to HEAD de9a230d… includes
**133 commits and 1234 changed paths**, listed in full. This can expose historical main code beyond
CI changes; scope is relative to main, not proof of novel reachability across all remote refs.
Dirty implementation is explicitly excluded. Re-preview a future committed candidate before publication.
CI-only APPLY is hard-blocked until real platform evidence and reviewed enablement; ordinary path unchanged.

Platform materials have not arrived. Accept only the already-requested credential file path or an admin
configuration export identifying repository/time; uncovered items stay unknown. No repeated credential request.
Outstanding online actions: complete automation isolation; verify sandbox/service identity; deploy explicit
mode under reviewed configuration; authorize and implement evidence-bound CI-only transport; real Push and
negative online acceptance. All remain not_run. Old runner and both product topics untouched.
Outcome: **local implementation verified; online acceptance blocked by platform evidence**. Formal merge
is separately blocked; deployment and user acceptance have not occurred.


Final review also removes any pre-existing count report before execution, preventing an early exit
from inheriting old success. Final acceptance suite: **17 passed / 1.750s**, l2-ci-only-closed.log.
Existing 39/18-case results remain valid. The changed allowlist receives focused policy validation
in l1-policy-ci-only.log. A local iteration checkpoint is prepared for review, not frozen delivery;
no freeze.prepare or Quick. Post-checkpoint read-only scope goes to ci-only-preview-checkpoint.json,
while the earlier 133-commit preview retains its historical context.


Checkpoint review additionally preserves signed-timestamp replay protection in acceptance mode:
duplicate SHA deliveries deduplicate, while reusing the timestamp for another SHA is rejected before enqueue.
Final affected acceptance suite: **18 passed / 1.708s**, l2-ci-only-replay.log; publication 39 and legacy 18
results carry forward unchanged. Clean local checkpoint preview includes **134 commits / 1247 changed paths**
relative to b9e main, still with zero remote writes and no integration eligibility. No final freeze or Quick.


## Steps 1–3: exact public exposure and incremental updater

Public visibility is user-confirmed. Existing self-hosted CI remains the target; no main catchup,
product-topic merge or deployment. Preserve 3dd58b82 and create a new local implementation commit.

Exposure is bound only to 3dd58b82. All 41 advertised refs were re-read; the four missing PR MERGE
objects were fetched exactly with no tags/ref updates/FETCH_HEAD writes. Ref observations before and
after match. Candidate exposure is **134 commits / 2739 novel blobs**, distinct from 1247 diff paths.
`publication-history-scan-3dd58b82-final.json` records every commit and blob identity/content hash,
historical paths, sizes and scanner/rule hashes. Intermediate/deleted versions are considered with
no suffix/size skip; no novel binary content or novel paths absent at final HEAD were found.
A test proves a secret introduced and subsequently deleted is still caught. Existing remotely reachable
content is excluded from new exposure.

Confirmed pattern matches: zero secret and zero unexempted personal-data findings. Six blobs initially
matched seven LC-006/LC-008 occurrences; the existing catalog explicitly classifies them NORMAL_TEXT,
with no new exemptions or sensitive values printed. Two ordinary P4 files contain named customer markers:
`tenant_product_payload_boundary_guard.py` blob 0f66fd4257b98c7dd119e8ef71ec1c1c48b780a7 and
`test_tenant_product_payload_boundary_guard.py` blob 0273b43eac554933dc04ef28a73f12d8c770ab27.
These are exclusion constants and negative naming tests, not customer business content. Publication
of those exact named identifiers lacks explicit authorization and is submitted as the concrete pending
list. No broad request to publish all history; no history rewrite or alternate repository/upload.
Pattern scanning is not a mathematical guarantee against unknown secrets.

Platform configuration remains unavailable: the existing credential-path/admin-export request is
unchanged. Complete hook IDs/events/filters, Go triggers, auto-merge identities, deployment/reverse-sync
rules and exact candidate matches remain unknown. Step 2 is blocked on configuration access, not guessed safe.

New P4 implementation: gitee_ci_incremental_update.py, gitee_publication_scope.py, two focused test
files, Make entrypoints and governance docs. The incremental updater has a read-only default, exact
plan drift checks including credentials, a fixed six-path update, package/isolation probe, verified
file/CI-metadata backups and conservative rollback. It never invokes the old initializer, regenerates
keys or stops the unrelated runner. Apply checks mirror isolation and empty queues, but those local
checks do not substitute for platform approval.

Validation: ci.local.iteration passed (l1-incremental-update.log). Incremental updater **15 tests passed**
(0.337s, l2-incremental-update-reviewed.log), using temporary filesystem/SQLite and fake system/package
commands. Scanner initially failed its empty-object-set case; that owning-layer bug was fixed, then
**4 tests passed** (0.166s, l2-publication-scope-final.log). Changed scanner results were regenerated;
unchanged worker/publication 18/39/18 evidence was retained. No production/runtime tests or final Quick.
Read-only server plan reports two active services, zero queued/running jobs, missing bwrap, pinned
bubblewrap=0.9.0-1ubuntu0.3 and writes=0. Development plan is incremental-install-plan.json; a new local
checkpoint gets incremental-install-plan-checkpoint.json. No installation, backup creation, package write,
service change or candidate push occurred. Online installation, real events and final freeze/review are
not_run. Final publication scope must be regenerated for the eventually frozen candidate, not inherited
from 3dd58b82.


The 2739 novel blobs map to 1245 distinct historical paths; the two remaining main-diff paths are
not novel content exposure. Remote ref observations match byte-for-byte. Focused policy validation
passed after the allowlist update (l1-update-policy.log). New source hashes and test-input bindings
are saved in incremental-update-local-evidence.json. Commit creation does not invalidate those inputs;
only the source-SHA-bound read-only installation plan is regenerated.
# Desktop execution takeover (2026-09-23, baseline db160f72)

Reverse mirror timer is disabled/inactive; the historical failed service has PID 0. The first incremental update installed
bubblewrap and backed up to `/var/lib/gitee-ci/update-backups/incremental-od5jpxr3`, then its sandbox probe failed due to
AppArmor capability denials. Original files were restored and CI services remain stopped. The upstream v4.0.3 ABI4 bwrap
profile (SHA256 a964037f6cf0df1099f14226b037eaedde6237c86e715188e93eb460b30be859) was installed without changing global
sysctls. A governed same-user/systemd-hardening probe now passes with network and credential isolation. This changed
environment permits a fresh installer plan/retry. A private rotation file is kept only in Git metadata and excluded from archives.

The owner explicitly requested execution of the existing CI update/isolation/CI-only acceptance plan. Historical main
catchup, merging and product deployment remain excluded. Public-history/customer-identifier authorization is retained.
User screenshots show no platform mirror and Gitee Go not activated. The authenticated hook 2106026 was paused and its
unsupported check-run subscription removed; the page confirmed success. Push/PR remain configured. No secret screenshot
is archived; the signing secret needs rotation. The live installer plan still matches the checkpoint, with zero active jobs.
The new bounded mirror-isolation Make target only disables/stops the registered reverse mirror and reads back its state.
Scope is P4 existing CI infrastructure, excluding product data, the old runner and both unmerged topics.


## 2026-09-23: post-Push check reporting increment (development)

Baseline `77c5efe111fb30b857bbb2b1c2a098b2f559630e`; dirty, not frozen.
The earlier real Push and exact-SHA 42-test server run passed; reuse the original
`desktop-ci-acceptance-result.md` and `ci-live-result-final.json` artifacts. This is
not full gate equivalence, main integration, deployment, or product acceptance.

Ownership: P4, existing CI worker reporting, `scripts/ci`; no P0-P3 business changes.
The opt-in trusted-parent reporter persists create intent before POST, reconciles
unknown outcomes by a unique marker without duplicate POST, and requires exact-SHA
readback. Zero tests or incomplete success receipts become action_required. The
fixed name is `sce/ci-only-acceptance`; no build logs or local paths are published.

The UI exposes required checks, but no protection rule was saved. The merge API
still has no source/target dual-SHA parameters. A single-repository, 30-day token
form with projects and mandatory user_info was prepared for user submission.
The user-requested empty private Git token file was created with mode600; it is
excluded from tracked files and evidence archives.

L1 local iteration passed; initial L2 reporter16 + acceptance18 tests passed.
Independent review and affected fixes follow below. Online installation remains
pending: the credential is not delivered, and the existing installer still allows
only its previous three modules. No Quick, push, server changes, or product-topic
changes in this increment. Next: local review, bounded installation/readback,
required-gate mapping and protected integration, then product iteration.

- Implementation review found malformed API output could interrupt the worker.
  Added output/summary type validation and worker-side reporting failure isolation;
  only a fixed error code is logged, without discarding tests or revealing exceptions.
- Revised L2 `make ENV=test verify.gitee.checks.unit verify.gitee.webhook.ci` passed:
  reporter18, legacy worker18, mirror4, cutover9. Sandbox18 evidence is reused because
  its execution inputs did not change. This remains dirty local implementation;
  installation and platform readback are unverified, with no frozen delivery claim.


### Check reporting installation closeout

After WSL recovery, read-only authenticated API identity and checks listing passed;
check-write permission is not yet accepted. The existing updater now includes the
fourth module and an optional fixed-path service-owned0600 token referenced only by
the worker. Plans exclude its value; failure restores old files/config or removes
a newly created token. L1 iteration and L2 updater18+reporter18 passed. Installation
is the next L3; business database/frontend L4 is out of scope. A clean installation
source commit is needed by the existing updater, not a frozen publication claim.
Final Quick/push remain pending until online readback.
