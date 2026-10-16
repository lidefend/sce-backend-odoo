# Main scheduled CI closure — 2026-10-16

## Scope and ownership

Formal Product Layer: P4. Layer Target: test fixtures and CI verification.
Module: frontend test scripts, smart_construction_core tests, demo tests, backend suite.
Standard vs User-Specific: generic verification; no customer-specific behavior.
Why Here: nightly failures must distinguish stale tests from actual product defects.
Why Not Elsewhere: do not weaken ACL, data-space or lifecycle guards to satisfy fixtures.
Blast Radius: affected frontend assertions and backend test classes; existing runtime behavior unchanged unless independently proven defective.
Excluded: dirty primary worktree, daily server, customer module, deployment, live data writes.

## Plan

1. Bind original schedule failures (10bf72ef) to current main41c7a9dd and classify exact failures.
2. Fix six frontend test lint errors and run affected behavioral scripts plus lint/type checks.
3. Repair confirmed stale backend setup/assertions using formal lifecycle/data-space declarations; validate targeted classes through existing governed test lanes. Escalate product defects to their source layer, never bypass guards.
4. Run affected CI lanes, independent review, freeze/Quick and protected PR integration. Restore scheduled coverage without skips or reduced test scope.

## Evidence and rollback

Original logs: /tmp/sce-ci-38818510036.log, /tmp/sce-ci-38811434965.log, /tmp/sce-ci-38811625754.log.
Release candidate failure is downstream of frontend gate. Backend core: 30 failures/59 errors of483 tests; demo:1 failure of11. These are original observations, not current candidate results.
Rollback: revert owned commits; ordinary tests rollback; independently committed race fixture cleanup and restoration required. Stop dependent validation on earlier failures; reuse independent results with unchanged inputs.

## Diagnosed product defect and refined boundary

P1 workspace dispatch was a real product failure, not a stale positive assertion.
The standard snapshot released both workspaces while their old standalone target
menus were absent from the released surface. Finance already declared the actions.
Use existing contextual action authority to bind each handling action to its released
workspace menu. Each workspace explicitly select their own carrier; the shared
ledger must not borrow the sibling workspace's route. No ACL, release filter or
visible navigation baseline is relaxed. Published integration tests move to the
industry bundle, which owns startup product identity; core-only installs do not.
All nine handling actions and both ledger buttons are asserted, replacing partial
continue-based observations. The first four bundle tests passed after this fix;
negative carrier tests and independent review remain pending.

Additional targeted results:54 transactional P1 funding/finance tests had53 passes
and one secondary-company context error, corrected in its fixture. Payment-domain
isolation6tests passed; normalized payment body assertion passed after removing
retired interaction fields and rebinding its exact edit field count. Core amount
matrix5tests passed. Runtime logs remain in /tmp/sce-scheduled-*.log; these are dirty
iteration observations, not frozen delivery receipts. Four independently committed
concurrency tests were excluded from this transactional run by AST call-graph analysis
(/tmp/sce-scheduled-p1-committed-exclusions.json), not from final CI coverage.

## Consolidated batch review

Three workspaces now bind contextual routes to their own carrier. Explicit grants
cover finance (11), project_member/pm (3 each) and exclusive business_full (14).
Published integration tests prove all actions, own-carrier refusal and exclusive role
behavior without increasing the 90 published menu baseline. Backend fixtures create
explicit synthetic customer companies and formal approval policies; platform bootstrap
data stays unchanged. Legacy-corruption negative fixtures are distinguished from
positive formal action flows. Demo assertions follow real approval-driver delegation.

Final uncovered run:13/13; separate ambiguity1/1 and legacy-identity1/1. P0 lifecycle79
passed and prior unchanged affected cases retained (single run evidence index).
Concurrent fixture setup now owns its independent company, uses bounded transactions,
and removes exact company dependencies after execution; prior failed-cleanup records
were restored through a bounded local.dev.test recovery and read back absent.

L1 iteration, role-surface16 + create-defaults4+5, scheduled guards and ORM31 negative/
positive cases passed. Independent dirty review found no blocker; this is permission
to freeze, not remote CI success. No daily/customer database changes or deployment.
Final exact-head Quick, independent frozen review and full isolated GitHub backend
suite remain required. Release/frontend schedule failures will be checked through
the affected candidate gates. All original logs are indexed in run.json.


## Owner-requested incremental premerge backend closure

