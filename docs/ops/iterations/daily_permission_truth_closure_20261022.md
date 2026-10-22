# Daily Permission Truth Closure (2026-10-22)

## Batch boundary

- Batch: Batch-A
- Objective: make declared business-full permissions agree with the deployed runtime and close the discovered permission-truth gaps.
- Formal product layer: P1 construction capability semantics with bounded P4 verification and deployment.
- Not in scope: ACL widening, platform-admin grants, frontend permission inference, production deployment, or new runtime/credential authority.

## Findings entering the batch

- `wutao` and `demo_full` expose 130 primary actions and all 90 formal declared entries open successfully.
- Three capability aliases report false navigation denial: `project.task.list`, `finance.payment_request.list`, and `contract.center.open`.
- `demo_role_finance` receives HTTP 403 from `my.work.summary` because a material-settlement prerequisite read raises `AccessError`.
- The role-scope declaration still expects one company while the current demo seed intentionally grants two companies.
- Tenant `demo` serves `2a5db0a2eef0b5850db93d508fef478594dd2942`; platform-control still serves `9734b5c6a687e3d1f2e3e6351d28de36d709f143`.

## Implementation

- `smart_construction_core/services/capability_registry.py`
  - `project.task.list` now resolves through the declared `task.center` scene instead of the unpublished native task action.
  - `finance.payment_request.list` now points to the currently published payment-application action.
  - the redundant aggregate `contract.center.open` is retained as a deprecated compatibility declaration with explicit replacements, but is no longer published in the user capability list.
  - hidden compatibility declarations no longer enter the user-visible capability projection.
- `smart_construction_scene/services/capability_scene_targets.py`
  - declares `project.task.list -> task.center`, matching the existing scene semantics and the browser-verified target.
- `smart_construction_core/models/core/payment_request.py`
  - material-settlement prerequisite checks now require caller read ACL and record-rule access before reading settlement state or balances.
  - an unreadable material settlement produces the named blocking advisory `P0_MATERIAL_SETTLEMENT_NOT_READABLE`; it no longer escapes as a generic `AccessError` that aborts `my.work.summary`.
  - both material-settlement checks share one guard and duplicate advisory codes are collapsed.
- `scripts/verify/demo_usage_foundation_role_scope_manifest.json`
  - aligns the expected company closure with the current demo seed declaration: main company plus the declared second operating company.
- `make/dev_test.mk`
  - registers non-zero ORM checks for capability-target authorization and payment prerequisite permission behavior.

## Verification

| Layer | Command | Result |
|---|---|---|
| L2 | `make PERMISSION_TRUTH_ENV_FILE=.env.local.clean verify.daily.permission_truth.capability.orm` | PASS, 10 tests |
| L2 | `make PERMISSION_TRUTH_ENV_FILE=.env.local.clean verify.daily.permission_truth.payment.orm` | PASS, 9 tests |
| L2 | `make ENV=dev ENV_FILE=.env.local.clean MODULE=smart_construction_core TEST_TAGS=payment_request_work_item_service test.safe` | PASS, 12 tests |
| L2 | `make ENV=dev ENV_FILE=.env.local.clean MODULE=smart_construction_core TEST_TAGS=my_work_backend test.safe` | PASS, 20 tests |
| L2 | `python3 addons/smart_construction_scene/tests/test_action_only_scene_semantic_supply.py` | PASS, 62 tests |
| L1 | `make verify.demo.usage_foundation_role_scope.unit` | PASS, 14 tests |
| L1 | `make verify.frontend.my_work_approval.guard` | PASS |
| L1 | `make ci.local.iteration` | PASS, L1 iteration plan |

Observed failures during implementation were used to narrow the fix:

