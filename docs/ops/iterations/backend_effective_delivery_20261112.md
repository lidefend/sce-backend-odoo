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

候选 `1656cb8a79b153fe76eea8c4abf1529d67b48446` 已通过完整本地增量门禁的 18 个目标，四组 ORM 为 24/49/3/2，源码和受管环境未变且清理完成；公共秘密/个人数据扫描及生成证据预检通过。PR #875 已创建。远端 frontend_release_gate 暴露旧职责测试仍要求 handler 直接合并平台职责授权；实际调用已迁至共享求解器。本次仅迁移接线断言并补增量映射，保留原有行为断言。原始主线 baseline 保持不变，不因本次修正推定未登记的 ORM 复用。最终候选及远端结果以 PR 和 `.runtime` 原始回执为准。

用户对1656候选独立评审发现三处S2：导入场景目录与内部准入声明分叉、tile按默认而非最终payload授权、落点集合固定首页。已停止a0a790的重验并确认临时测试载体移除。修复保持P0/P1边界：共同数据声明读取保留原合并优先级且不调用能力消费者；tile显式提交合并/冻结目标，权益与依赖仍归capability；落点在最终准入过滤后按原声明优先级选择。新增离线及ORM回归，当前仍待运行验收与复审，不能沿用此前无S2结论宣布完成。

修复候选补充：有效声明共用 DB/导入/代码优先级；tile 按实际或冻结 payload 准入；落点从最终 authority 选择。移除 dbname 派生映射缓存，场景/版本事实变化清 registry。远端 bundle 分片另暴露正式 contextual 工作台承载 menu 与目标 action 不同，被新增严格绑定误拒绝；仅可信角色声明允许 carrier，并分别检查两端原生权限。55 项菜单单元、63 项场景语义及三组定向 Make 单元通过；新增导入和版本生命周期 ORM 尚待执行，旧候选结果不能覆盖本轮。

5486a5f74 的受管 lifecycle：54 项中 1 项失败（落点正例未冻结正式发布事实，53 项通过），完整回执 `.runtime/test-baseline/1794485214694278724/receipt.json`；未记为整组通过。补齐正式发布前置后复验。新 workspace 目标自身四份测试的 planner 映射也已补齐。

01f67e709 增量检查在 lifecycle 阶段停止：身份 ORM26通过；lifecycle54中2失败。落点测试还需显式发布原生 setup 候选（仅冻结既有策略不会授予候选资格），最终准入导航中的 scene 标记也应纳入落点集合。另 HTTP startup 与直接缓存 authority 的无 action 首页 pair 不一致，增加 fresh/cached 诊断，尚未定因，不能宣称修复完成。

6a5424300 的 bundle 定向26项：1失败/1错误。setup候选显式发布后被旧 resolve_scene_key 的逐行 model/view 回退映射成enterprise.company，已按原生 menu/action 身份优先修复并补纯单元。班组项目经办正例缺失菜单原生 entry_p03 组，补正例并保留撤销入口后拒绝的负例。此次HTTP启动/fresh/cached一致性通过；另修复求解异常不应被ormcache持久缓存为空authority，新增瞬时失败恢复用例。当前仍verification_pending。

1c7bec14a 的 bundle 集成32项：31通过，1失败。工作台正反例、瞬时缓存恢复通过；setup共同求解和真实handler role正确，但精简payload因home页面存在重写default_route/home_ref。修复投影仅补缺省首页、保留明确有效路由，新增pure反例及planner映射，定向单元通过，独立源码复核通过；新候选ORM仍待验证。
