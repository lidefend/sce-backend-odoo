# Scheduled CI capability projection performance recovery

Status: verification_pending

- Formal Product Layer: P1
- Layer Target: construction capability registry startup projection
- Baseline: `main@1ad805b621de6ced0a497c5a5f6e10bec358896d`
- Failure owner: product performance
- Excluded: budget threshold changes, ACL/navigation semantics, business data and deployment

## Failure

Full frontend release run
[`42754741091`](https://github.com/lidefend/sce-backend-odoo/actions/runs/42754741091)
passed lint, typecheck, production build and all preceding static gates, then
failed the absolute performance budget:

| scenario | observed median/max | budget median/max |
| --- | ---: | ---: |
| login_to_interactive | 6667 / 6784 ms | 3000 / 5000 ms |
| my_work | 4284 / 4339 ms | 1200 / 2500 ms |
| company_switch | 3499 / 3660 ms | 2000 / 4000 ms |

The login samples attribute 4.6–4.9 seconds to `system.init` capability loading.
That path delegates to the construction capability registry, where each
action-bound capability rebuilds published navigation authority during access
resolution and again while building its entry target.

The My Work samples also start measuring while the role-home capability,
scenario and work-summary requests are still in flight. The arbitrary two-second
wait therefore contaminates the SPA transition measurement with background home
requests. The probe must wait for intent traffic to become quiet before taking
its request offset.

## Repair rule

Resolve the published menu/action pair map once for the whole capability
projection and reuse it for every action-bound capability. Do not change native
actions, action groups, model ACLs, role declarations, navigation publication,
company scope or performance budgets.

The browser performance probe waits for bounded intent quiet before measuring a
SPA transition. It does not remove requests or extend scenario budgets.

## Observed validation

- `verify.daily.permission_truth.capability.orm`: 12 tests passed, including
  cached-versus-legacy pair equivalence and one-call route-authority regression.
- `verify.frontend.delivery_hardening.guard`: 17 tests passed.
- `verify.frontend.dev.incremental.unit`: 104 tests passed.
- `verify.frontend.standard_preview.unit`: 131 Python tests and 42 Node
  assertions passed.
- `verify.capability.provider.guard`: passed.

The local ORM fixture now codifies the post-PR #862 rule: a read capability
without a published role surface remains denied, while native action/model
changes remain bound to the same action authority.

The generated complexity and split-plan reports refresh only the changed line
counts for the capability registry and its test.
