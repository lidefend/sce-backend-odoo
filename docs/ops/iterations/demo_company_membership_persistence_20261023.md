# Demo Company Membership Persistence (2026-10-23)

## Batch boundary

- Batch: P1 demo data ownership correction.
- Objective: keep `wutao` and `demo_full` in the declared `[1,2]` company scope
  across module upgrades and runtime restarts.
- Formal product layer: P1 construction demo baseline.
- Layer target: `smart_construction_demo` module data and the declared
  `demo_company_membership` seed step.
- Not in scope: ACL/group widening, platform administration, customer data,
  production deployment or Gitee integration.

## Root cause

`data/demo/wutao_full_product_user.xml` uses `noupdate="0"` and previously
redeclared `company_ids` as only `base.main_company`. Every smart_construction_demo
data update therefore reset the two business-full users to company 1. Other
group-level users whose records do not redeclare `company_ids` retained the
membership added by `demo_company_membership`.

## Implementation

- Remove `company_ids` from both business-full user records in module XML.
- Keep `company_id` as the primary-company declaration.
- Add a hermetic regression test requiring `demo_company_membership` to remain
  the only runtime company-scope writer.

## Verification

- `make verify.demo.lifecycle.unit`: PASS, 142 tests.
- exact-head Quick, module upgrade, seed replay and post-restart role readback:
  pending in this batch.

## Rollback

Revert this commit and re-run the declared demo seed. No ACL or data migration
schema change is involved.
