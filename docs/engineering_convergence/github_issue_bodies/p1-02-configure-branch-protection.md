### Problem and Goal

Protected branch policy must be enforced by GitHub.

### Scope

Configure the `main` branch protection settings listed in `github_governance_runbook.md`.

### Non-Scope

Repository permission redesign beyond `main`.

### Acceptance Criteria

- Direct push to `main` is blocked.
- `merge_policy_gate` branch protection and review rules are active; release
  qualification remains a separate candidate path.
- Evidence screenshot or settings export is attached.

---
Source: `docs/engineering_convergence/github_issue_seed_v1.1.md`
