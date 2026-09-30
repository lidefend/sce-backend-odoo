# Gitee frontend execution evidence reuse

Formal Product Layer: P4. Layer Target: existing local offline verifier, owner SSH
publication, trusted Gitee worker. Module: scripts/ci and scripts/ops. This is CI
execution reuse, not product semantics or authorization. No P0–P3, database,
credentials, service resource limits, or deployment behavior changes.

PR #30 first failed because generated reports were stale and its dependency
manifest had no matching remote offline cache. Those were fixed in `6ddf4bda` and
the existing cache install entry. The next remote production build took over
15 minutes under the existing small worker memory limits. Local verification of
the same candidate passed; merely asserting this locally could not satisfy a
remote required check. This batch adds an authenticated publication/consumption
path, using the existing owner trust and infrastructure.

## Trust and identity

The authority is the authorized owner's local execution host plus existing SSH
authentication. Hashes prove integrity/binding, not execution provenance. There
is no arbitrary receipt import CLI and no new signing key. The publisher itself
runs the existing verifier against `git archive` of the exact clean HEAD in a
credential-free, network-isolated bwrap process. Candidate processes cannot see
the host receipt directory or SSH credentials. Only the trusted parent seals
successful subprocess outcomes. This does not defend against malicious root or
compromise of the authorized owner's host.

The package manager runtime is moved outside the writable candidate tree before
the first step on both local and remote runners. Candidate-created `/work/pnpm`
aliases cannot alter a later host bind mount. Remote Git metadata is read-only in
the sandbox. Artifact collection checks every path component from work to dist,
rejects symlinks/special files and enforces size/count limits before bounded reads.

The receipt binds repository, PR number, source branch, head, target branch and
base, Git tree, all dependency input manifests and archive hash, pinned Node and
pnpm hashes through the dependency key, Python version/Linux/architecture,
declared execution environment, exact four commands, and trusted policy/tool
source hashes. Actual execution dependencies (`Executor`, test counter, producer,
consumer, cache verifier and workflows) are included. It contains each step's
successful exit, nonzero test count, log digests and a regular-file-only build
archive with a per-file digest manifest and a nonempty index.html.

The publisher checks clean source identity before and after execution and before
transport. The server bootstraps only its active root-owned controller, validates
the payload, fsyncs files and atomically installs an append-only directory. It
never executes or extracts the build archive as root. Existing conflicting
evidence is not overwritten. Root-owned storage and every ancestor must reject
symlinks and group/other writes. The trusted controller, never candidate imports,
validates the receipt against the current plan and candidate tree before use.

## Operation

Use the already prepared matching dependency bundle; prepare a new one with the
existing governed entry only when dependency inputs change. Install the reviewed
controller through `gitee.ci.server.update` after its normal idle/backup checks.
Then, on a clean candidate, preview and execute:

```sh
make gitee.ci.frontend.reuse.publish EXPECTED_HEAD=<full-head> GITEE_EXPECTED_MAIN=<full-base> GITEE_PR_NUMBER=30 GITEE_FRONTEND_OUTPUT=<prepared-directory> GITEE_NODE_ARCHIVE=<pinned-node-archive>
make gitee.ci.frontend.reuse.publish EXPECTED_HEAD=<full-head> GITEE_EXPECTED_MAIN=<full-base> GITEE_PR_NUMBER=30 GITEE_FRONTEND_OUTPUT=<prepared-directory> GITEE_NODE_ARCHIVE=<pinned-node-archive> APPLY=1 GITEE_FRONTEND_REUSE_CONFIRM=RUN_AND_PUBLISH_EXACT_FRONTEND_EVIDENCE
```

Publish the sealed receipt before pushing the exact candidate to avoid starting
an unnecessary remote build. A dependency cache is still needed if reuse fails.
Historical `verification.json` files are not retroactively admitted: the new
producer must run and capture the artifact itself. A receipt with the same exact
identity but different contents is a conflict, not permission to overwrite. If
SSH completion is uncertain, read back that exact server directory and validate
its files before deciding whether any further action is needed.

The worker continues all other gates and the cheap frontend extension policy
guard. Only lint, full/strict types, tests and build are reused. Its receipt says
`verified_local_execution`; it does not claim those steps reran remotely. Missing,
corrupt, untrusted or stale evidence records a bounded fallback reason and runs
the original dependency/command chain. A failed remote policy guard, cancellation
or final PR/base identity drift still prevents success. Candidate/full lanes and
their runtime requirements are unchanged. No product deployment follows reuse.

## Validation and recovery

Extend existing frontend cache, formal executor and update targets; no new gate
system. Tests cover all identity dimensions, tool/environment/recipe drift,
zero/all-skipped counts, failed/partial receipts, log/artifact corruption, unsafe
archives, unprivileged/writable storage, append conflicts, actual sealing, and
remote execution routing including fallback. Generated reports and registry
evidence must be refreshed when source inventory changes.

The living execution result index remains the PR #30 external evidence index at
`/home/lidefend/workspace/.codex-evidence/frontend-quick-closure-20260928/result-index.json`.
It records exact frozen identity, focused tests, independent review, local proof
publication, controller installation and remote original receipts. A local test
pass or publication alone is not proof that the live worker consumed evidence.

Rollback the trusted controller with its captured pre-update backup/pointer;
older controllers ignore the append-only evidence directory. Existing dependency
caches and server credentials remain unchanged. Do not delete unrelated caches
or modify success records to recover. Four current-head checks and protected PR
identity/readback remain required for integration. Mainline, deployment and user
acceptance are reported separately.