P4 owns the exact-tree impact planner and required-check wiring. Nightly remains
full. PR execution selects changed module owners and transitive consumers from
both base/head manifests and explicit cross-module imports. Deletion and rename
both sides are retained; shared runner or unknown inputs select full, with reasons.
Each changed owner must have executable coverage; another covered owner cannot
mask a gap. Excluded modules are outside impact, not fabricated passing receipts.
No second cache or result-reuse authority is introduced.

`professional_quality_gate` waits for the selected reusable backend runner and
fails on authorization/plan failure, missing/invalid required output, failed,
cancelled or skipped required execution. The reusable runner re-derives the plan
from exact trees, retains per-module isolated databases and existing nonzero,
identity and complete-plan execution checks. The registered sc_gate/sc_smoke
suite selection remains unchanged, as do separate specialized ORM gates.

This batch changes shared execution infrastructure, so its deterministic impact
is the full 14-module set. This is not the default for every merge. Leaf changes
select only their owner/consumer closure; docs/frontend-only inputs declare an
empty backend set. Tests prove deletion, rename, old dependency retention,
unknown/global fallback, individually uncovered seeds and the actual aggregate
shell failure truth table (15 planner tests,29 risk tests,6 dispatch tests,
16 security tests). Independent review's two fail-open findings were fixed.

Old frozen run38850683334 attempted14/14; only eight methods in
TestDeclaredStateTableIsTheOnlyStateWriter failed setup because clean installation
had no implicit tax group. Explicit company-owned group and country fixed the
fixture; governed local.dev targeted8/8 passed. No lifecycle assertion weakened.
Remote execution of the new workflow and final integration remain pending.


## Owner correction: GitHub-hosted CI only

The owner clarified that GitHub availability means validation must not use the
slower self-hosted runner. The previous candidate reused the legacy backend
self-hosted executor; that choice is superseded. All four remaining CI runner
bindings (backend suite, demo, smoke, infra stage) now use ubuntu-latest. The
security guard rejects self-hosted/dynamic runner labels. Manual legacy lanes
remain manual and are not claimed as runtime-validated by this change. Demo
image references retain their immutable digests but use official origins rather
than domestic runner-specific mirrors. No daily deployment resources change.
The backend remote result must come from the newly frozen hosted candidate;
previous runner observations cannot prove this execution environment.

## Navigation failure discovered by the full remote lane

Remote b5a4647c frontend run 38854098601 passed all 28 observed page identities
but failed navigation comparison. The prior 605c frontend run skipped the full
surface command; it is not evidence of the same browser layer passing.

P1 fixes restore existing role business capabilities through formally released
replacement menu identities: owner daily contract; project-member/PM daily-contract
deduplication; PM income/expense settlement and budget. Native budget menu restores
its predecessor's cost_read group without changing model ACLs. Its two contextual
budget actions follow the same replacement carrier. Conflicting exposure records
are updated only for these identities; finance/executive remain explicitly narrowed.
The budget acceptance row's previous visibility evidence is invalidated, not reused.

P4 fixes bind browser expectations to the formal menu policy and explicit backend
scene map. A scene without action/model must match its declared menu and exact route;
arbitrary missing action/model still fails. The release summary now includes the
navigation failures, not just page failures. Formal-target negative tests reject
stale identities even if role policy and expected manifest agree with each other.

Affected validation: role policy/exposure and navigation-audit pure tests; new
bundle real released-navigation test for three roles plus existing affected role
contract tests; native XML module upgrade on registered sc-local-dev/sc_dev_demo.
No daily server, customer library, new environment or frontend rendering change.
Local paired recovery point: artifacts/local-dev/snapshots/20261016T053115Z.
The upgrade initially refused the default fast-mode guard before execution; the
XML change justified CODEX_NEED_UPGRADE=1/CODEX_MODULES=smart_construction_core.

The d0fcb7b1 Quick executed its checks successfully but issued no receipt because
another worktree committed while the trusted all-reference scan snapshot was live.
Do not reuse it as a delivery pass. This new product candidate requires final
validation after owning-layer defects are closed; unchanged earlier evidence remains
indexed in the run. Shared-reference concurrency is not bypassed.

## Shared-reference Quick recovery

The 8ff27d65 suite also passed every check but correctly refused its receipt after
another worktree committed 1cf5f74c during execution. This observed repeated failure
is P4 orchestration scope: candidate source did not change, scanner reachability did.
The existing single-run receipt producer now validates original scanner proofs first,
then permits one refresh of only the affected existing scanner targets when only
refs changed. Source, scanner authority, protocol and revision selection must remain
unchanged. Old affected proofs are deleted; actual new successful proofs and stable
post-refresh refs are mandatory. Failure, absent proof, candidate mutation, authority
change or a second drift still refuses signing. No receipt import, ad-hoc cache or
successful test fabrication is introduced. The sharded lane remains unchanged.