- the first capability test run exposed stale action-count and hidden compatibility-target assertions; tests were corrected without changing ACL/publication assertions;
- the first payment test run exposed the sibling material-settlement balance check; both checks now use the same permission guard.
- the first deployed account sweep showed that applying `[1,2]` to every role was too broad; the live seed grants the second company only to `wutao`, `demo_full`, `demo_role_owner`, and `demo_role_executive`. The declaration now carries account-specific company scope.

## Runtime verification

Product candidate `20f6275f9292ccda03b4a4d075d72b4e9f60b673` was deployed through the governed candidate lane. Both the tenant and platform-control duties restarted and reported that exact source revision.

| Layer | Command / observation | Result |
|---|---|---|
| L4 | `daily.runtime.entry.verify` at `20f6275f9292` | PASS, 66/66 |
| L4 | `verify.demo.usage_foundation_role_scope.smoke` | PASS, 11/11 accounts plus the wrong-password negative |
| L4 | `wutao` and `demo_full` `system.init` capability readback | 57 capabilities READY, 0 LOCKED; deprecated aggregate absent |
| L4 | `demo_role_finance` `my.work.summary` | HTTP 200 |
| L4 | `verify.frontend.product_configuration_capability.browser` | PASS, 31 assertions, 0 console/page errors, 0 failed requests |
| L1 | `make verify.docs.all` | PASS |
| L1 | `make verify.agent.ledger.unit` | PASS, 18 tests |
| L1 | `make verify.smart_core.ui_base_asset_refresh.unit` | PASS, 9 tests |
| L1 | `make verify.capability.provider.guard` | PASS |

The two prior S1 permission-presentation defects are closed:

- the task-list capability opens `/s/task.center` with 23 task rows;
- the payment-request capability opens the current published payment-application list with 24 rows;
- the duplicate contract-center aggregate is no longer a separate false-locked card; the two real contract lists remain ready.

## Delivery gate closeout

The existing `verify.capability.provider.guard` was red because its July policy allowlist named only `system_init.py`. A later product-catalog handler legitimately consumes the P0 provider, and the provider-focused test imports the same public functions. This was a stale baseline policy, not a provider-boundary violation.

The policy now explicitly permits only those two consumers in addition to `system_init.py`; it does not relax the prohibition on provider imports from construction modules, and it does not widen any runtime authorization.

The restricted scene audit then exposed a separate P0 cache projection gap: the daily runtime uses `ENV=demo`, but missing `ui_base_contract_asset` generation was enabled only for `dev/test/local/ci`. Every scene therefore fell back to `runtime_minimal` and the asset ratio was zero. The demo environment is an internal development tenant, not production, so its missing projection cache now uses the same controlled auto-generation path. This writes only rebuildable UI base contract cache rows and does not change business facts, permissions, menus or scene declarations.

The first exact-head Quick exposed a verification-lane ledger gap, not a product failure:

- the new capability/payment ORM entries were registered as owned `runtime_audit_probe` surfaces rather than silently added to a static lane;
- the pure UI-base asset refresh test was wired into `ci.local.quick.run`;
- the reviewed verification-lane baseline was rewritten to freeze the measured identities (`targets_zero_reference=643`, `remote_only_scripts=83`). No threshold or required-check count was relaxed; `unregistered`, `stale`, missing-owner and missing-basis counts all remain zero.

The next Quick run reached the final shard and found a pre-existing target-name typo in `ci.local.quick.run`: `verify.frontend.static.image_decoupling` did not exist, while the governed target is `verify.frontend.static.image.decoupling`. The prerequisite now names the real target; this also wires the fifteen production/release tools owned by that target into the exact-head local lane, so no remote-only exemptions were needed.

## Rollback

- Revert this branch's product commits.
- Re-select the prior capability/scene declarations and restart the affected duty through governed entries.
- The database change is limited to the governed `smart_construction_core` upgrade; no schema migration or data rewrite is introduced.

## Next exact step

Rerun the final clean Quick gate, deploy the resulting SHA, prove the scene asset ratio and all role snapshots recover, then publish the exact branch candidate for remote CI and protected merge.
