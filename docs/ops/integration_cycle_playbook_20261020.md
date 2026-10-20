# Product/Demo Integration Cycle Playbook (2026-10-20)

## Why

The product-configuration + demo integration exposed a repeatable efficiency
defect: a candidate was pushed again after almost every single gate failure.
Each push restarted the 8–10 minute remote suite, while the failing checks were
mostly cheap local guards that could have been collected before the first push.

Observed integration cost:

- 10 overlap conflicts, only 4 of them real product/tool overlap.
- 10 distinct gate failures surfaced one at a time.
- Repeated Codex/Build/Quick cycles instead of one local convergence pass.
- `ci.local.quick` was terminated by a short-lived runner session twice even
  though the suite itself was still healthy; SIGTERM was not a test failure.

The rule below changes the loop, not the gates.

## 1. Before claiming a file is in flight

Take one ownership snapshot from the exact worktree:

```bash
make integration.cycle SUBCOMMAND=snapshot \
  ARGS='--path <path> --path <path>'
```

If the path is already in `HEAD`, it is not an in-flight file. Do not submit a
second copy from another worktree. A stale status report is a coordination
defect, not a reason to touch the file.

## 2. Converge locally before the first push

Run the high-yield integration guards as one bundle. The helper continues after
a failure and prints every independent failing gate in one pass:

```bash
make integration.cycle SUBCOMMAND=fast-gates \
  ARGS='--json .runtime/integration-cycle/fast.json'
```

If a guard fails, fix it before adding more changes. Do not push a candidate
with a known local failure and use remote CI as the debugger.

## 3. Freeze once, then Quick once

After the code and targeted tests are stable:

```bash
make ci.delivery.freeze.prepare
git status --short
```

Review the generated diff, commit it, and only then run the exact-head Quick:

```bash
make ci.local.quick
```

Do not edit, commit, or regenerate tracked evidence after Quick has started.
If Quick fails, fix the owning layer, regenerate once, commit, and rerun the
affected Quick shard. Passed shards remain reusable.

### Long-running Quick

When the runner session has a short wall-clock cap, start Quick detached and
poll the receipt instead of treating SIGTERM as a failure:

```bash
make integration.cycle SUBCOMMAND=quick-start
make integration.cycle SUBCOMMAND=quick-status
```

`quick-status` exits `0` with a verified receipt, `1` while the process is
still running, and `2` when the process stopped without a receipt.

## 4. One push per converged candidate

Push only after the local fast bundle and exact-head Quick are green:

```bash
make pr.push
```

If remote CI fails, collect the complete failed-check set first:

```bash
gh pr checks <pr>
gh run view <run-id> --log
```

Fix all failures in one local batch, rerun the fast bundle, refresh generated
evidence once, rerun Quick once, and push once. Pushing after each individual
fix is the anti-pattern this playbook removes.

## 5. Merge lane

Merge only when all required GitHub checks are green on the live PR head and
the exact-head Quick receipt verifies:

```bash
make integration.cycle SUBCOMMAND=merge-readiness ARGS='--pr <pr>'
gh pr merge <pr> --squash --match-head-commit <sha> \
  --subject "<subject>" --body "<body>"
```

Use `ARGS='--pr <pr> --allow-no-quick'` only for an explicitly docs-only fast
lane where the exact-head Quick is not required.

`make pr.merge` remains the stricter local lane. If its preflight blocks only
on runtime suites outside the selected product/demo scope (for example
`daily_runtime_entry`, `path_namespace_identity`, `list_surface_structure`,
`relation_roundtrip`), record that as an explicit exclusion. Do not fabricate
runtime evidence and do not silently weaken `pr.merge`.

## 6. Post-merge closeout

```bash
git switch main
git pull --ff-only origin main
git rev-parse HEAD
git status --short
```

Close the goal/run metadata in the same bookkeeping change: set the run and
goal to `completed`, remove the completed run from `.agent/active-runs.json`,
and record the merge SHA in the batch record. A squash-merged release branch is
not necessarily deletable with `git branch -d`; keep it unless an owner
explicitly authorizes a force deletion.

## 7. Checklist

- [ ] Ownership snapshot taken; no duplicate copy of committed files.
- [ ] Integration fast bundle green.
- [ ] Targeted non-zero L2/L3/L4 checks green.
- [ ] `freeze.prepare` diff reviewed and committed exactly once.
- [ ] Exact-head Quick receipt verified.
- [ ] One converged push.
- [ ] All required remote checks green on the live head.
- [ ] Protected merge bound to the exact head.
- [ ] main fast-forwarded and run/goal ledger closed.
