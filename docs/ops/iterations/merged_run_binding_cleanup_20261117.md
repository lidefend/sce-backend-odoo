# Merged run binding cleanup (2026-11-17)

## Scope

- Formal Product Layer: P4
- Layer Target: `.agent/active-runs.json` lifecycle state
- Module: governed local and remote branch cleanup
- Reason: merged branches remained bound to active runs after squash integration, causing the cleanup entry to reject safe retirement.

This batch removes only bindings whose branch, local head, and live remote head exactly match a merged GitHub pull request head. It does not delete references itself; deletion remains owned by `make branch.cleanup.feature` with exact SHA and current-main checks.

Unmerged branches, protected release lines, branches occupied by worktrees, stale detached worktrees and runtime/database state remain untouched.

## Candidate set

The candidate set is derived from:

1. merged GitHub PRs with exact `headRefOid`;
2. a currently bound branch in `.agent/active-runs.json`;
3. a local branch and live `origin` branch at that exact head;
4. no worktree occupancy;
5. no protected `release/*` prefix.

The cleanup pass removed 46 stale bindings. Exact branch identities remain available in the PR description and cleanup runtime evidence.
