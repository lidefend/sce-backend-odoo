# My Work Payment Detail Target — Batch I

## Boundary

- Formal Product Layer: P1 construction industry standard product.
- Layer Target: authoritative payment work-item detail navigation.
- Module: `smart_construction_core` payment work-item service and the existing
  generic typed frontend consumer.
- Standard vs User-Specific: construction product standard; no customer rule,
  runtime configuration or data repair.
- Why here: the service owns payment work-item facts, actions and targets, and
  already declared the formal action XMLID.
- Why not elsewhere: Canonical/Floorplan must consume the selected action
  contract, not choose it. The frontend and UI kits must not infer payment
  semantics. The P0 validator must not accept synthetic native identities.
- Blast Radius: the detail link of payment items in My Work. Lists, action
  execution, permissions, record state and other models are unchanged.

## Root Cause

The product workspace target contained `action_xmlid`, but its route was fixed
to `/r/payment.request/<id>`. That route omitted both `action_id` and `menu_id`,
so the form request used the actionless model fallback instead of the formal
payment action whose Contract V2 drives the golden Floorplan.

## Change

- Bind the workspace target to the formal user payment-application action and
  menu already registered by `smart_construction_core`.
- Supply stable `action_ref` plus resolved `action_id` and `menu_id`.
- Include those identities in the record route so the existing generic router
  and Contract V2 consumer preserve backend authority end to end.
- Preserve the formal `生成付款登记` state visibility on its product action so
  a draft readonly record retains `提交审批` as its single effective primary
  action.
- Keep model-only routing as a missing-registry fallback; do not weaken native
  occurrence validation or add frontend model branches.

## Evidence

- Exact `TestPaymentRequestWorkItemService` method — PASS, 1 selected, 0 failed,
  0 errors.
- Strict frontend TypeScript — PASS.
- P1 payment field completeness guard — PASS.
- Draft-readonly single-primary Contract V2 regression — PASS, 1 selected, 0
  failed, 0 errors; `提交审批` is the only effective primary and `生成付款登记`
  is invisible before approval.
- The first frozen release run proved the target-routing correction (no HTTP
  500) and then failed closed on the missing single primary, which produced
  this second P1 correction. The final release evidence follows the refreshed
  candidate.
- Quick relevant security and contract guards — PASS; the aggregate Quick
  target stopped later on an unrelated pre-existing product-version duplicate
  in architecture documentation and a generated snapshot.
- Governed acceptance upgrade, fixture reset and J10 browser evidence are
  recorded after freezing the candidate commit.
