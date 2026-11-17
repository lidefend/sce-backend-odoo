# FE run binding invariant repair (2026-11-18)

## Boundary

- Formal Product Layer: P4
- Layer Target: active-run invariant and exact branch cleanup
- Module: repository delivery lifecycle
- Standard vs User-Specific: platform standard

PR #924 was merged at `9b87cf0e4e59261689a5d9ab107444aa1220ea94`
from source head `8e10133e40a3fa1492fe8f27a37555412864ab76`.

The first cleanup design allowed a bookkeeping branch to delete itself while
its binding remained in main. This satisfies the immediate deletion request but
violates the stronger invariant that no active-run binding may point to a
missing branch. The runtime cleanup demonstrated the defect: the source branch
was deleted while the main binding remained.

## Repair

- Remove the dangling binding for the deleted cleanup branch.
- Restore branch cleanup's existing fail-closed rule: any branch still bound in
  main must first clear that binding through an ordinary merged PR.
- Remove the bookkeeping self-retirement exception and its tests.

The final repair branch is intentionally left bound and undeleted. Its binding
points to an existing branch, so it is valid. A later ordinary product or
bookkeeping PR can clear that binding before the branch is retired; this repair
does not recurse into another self-deleting cleanup.

## Verification

| Check | Result |
| --- | --- |
| `verify.workspace.worktree.guard` | PASS; 152 tests |
| `verify.agent.ledger.unit` | PASS; 18 tests plus ledger guard |
| `ci.local.iteration` | PASS; 2 affected targets with non-zero collection |

The removed self-retirement tests are not carried forward because the authority
they proved is intentionally retired. The original bound-branch refusal remains
covered by the worktree cleanup suite.

## Exclusions

- no product, contract, frontend, model or permission changes;
- no database, runtime, release or deployment changes;
- no deletion of unrelated or protected branches;
- no worktree or evidence cleanup.