58 focused tests pass, including a real temporary second worktree committing new
content and moving its branch, as well as each refusal condition above. Independent
review found no blocker. Prior full Quick runs without receipts remain non-delivery
observations. This receipt-producer source change requires a newly frozen candidate.

## PRODUCT-STALE-USER-BOUNDARY-GUARDS-01（P4，2026-10-16）

用户授权产品执行器接管。来源候选 `ac8987fdf9458645bba9cebf78731bccdba6a720`；本节记录未提交范围，非冻结证据。

A 的静态与运行时脚本通过 `make guard.retire` 转入 retired，产品的两个 form_structure 聚合入口解除 P2 前置。替代职责并非客户布局等价验证：

- 原生视图/有效结构：`verify.form_view.native_structure.boundary_guard`。
- 模型、视图、动作作用域：`verify.form_view.scope.boundary_guard`、`verify.form_view.scope.runtime_chain_guard`、`verify.form_view.scope.action_projection_audit`。
- 产品契约及运行时：`verify.form_structure.contract.guard`、`verify.form_structure.contract_runtime.audit`。运行时零模型、契约错误和边界违规失败；无 notebook 等描述性观察不构成违规。wrapper 不再覆盖环境或使用遗留默认库/容器，复制与执行共用调用方受管 Compose 身份；拒绝 isolated 执行并传播失败。
- A 中三列平铺、无 tab、固定客户字段、客户初始化方法和客户菜单覆盖属于 P2；本次没有证明外部客户包验收通过。

同步发现的通用运行链守卫仍检查重构前 API 文件与旧单行文本。已改绑真实 v2 client、保留 view/menu/action 传输及明确 view 上下文；六种删除注入必须失败。未修改产品消费者。

B **仍为 orphan，未退役、未重新接线**。原源码保留在上述 Git 候选；以下为完整的九组函数级职责映射。未验证的外部职责不能以产品抽离守卫 PASS 代替。

| 旧函数 | 责任及处置 | 替代证据状态 |
| --- | --- | --- |
| verify_manifest_boundary | P2 包依赖、初始化资产顺序、载体分离 | 外部 P2 包测试待核验 |
| verify_lowcode_customer_config_baseline_manifest | P2 已确认低代码资产、接受记录、replay 顺序 | 外部 P2 资产及升级测试待核验；通用 lowcode 守卫不等价 |
| verify_history_business_data_baseline_manifest | P2 历史来源、家族覆盖、载荷锁定及恢复 | 外部签名载荷与对账待核验 |
| verify_user_data_rebaseline_contract | P2 历史数量、来源和附件约定 | 旧固定数量不升级成产品默认；版本化 P2 基线待核验 |
| verify_xml_boundary | P2 XML 与数据/偏好初始化载体 | 外部包安装、升级验证待核验 |
| verify_hook_boundary | P2 数据与偏好及已批准资产的调用顺序 | 外部包安装、升级验证待核验 |
| verify_partner_location_boundary | P2 地址回填与偏好分离 | 外部迁移负例待核验 |
| verify_user_data_baseline_boundary | P2 幂等、密码与权限不破坏及历史重放 | 外部迁移行为证据待核验；签名授权不是这些行为的证明 |
| verify_industry_modules_do_not_carry_user_data | 产品行业模块不得承载真实用户资产 | 已迁入 customer_module_extraction_guard；原三模块、文件名、五类文本后缀均保留；实际文件注入负例通过 |

B 退出条件：外部执行器提供精确包身份、上述八组义务的替代用例/版本化废弃理由与非零结果；产品侧核验后通过受管退役入口处理。当前不能声明此缺陷整体关闭。

验证：extraction 五项测试（含六种运行链注入）通过；runtime audit 二十项测试（含真实 main 零样本、shell 环境传递/失败传播）通过；通用结构、scope、native、修正后的 chain 静态守卫通过。独立复核指出并促成环境接线修复，当前 A/B 增量无确定阻断。真实 Odoo 运行时审计未执行，shell stub 不充当活体验收；不改业务数据，不跑浏览器全量。当前 PR 的结算探针菜单缺陷仍独立未关闭，本节不宣称主线集成或发布。
