# Scheduled CI full frontend release dispatch

Status: active

- Formal Product Layer: P4
- Layer Target: exact-head GitHub Actions full frontend release dispatch
- Baseline: `main@5897cb3c3cf23be94cc935741fcf11840e31f54f`
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

The candidate was rebased by merge onto `main@5897cb3c3`, which includes the
backend authority and approval-contract closure lane. The merge exposed one
P4-only routing conflict: the product menu contract is consumed by both its
specific contract guard and the role-surface/navigation projection guards.
The integrated selector must require that union, not replace one owning check
with another.

Runtime verification after upgrade exposed a second P1 defect: the new
`operation_user` role resolved correctly from the real group, but did not bind
the existing native entry group `group_sc_entry_p06`. The daily-contract menu
was rebound to that entry group, so the role still had no visible native route.
The repair adds only `group_sc_entry_p06` to `group_sc_role_operation_user`;
it adds no ACL, capability group or menu record.

On the governed `local.dev` profile, the real operation user now resolves only
as `operation_user`, sees `menu_sc_p1_daily_contract` natively, and receives the
same menu/action pair in runtime release navigation. The container runtime also
had to be recreated through `local.dev.up` because its source bind mount pointed
at the separate acceptance worktree; the database volume was preserved.

The first full lane on `924c8965c` passed role/navigation projection and the
release build, then failed the delivery-hardening accessibility matrix with
nine identical `scrollable-region-focusable` violations. Every finding targeted
the same nested TDesign `.t-menu--scroll` list. The outer navigation tree
already owns a labelled, focusable scroll region, so the vendor inner list must
delegate scrolling to that host. The two navigation commits from the paused
performance branch are integrated here with their static negative guards.

The focused local axe probe did not reach browser assertions because the
acceptance environment stopped while reading runtime IDs; that attempt is an
environment defect and is not recorded as accessibility evidence. The current
production build was inspected to prove both override declarations are present
in the emitted CSS.

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
