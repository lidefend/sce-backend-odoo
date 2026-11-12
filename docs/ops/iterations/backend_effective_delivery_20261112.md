# Backend effective delivery closeout

Baseline: `45cd5c6714a54339a8f073019a8604ffb71e7046`, protected merge of PR #874. Branch: `refactor/backend-effective-delivery-20261112`. Single result index: `.agent/runs/BACKEND-EFFECTIVE-DELIVERY-20261112/run.json`.

P0 smart_core owns native identity, discovery and effective qualification. P1 construction consumers preserve product entitlements/dependencies and consume the shared native decision. P4 only extends existing deterministic test selection and disposable local.test wrappers. Frontend changes are contract-consumption tests only; no frontend product feature, customer data, deployment or new runtime authority is included. Initial worktree was clean.

`EffectiveDeliveryService` resolves product identity, release policy, native reachability and tenant scene selection without calling system.init or capability-list consumers. Startup compiles its navigation projection; direct gates use its cached authority; native capability aliases consume the same pairs. Internal scene actions are qualified from native/provider declarations before tenant selection. Equivalent references are coalesced after selection without losing contextual action-only access; different execution requirements remain ambiguous. Odoo still enforces actual data and operation permissions.

The P0 authenticated `workspace.home` is an explicit actionless platform declaration. It survives absent business qualification and release failure, grants no native action, and is not granted to the public user. It is part of the shared result rather than a restored startup-only navigation fallback.

| Acceptance behavior | Scoped evidence |
| --- | --- |
| Native identity survives labels, same-model duplicates and missing XMLIDs | Catalog/consumer units; unusual separator collision regression; database-local scope explicitly marked |
| Module discovery cannot broaden when no XMLID matches | Empty-module and renamed-title discovery units |
| Discovery does not publish | Candidate rows disabled/hidden; ORM verifies runtime does not invoke catalog fallback |
| Tenant selection remains independent | Real scene enablement test grants selected compositions, removes grants when disabled, without changing native ACLs |
| Shared capability survives A/B composition | Real tenant-filter function plus actual direct validator body cover A+B, B only, neither; different execution semantics stay distinct |
| Native denial remains authoritative | Action-group/model changes, invalid or conflicting alias references, and native-source denial regression |
| Startup/direct consistency | HTTP system.init compares final authority pairs with the same user's direct authority; final navigation and scene-ready both contain declared home |
| Designed/native channels and route meaning | Scene-shell units and existing frontend shell consumption; actual Python output feeds strict TypeScript route normalization and action-only/menu lookup |
| Execution checks remain live | Admitted entry does not permit unauthorized project write or record read; project contract operation rejects missing native access |
| Context/cache lifecycle | Real company A→B→A, scenario enablement change, no-XMLID implied-group signature and cached recomputation |
| Single qualification ownership | Compiler cannot rebuild authority; runtime solver does not import handler; native alias paths consume common result |

The frozen code candidate `78a4aeae1aa035653904e20c8c69111af9a1ac4b` passed 49 governed lifecycle ORM cases with zero failures/errors. Receipt: `.runtime/test-baseline/1794480752660025578/receipt.json`; source unchanged, carrier cleanup confirmed. Pure navigation, publication, scene, cache and cross-language consumption checks passed. Independent code review found no remaining proven S0–S2 findings. `make ci.delivery.freeze.prepare` passed with no generated differences. Full mapped iteration and current remote PR gates remain pending at this documentation commit.

Earlier failures and interrupted attempts remain in the run index, including the genuine empty-startup regression and the multi-scene/cross-bucket review findings. No failed, zero-test, interrupted or changed-source attempt is counted as passing. All runtime writes used the governed disposable `sc-local-test/sc_test` profile; persistent development and customer databases were not modified.

This is scoped backend acceptance, not a claim that every installed action or frontend workflow was exercised. A full browser matrix was intentionally not run; representative existing consumption was sufficient for backend-only contract changes. Mainline integration, deployment and user acceptance are separate and are not claimed. Roll back owned topic commits in reverse dependency order; no production migration or data restoration is required. The run index holds the next exact step and final check results.

P4 验证登记修正：完整增量门禁发现已接线的 `verify.nav.pro01r.route_authority.unit` 仍在零引用处置表。通过现有 `--unregister-target` 校验实际引用后移除该条登记，冻结阈值不变。原始失败日志：`.runtime/backend-effective-iteration-final.log`。新登记文件自动映射到 `verify.verification.lane_coverage`。
