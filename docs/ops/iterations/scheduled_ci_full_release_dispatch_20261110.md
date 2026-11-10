# Scheduled CI full frontend release dispatch

Status: active

- Formal Product Layer: P4
- Layer Target: exact-head GitHub Actions full frontend release dispatch
- Baseline: `main@fb5f5c82fe7404939cd697ea99e1f2ba237b0310`
- Failure owner: validation tooling
- Excluded: product code, contracts, ACL, performance budgets, business data and deployment

## Context

The scheduled full frontend release lane has remained red on older mainline
SHAs. PR #866 later got the performance probe through, but its branch stopped at
the released-navigation assertion for the contract surface. PR #868 has since
merged the capability reuse and the scene/company route cache invalidation that
were missing from the earlier mainline.

The first repair attempt added a governed full-release dispatch target and ran
it on `main@fb5f5c82f`. Run
[`42815547971`](https://github.com/lidefend/sce-backend-odoo/actions/runs/42815547971)
passed the absolute performance budget and all preceding gates, then failed at
the contract-list released-navigation assertion:

```text
smart_construction_core.menu_sc_p1_daily_contract is not present in the
fixture_role_contract_operator released navigation
```

The fixture user carries the real
`smart_construction_core.group_sc_role_operation_user` group, but the product
role catalog did not declare `operation_user`. Identity resolution therefore
fell closed to `restricted` and denied the entire navigation surface. The menu
and implied contract/cost/settlement/project groups were already correct; the
missing artifact was the product role declaration.

The remaining control-plane gap was that there was no governed Make target for
dispatching `frontend_release_gate.yml` on an exact remote main SHA and reading
back the newly created run. Ad hoc `gh workflow run` would bypass the
repository's remote-write authority.

## Repair rule

Add one P4 dispatch target that:

- requires a full expected SHA;
- requires a clean worktree and the authoritative repository identity;
- requires the live remote target branch to equal that SHA;
- dispatches `frontend_release_gate.yml`;
- waits for and reports a newly created `workflow_dispatch` run whose head SHA
  equals the expected SHA.

Do not change product behavior, contracts, ACL, release budgets or workflow
semantics.

The companion P1 repair declares `operation_user` against the existing real
group and uses capability discovery, so navigation remains the intersection of
the declaration, real groups, model ACLs and record rules. It does not add an
ACL or widen a group.
