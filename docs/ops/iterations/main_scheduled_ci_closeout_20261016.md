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

### 后续交付探针绑定修复

`ac8987fd` 远端 backend_impact_suite 已通过；frontend_release_gate `38858302924` 在导航之后的交付强化阶段拒绝旧结算菜单。P4 resolver 改绑已发布的 `menu_sc_p1_expense_settlement`，动作不变。现有 release_navigation_policy guard 对 resolver 的全部实际 `target()` 调用解析菜单/动作，与正式 standard 发布声明核对；空集合、动态未声明、退役/停用菜单、缺动作或动作错配均失败。13 项导航测试、16 项曝光声明测试、26 项 hardening 测试通过。仅探针输入变化，无模型升级；下一冻结候选交给既有远端 frontend 门禁，不另跑手工全矩阵。旧后端成功不是新 SHA 的合并资格。

### 所有者耗时核查：质量调度串行缺陷

run `38858302942` 实际成功，总约30分钟。后端套件13m50完成后才启动质量worker，其中 chatter 专用ORM4m47、settlement专用ORM2m45、静态/报告/轻量测试5m18。后端使用sc_smoke/sc_gate，不能以重名模块为由删去两项专用ORM。真正的问题是独立runner之间被needs串行化；同worker内部artifact写入仍需串行。

本轮P4修复：重活改名professional_quality_checks仅依赖授权，与backend_impact_suite并行；保留原受保护professional_quality_gate名称作为轻量汇总，强制核验授权、后端选择、质量worker和Python3.10兼容性。Python兼容性原来未进入该汇总，现push应skipped、其他授权事件应success；失败、取消、非预期skip、缺值全部拒绝。重活采用可取消条件，汇总保持事件/身份约束及失败结果可达；工作流取消仍不产生合并资格。现有测试和job内串行步骤不减少。

工作流16测试（新增100种质量/Python/事件结果组合实际运行shell）、impact15、安全17通过。旧冻结adc69935已完成Quick并签发回执，但调度修改使其回执不再满足新候选发布；仅保留输入未变的产品行为证据，重新冻结的理由是所有者新要求及已证实调度缺陷。实际加速待新远端run，不以理论并行宣称实测。


### 0529 远端前端失败收口（P0/P4）

远端 backend/quality 已通过且同时启动；frontend run 38862350872 首个失败为缺失记录返回409后404，另已有7个场景的帮助按钮ARIA关键错误。受管 local.dev 定向真实ORM复现了 NATIVE_ACTION_GUIDANCE_INVALID / action_guidance.record_identity：缺失记录仍进入动作提示投影。原始失败及结果证据统一索引在 run.frontend_failure_0529。

P0在缓存/记录投影前通过现有ActionResolver解析动作、菜单、XMLID及显式server映射，执行模型ACL→记录存在→记录规则；缺失返回404/RECORD_NOT_FOUND，模型冲突400，真实配置409仍拒绝。前端停止吞动作契约异常后切换模型默认源。ScPopover只暴露官方可见事件状态，FormSection只在帮助内容挂载时建立aria-controls；未修改任何行业/角色语义。P4探针精确约束单次动作契约缺失响应、记录/动作身份和实际缺失页面；不接受409或无关404。仅收集机器原因码，不存业务响应。

B线发现首版使用cache_model作为权威会漏掉menu/XMLID并错查冲突模型，已按真实解析器修复。最终真实ORM2methods覆盖4种缺失入口与冲突模型，通过；纯后端142、探针27、前端错误传播19、布局80、真实Vue组件交互29通过，L1/类型/ lint通过（72既有警告、0错误）。新增ORM用例一度误写不存在菜单，已按正式菜单声明修正，失败日志保留。

本次只改Python处理链及通用消费组件，不改schema、XML或ACL；无需数据库升级，受管测试新进程加载当前代码并事务回滚。受影响集合为缺失记录/错误传播及七类帮助交互；未变导航与调度证据复用。完整前端release车道仅在新冻结候选按既有必需CI运行。主线集成、部署、产品交付尚未完成。

7fbd072e冻结Quick被组装缓存输入摘要门禁拒绝，无回执、未推送。已递增实际ASSEMBLED_CONTRACT_CACHE_VERSION并按完整输入重新锁摘要，保持旧缓存失效；同时把该守卫接入既有handler/projection增量推荐，避免只能在Quick发现。此次修复不改已验的记录/权限/前端行为，复用对应定向结果；补跑缓存所属组装与同层契约检查后再冻结。

653cfaaa Quick继续发现入口等价性守卫阻断：校验为获取resolver构造了第二个ActionDispatcher。改为直接实例化相同ActionResolver，保留唯一投影分发器；不放宽守卫并把入口等价检查加入早期推荐。无推送、无成功回执；收集剩余受影响同层廉价检查后再冻结，避免继续靠Quick逐项发现。

### 2026-10-16: CI redundancy and separate contract performance investigation

Owner requested joint CI failure/efficiency recovery, then explicitly separated
contract-driven performance as a dedicated investigation. Candidate 56f50964 remote
quality passed (quality worker 954s; backend worker 914s, parallel). Frontend run
38869819093 failed its performance phase: login median 3289ms against 3000ms;
company switch median 2277ms against 2000ms. Other measured scenarios met absolute
budgets. The later full functional phase did not run; no functional PASS is inferred.

P4 scope: the candidate ORM runner now shares one isolated installation between
chatter authorization and settlement profile suites, while retaining separate Odoo
processes, tags, logs, count/identity guards, failure propagation and cleanup. The
settlement-only path remains for non-candidate scopes. No threshold, business rule,
ACL or cross-user cache changes. L1 iteration passed; workflow suite 17 tests passed
including six executable shell scenarios proving first/second suite failure cannot
be masked; ORM guard 31 negative/positive checks passed. Actual shared ORM execution passed: chatter 5 and settlement 7 tests, both non-zero, with database/resource cleanup confirmed in /tmp/sce-ci-shared-orm.log. No new Quick or publication while blockers
remain.

Performance investigation sequence (P4 measurement, P0 only if proven necessary):

1. Keep the existing login and company-switch total measurement boundaries and
   budgets unchanged. Login includes login-page loading/filling/authentication/init;
   company switching includes panel interaction/init/UI settlement. Neither metric
   alone measures contract generation. Capture only the existing five measured
   samples and their existing warmups, not the full browser matrix.
2. Correlate request counts/timing for login, session.bootstrap and system.init with
   each sample; retain trace IDs and allowlisted numeric startup_profile timings,
   never passwords, tokens, full response bodies or business values. Bind candidate,
   environment, role, company direction, cache temperature and bundle identity.
3. Separate browser pre-request time, authentication, init server time, request
   completion and post-init UI time. Use actual startup_profile timing/subtiming
   names; label gaps rather than assign unmeasured duration to the backend.
4. Rank measured costs. Read-only review found repeated capability target building
   (capability_registry -> capability_scene_targets) and repeated snapshot reads as
   leads, not established bottlenecks. Prefer request-scoped reuse of proven equal
   inputs. Never reuse permission-filtered contracts across users/company/project,
   data purpose, version or policy changes. No speculative persistent cache.
5. For each proven optimization: nonzero owner-layer tests and permission/cache
   invalidation negatives; rerun the affected samples in the same environment and
   report before/after distributions plus request counts. Final current-candidate
   performance gate and independent review remain mandatory.

Deferred CI candidates: synchronize plus label dispatch cancellation; backend image
coupling to frontend builds; repeated release builds/fixture preparation; coarse
shared-runtime incremental triggers. Each needs source-to-execution proof before
change. A full backend selection in this batch is expected because its shared
workflow/test infrastructure changed; it is not evidence that incremental planning
is disabled. No weakened guards or automatic unchanged-failure retry is authorized.

Backend runtime investigation: shape observation found 1,836,718 nodes under scene_ready_contract; original full traversal about 1.85 million nodes. Five same-process alternating comparisons preserved full reply.data but did not demonstrate stable latency improvement. The primitive recursion change remains unaccepted as a performance fix. Full-chain investigation is specified in runtime_performance_baseline_v1.md; unchanged remote failure remains blocking. L1 iteration passed for current diagnostic batch, not a runtime acceptance verdict.


Backend investigation correction and next ownership (HEAD 56f50964 + dirty scope):
- Earlier empty-parameter observations execute full scene mode, not the actual web registry startup. The 1,854,242-node input / 26,191,732-byte final JSON therefore belongs to full-default diagnostics only. It must not be cited as the login timeout cause. Full scene metadata accounts for 822,210 nodes, per-view blocks 616,914, form surface 253,207. Final response still contains 1,007,747 scene-ready nodes.
- Web startup is now explicit: scene=web, with_preload=false, scene_ready_mode=registry, with=[workspace_home]. This is the default request shape; optional runtime root/route/context and HTTP authentication are not represented by the shell observation. Local first-process call 2038ms / 3285 SQL; subsequent profiled request 836ms / 906 SQL is an instrumented observation, not a latency baseline.
- SQL origin diagnostic confirms 192 action external-ID reads in route authority, 90 native menu-path reads, 72 scene-normalizer target resolutions and 69 scene-provider target resolutions. Both route-authority passes have distinct safety responsibilities (delivery projection and final post-overlay publication reconciliation); removing the latter is prohibited. Three visible-menu exports and one authorized-menu export are distinct projections; never merge visibility and authorization semantics.
- Next P0 work: batch action metadata/XML-ID reads while preserving Odoo selection semantics; batch menu path/target resolution; only then evaluate explicitly scoped same-request fact reuse. Full-scene payload generation/consumer analysis is a separate measured path. No global cache or permission bypass.
- Original SQL attribution probe used a filesystem-path assumption and classified all calls as framework; it is diagnostic-invalid for attribution. Corrected to actual Python module identity and reran that affected mode only. Original log retained /tmp/sce-web-startup-sql.log; valid /tmp/sce-web-startup-sql-owned.log.
- Evidence under artifacts/main-scheduled-ci-closeout-20261016/: local-runtime-deep-shape.json, web-startup-profile.json, web-startup-sql-owned.json. No response body/query arguments/credentials recorded. Diagnostic tests 4 passed; absolute CI failure remains open. No new publication or deployment.

P0 action XML-ID batching implemented in MenuService, preserving the native selector and both permission passes. No schema/XML/ACL changes and no persistent cache. Five alternating same-process finance registry pairs: previous SQL906/current786 each pair, full reply.data hash equal 5/5, median previous495.86ms/current387.01ms. This is backend-only evidence, not the browser acceptance gate. Evidence: menu-batch-paired.json under the existing ignored performance artifact directory, with handler and menu service source hashes.
Metadata pure tests4 + diagnostic tests4 passed. Real ORM original5 passed; independent review found demo-user fixture in bundle test, corrected by moving that one method to demo-owned TestStartupMetadataPerformance and registering its test module. Remaining bundle4 unchanged tests carry their original evidence; only relocated demo method requires execution to establish correct module wiring. XMLID deletion test is metadata invalidation, not permission revocation proof. Review found no P0 semantic blocker. L1 passed before this relocation; final affected L1 pending. No remote publication, merge or deployment.

Relocated demo-owned runtime test executed: 1 test, 0 failures/errors, /tmp/sce-menu-batch-demo-contract.log. This closes its registration/dependency check; no bundle dependency on demo was added.

P0 native menu-path batching: _flatten_policy_menus now resolves enabled menu refs via Odoo native XMLID resolution, checks menu existence in one current-user recordset, reads complete_name without sudo, and retains old per-record behavior for unresolved failures. Source semantics checked against Odoo17 api.Environment.ref and ir.model.data._xmlid_to_res_model_res_id (official source https://github.com/odoo/odoo/blob/17.0/odoo/api.py). No schema/data upgrade or new environment. Six metadata pure cases and four diagnostic cases passed; affected real ORM cases executed independently: bundle path alias/inactive/rename/delete1 PASS, demo finance whole-registry response equality and SQL reduction1 PASS. Earlier unchanged action-XMLID evidence retained; path-specific paired observation and review pending. No broad browser rerun or new Quick.

Path batching completed scoped verification: five alternating same-process pairs all full reply.data equal; SQL786→697 each pair, median378.65→361.87ms. First pair candidate371.63ms vs previous370.05ms, so do not claim every latency sample improved. Independent review no blocker; L1 iteration PASS. These are local finance warm backend observations only; HTTP/auth/browser and formal performance acceptance remain open. Evidence path-batch-paired.json binds both product source hashes. Next measured owner is scene target reference resolution (normalizer/provider), preserving native identity and current-user reads. No merge/deploy/freeze performed.

P0 scene-normalizer batch: _resolve_xmlids_batch uses native lookup and one same-user exists query per referenced model. Target normalization, numeric-ID mismatch correction, missing-reference diagnostics, and existing model-selection semantics remain unchanged. Failed resolution stays on the original per-ref path; no sudo/cache/schema change. Pure normalizer tests5 pass. Real demo finance whole-response equality/query reduction1 pass; registered bundle-owned native-reference/diagnostic fixture1 pass. Old TestSceneNormalizerTargetResolution command executed zero tests (unregistered file), recorded as failed diagnostic and not reused as evidence. The bundle fixture is its scoped replacement for this change, without product->demo dependencies. Independent review identified two-pass iterator exhaustion, fixed by materializing one-shot inputs and returning the normalized sequence to the public resolver; generator/list outcome and diagnostics equivalence test passes. Existing list-path runtime evidence carried forward because the added materialization branch does not run for lists. Paired measurement and re-review pending.

Scene-normalizer optimization closed its targeted batch: five paired requests full reply.data equal; SQL697→630 each pair, median401.33→346.45ms. Independent re-review confirms iterator fix and actual replacement ORM1 PASS, no remaining code blocker. L1 PASS /tmp/sce-scene-batch-iteration.log. Evidence scene-batch-paired.json binds current normalizer and handler sources. Runtime is local demo warm backend-only; do not add medians from different runs or call this frontend acceptance. Next: resolve served frontend/API identity through existing governed entries, then affected login/company-switch browser measurement before prioritizing further micro-optimizations. No freeze, publication, merge or deployment.


Local browser performance observation (HEAD 56f50964 + dirty scope): P4 existing local.dev.frontend and local.dev.up refreshed only the registered sc-local-dev/sc_dev_demo runtime; retained volumes, no module upgrade or fixture reset. Container start/source hashes and served index match candidate. Later identity-only readback additionally checks source mtimes precede service start and entry JS/CSS digests; lazy chunks are not fully inventoried. Refresh log /tmp/sce-runtime-browser-up.log; pre-change identity browser-runtime-before.json in the existing artifact directory. Rollback uses local.dev.up from the recorded original source worktree.

Five completed login-to-WorkspaceHome.ready observations: 1441/1318/1342/1298/1421ms, median1342ms. These use a local development build after two warmups, differ from CI shell-ready and are not release/capacity acceptance. Preserve local-browser-performance.json as status=failed: after these five samples the old company-selector timed out. Fixed only the probe selector to declared WorkspaceContextIndicator; company-only observation found one assigned company and correctly records switching not_run. No permissions/data fabricated. local-browser-company-performance.json and local-browser-identity-performance.json bind the same container, product hashes and served index, allowing reuse of completed login samples. The reporting change does not invalidate unchanged product inputs; no repeat login matrix.

Diagnostic suite5 passes including six runtime identity rejection cases. Independent read-only review found no execution blocker and identified identity limitations addressed above; report acceptance_pass remains false. P4 diagnostics do not own product policy or performance budgets. Affected L1 pending; L3 module upgrade skipped (no schema/data changes), full L4/freeze/remote gates deferred until candidate preparation. Company switching and remote absolute-budget failures remain unproven for this candidate; no mainline/deployment/product-delivery completion claim.

Browser diagnostic L1 completed: make ci.local.iteration PASS (/tmp/sce-browser-performance-iteration.log), git diff --check PASS. Later record-only updates do not invalidate that result. No new runtime or browser execution.

Independent browser-tool review: no S1/S2 blocker. S3 fixes attach response promise rejection handling immediately and always persist report after best-effort context/browser cleanup, including launch/context-creation failure. Diagnostic5 + metadata6 cases pass. Unproven primitive-recursion optimization withdrawn; system_init restored to HEAD and implementation-specific call-count test removed. Equality/copy regressions remain. Earlier backend batching comparisons remain evidence about those experiments, but browser timings now belong to historical dirty candidate only, not final candidate. Local service has not been refreshed after withdrawal; mtime identity guard will reject observation until governed refresh. Do not rerun unchanged browser samples merely for reassurance; next controlled lane measures final candidate. Final affected L1 pending.

Final affected L1 PASS: /tmp/sce-browser-performance-final-iteration.log. Subsequent edits only record this result. Candidate remains dirty/unpublished; no Quick, merge, daily deployment or release claim.


Owner requested systemic diagnosis instead of candidate closeout. Publication/freeze preparation paused; final scoped ORM5 passed (/tmp/sce-performance-final-contract.log) remains valid code evidence, not performance acceptance. P4 diagnostic adds profile_first: exactly one request, no hidden warmup, explicit profiled flag and self-time ranking; unit6 passes. Existing registered local.dev shell only, current cursor rollback, no cache clearing or runtime restart.

New evidence: systemic-current-profile.json records unprofiled first shell request2011.65ms/3009SQL (build_nav1251ms); profiled warm request716.84ms/630SQL. systemic-first-profile.json exposes first-call menu generation: total profiled3555.51ms, app.menu.config generation1581.54ms, collect503 nodes, action_summary873. Code app_config_engine/models/app_nav_config.py first fetches all active menus then searches children per recursive node; leaf heads call action summary again. Confirmed structural N+1 generation, but actual persisted cache trigger/frequency remains unverified. Diagnostic rollback can leave generated cache unpersisted; do not call this live cold-login evidence or compare profiled latency with unprofiled samples.

Independent frontend source review adds two hypotheses: list preflight resolves full contract before data on load (need trace pagination/search triggers); edit form may read record after contract snapshot hydration (need field overlap/freshness evidence). Existing epoch/in-flight startup dedup found, no duplicate system.init claim. Login probe includes navigation/fill/automation; approximately300ms post-response tail is not a measured rendering cost. Next must align actual browser events with request chain and backend stages, then prioritize total wait contribution. No threshold relaxation, no cache across permission scopes, no removal of the two route-authority passes.

Systemic diagnostic L1 PASS (/tmp/sce-systemic-diagnostic-iteration.log); final record-only update reuses it.


P4 cache trigger readback: company1 zh_CN has no persistent projection; existing-dimension readback reports an en_US projection, so shell language is not interchangeable with HTTP context. First cache probe failed before readback because Environment has no with_context; corrected to native api.Environment with unchanged actor/company, seven unit cases pass. Original failure retained. No live recurring-rebuild conclusion from shell-only evidence. Added scoped per-company metadata inventory; no business data exported.

P0 confirmed freshness defect: _generate_from_menus leaves last_generated unchanged when native metadata changes but generated hash does not. Real ORM regression fails on old code (timestamp remains2000); fixes only validation watermark, preserving version/hash/tree and all source/ACL rules. Boundary recorded in run; no schema upgrade, deployment or permission change. Existing registered bundle test owns native fixtures; test rollback. After-fix runtime test pending. Systemic investigation continues; not candidate closeout.

Cache watermark regression: old production fails1 actual ORM (last_generated remains2000), initial fix passes1 actual ORM (/tmp/sce-cache-watermark-after.log). Independent review identified end-of-generation watermark can swallow edits during the build. Watermark now captured before source reads; unchanged hash writes only last_generated. Added actual ORM source-edit-during-generation case, comparing source write_date and snapshot watermark. Two affected methods rerun; pending. This is a conservative correction to existing timestamp mechanism, not proof of all concurrent/late-commit invalidation; no new shared permission cache. Cache-state raw reports archived as systemic-cache-state.json and systemic-cache-dimensions.json. Scope of latter was web cache inventory with language but no company field, so cannot infer that en_US row belongs to company1; diagnostic has since narrowed inventory domain to company1. Original reports never overwritten.

Cache boundary test exposed another source-domain mismatch: generated menu metadata uses full_list=True, while stale detection used native visibility-filtered search. New menu write_date>snapshot watermark assertion passed but stale detector returnedFalse, both inactive and active actionless fixtures; original failures retained in /tmp/sce-cache-watermark-boundaries.log and /tmp/sce-cache-watermark-during-edit.log. Corrected detector to sudo full_list=True, active_test=False, affecting only source invalidation, not user authorization. Final actualORM2 PASS /tmp/sce-cache-watermark-source-domain.log: unchanged content advances freshness without version/tree/hash changes; an active menu edit during generation remains stale. Inactive invalidation now included by declaration but final case did not separately execute that negative; no extra claim. Existing timestamp design does not prove deletion or late-commit concurrency safety; systemic review remains open.

Final source-domain/watermark L1 PASS /tmp/sce-cache-source-final-iteration.log; seven diagnostic unit cases and two actual ORM cases passed. Dirty/unpublished; no live deployment or general performance closure.


Full HTTP chain diagnostic (existing local.dev only, refreshed using local.dev.restart after up reported Running): P4 request shape/status/bytes/elapsed/field-name metadata, no bodies/values/credentials persisted. First chain attempt fails before list because menu is canonical TDesign node, not link; retained local-browser-chain-initial-selector-failure.json. Fixed declared menu/status selectors. Independent review S2 record/edit failure propagation fixed, body parsing moved after measured operation, field names bounded. Node syntax and seven diagnostic unit tests pass.

Observed chain (local development build, automation durations, not SLO): login1516ms including my.work.summary164ms server; initial post-restart summary492ms reveals old limited collector omitted this later request. List3813ms: full contract2889.533ms HTTP/2615ms server/106992bytes; two preferences1853.466ms and836.034ms overlap other work; data180.58ms. Query599ms requests full contract again180.443ms then data158.41ms. Separate record-only observation reuses prior list evidence: record3583ms, contract2716.993ms/1047844bytes; subsequent record read96.767ms then attachment contract414.634ms. MainData94 fields, requested76, overlap46, missing30 includingwrite_date. Cannot delete second read without completeness/freshness proof. Selected record has no enabled unique edit action; edit not_run, no authorization altered.

Source routing: preferences call UiContractHandler internally to obtain list_profile, with full generation fallback. ActionView preference watch includes arriving column options; two requests observed but exact keys not captured, do not claim identical yet. Query path serially resolves contract before data. This shifts priority to full contract compilation/transport and redundant contract generation inside preferences, rather than more isolated startup SQL micro-optimizations. login profile langzh_CN does not prove effective Odoo env language; runtime company1 observed. No publication or overall performance closure.

HTTP-chain diagnostic L1 PASS /tmp/sce-http-chain-iteration.log; subsequent metadata-only result update reuses it. Candidate remains dirty, runtime observation only, no acceptance/deployment-release claim.


Contract-stage continuation: metadata now identifies two identical list_columns preferences (payment.request/action878), 1548.325ms and1087.269ms in pre-copy observation. Persisted list contract671.122ms included post_cache_store246ms; record contract1652.908ms included relation_base_map351ms within business_category_policy410ms and source_assembly274ms. Nested stages must not be summed; warm observations are not improvement evidence. Earlier chain references are now preserved as local-browser-{chain,record}-before-stage-profile.json, with stage observations in local-browser-{chain,record}-stage-profile-before-copy.json.

P0 cache change: handler retains independent per-component deep copies and produces an exclusively owned snapshot through put_generated; cache does not copy that snapshot again. Normal put still isolates input, get still isolates every reader, and factory runs under original RLock to preserve clear ordering. No key/token/TTL/ACL changes, no cross-user cache scope extension, no P1/P2 semantics. Test executes the real handler AST call with deliberately aliased inputs, proves source/reader/component isolation and strips request metadata. Duplicate-copy injection is rejected. Cache12, V2 boundaries142, diagnostic7 and L1 pass; logs in run. Independent review identified lock-order and evidence-binding refinements, both adopted.

Affected local.dev chain after restart binds ui_contract_v2.py and cache-utils source hashes/mtime as well as earlier startup files. Cache-miss list contract HTTP2615.259ms: source_projection1984ms, post_cache_store51ms; preferences1763.84/912.754ms; list automation3503ms. Hot query contract187.218ms. This is not a controlled comparison against prior persisted246ms store observation and does not prove a percentage improvement. It confirms source generation and duplicate preference work remain material; performance closure is explicitly OPEN. First post-change observation omitted changed-file hashes and is preserved as copy-incomplete-source-binding diagnostic, not candidate evidence. No record rerun: changed cache write branch excludes record-bound requests. No publication, mainline integration, daily deployment, or product acceptance in this continuation.


Preference scheduling increment (P0 generic consumer): separated scope-bound parallel GET from first-ready contract application. Subsequent column/policy/context changes still fetch server-sanitized values. Queued SET captures its original scope, currentContextEpoch plus principal/context identity; owner generation gates status updates. GET waits existing writes before refetch and rechecks sequence. Inactive KeepAlive pages invalidate without requesting. Independent review found and closed pending-SET/GET and authority A-B-A races; 15 nonzero tests, typecheck and L1 pass. No schema/new defaults/ACL changes. Actual local.dev frontend build and list/query observation: exactly ONE list_columns GET, all list requests ok. Preference1407.938ms, persisted contract640.606ms, data73.545ms; total automation1454ms is not an SLO or controlled comparison with earlier cache-miss3503ms. No actual preference writes performed by browser; save behavior proven through deferred tests. Original pre-change report retained as local-browser-chain-before-preference-scheduling.json.

P4 extended the existing read-only local.dev observation with preference_profile: exact action ID from browser observation, same demo finance authority, handler hash checked, two profiled calls, cursor commits refused/rollback final; no response values persisted. Nine diagnostic tests pass including failure rollback. Actual profile: first3121.4ms/1117SQL, second1178.8ms/218SQL (instrumented, not latency baseline). BOTH calls generate27 view contracts and24 relation search-dialog contracts merely to return list preference. Second relation injection463.82ms includes search-dialog302.88ms; nested timings not additive. This proves overgeneration beyond process initialization. Next owning fix is a narrow backend list-preference profile projection preserving authoritative policy/permission/finalization equivalence; not a global omission of relation contracts or client-side policy bypass. Systemic performance remains OPEN; no freeze, commit, publication, mainline merge or daily deployment performed.

### Full HTTP / intent-chain attribution (dirty candidate 56f50964)

Owner requested full request/intent/entry/dispatch investigation, not only contract profiling. Reused local.dev sc_dev_demo and original finance principal. P0 generic controller/router observation, P4 metadata-only collector; no schema/fixture/permission changes. Normal JSON responses expose monotonic Server-Timing phases. `dispatch_*` is nested inside `dispatch`, never additive with it. Error, 304 and direct Response paths remain unmeasured.

Actual final list preference HTTP 1186.186ms: context/auth22.552, permission2.147, dispatch1133.938, handler.run1133.804, JSON0.150ms. Router resolution0.005, environment0.043, handler preparation0.019ms. This excludes generic same-db intent dispatch as the main bottleneck; policy lookup through page generation remains architectural overwork. Contract first permission215.173ms vs query2.312ms is a separate open hotspot. Existing meta.elapsed_ms is not an HTTP total (setdefault and before serialization). Proxy/worker/remaining Odoo/transport residual is not attributed.

The backend paired preference experiment retained complete envelope equality6/6, candidate76SQL vs warmed previous218SQL; this does not mean latency acceptable. Follow-up must obtain the exact shared authoritative policy inputs, retain field/action/role constraints, and avoid a second policy source. Broad exception fallback may generate a second contract and erase missing policy; its runtime activation is not yet measured. Token authentication uses an additional cursor for token version; consistency purpose must be established before changing it.

Results and original artifacts are referenced only in run.backend_runtime_investigation.full_intent_chain. Diagnostic12, router envelope9, permission details2 passed; L1 passed. Independent review found no blocker in instrumentation. Browser list/query observed; no write workflow or release acceptance claimed. Earlier collector draft patch failed an exact source-string assertion before writing collector; corrected to actual relative paths, no runtime defect. No freeze, Quick, push, merge or daily deployment for this diagnostic extension.

### Stored preference read: implemented and observed

P0 separates stored user choices from current-page effective policy. ActionView explicitly requests `projection=stored`; backend returns current-user scoped, shape-sanitized values and explicit projection/policy-source markers without resolving a list profile or assembling a page. Existing effective GET and SET remain compatibility paths and are not claimed closed. No new cache or permission bypass.

Consumer requires current-page policy, intersects choices with eligible declared columns, preserves locked restrictions and refuses missing policy/response markers. Independent review found and drove correction of two concrete flaws: hard denial had been represented only as default hidden; an empty authorized option list fell back to original fields. Both are covered through contract parsing, stored projection and final enabled-column calculation. Optional hide stays adjustable; conflicting occurrences halt rather than choose an authority.

Existing local.dev finance/profile browser observation: one stored GET, HTTP43.469ms / handler11.677ms, versus previous effective GET1186.186ms / handler1133.804ms. Request and response modes verified. List and query observed with no failure; record not_run. Single observations are not latency distributions or SLO acceptance. Contract first request2095.412ms remains open. Exact evidence, tests, failures and independent review are in the living run's stored_preference_projection entry. No daily deployment, freeze/Quick, push or mainline integration.

## 契约装配性能接力交接（2026-10-16）

所有者要求本轮完成后停止，由其他执行器接力。本节是当前接力顺序；证据结果只维护于
`.agent/runs/MAIN-SCHEDULED-CI-CLOSEOUT-20261016/run.json` 的
`backend_runtime_investigation.single_source_assembly`，不新开平行台账。

### 接手身份与本轮结果

- 唯一写树 `/home/lidefend/workspace/sce-backend-odoo-local-env`，分支
  `fix/main-scheduled-ci-closeout-20261016`，HEAD
  `56f5096422d967d582c2b25ab9a4bfaa03173534`。现有批次仍 dirty，包含多轮未提交工作，
  不得 reset/覆盖，也不得改另一个主 checkout。本轮未提交、冻结、Quick、发布或部署远端。
- 本轮 P0 修正：V2 仅解引用 `subject=menu` 的显式 `entry.model`；完整 action/model/view
  页面原样消费，不能凭顶层 model 或辅助 entry 再次装配。源缓存命名空间及 assembled
  版本已更新。首次 action 分发补回 `view_id`；finalize 前保留声明的 scene/menu 来源。
- B 线发现的显式视图遗漏与路由来源遗漏均已修复、复核关闭。不是靠恢复第二次装配补输入。
- 当前本地后端已受管重启加载最终源码，前端产物沿用上一轮未变化构建。
  project=sc-local-dev，db=sc_dev_demo，filter=^sc_dev_demo$；finance demo principal/company1。
  浏览器身份以报告内源文件哈希、挂载、启动时间为准，不能把 revision=unknown 说成部署 SHA。
- 本轮 scoped 验证通过：L1 iteration；诊断14、V2边界145、源入口9；真实 Odoo 显式视图
  接受/拒绝2；旧重复装配注入反例确实失败。列表/查询观察无失败，记录页未执行。
- HTTP 首次契约 2095.412→1553.605ms；stored 偏好45.596ms；源装配仍1157ms，首次权限148.869ms。
  热契约176.984→315.920ms，不能掩盖或归因于抖动后宣布通过。cProfile 首次查询1374→1163，
  页面装配2→1，关联弹窗48→24；带 profiler 的时间不能与 HTTP 直接比较。
- 批次结论：本轮限定修复验证完成；整体性能基线未达成、整批交付未冻结；主线集成、远端部署、
  用户验收未完成。不得以偏好读取改善或本轮26%的单次改善宣称平台收口。

### 后续按依赖顺序执行

1. **R1：剩余源装配归因，P4诊断/P0修复，最高优先。**
   先轻量 preflight + `make agent.run.resume`，复用上述 run，不重复全仓/环境盘点。
   使用既有 `local.dev.runtime.performance.observe` 的 `contract_profile` 模式与已观测 action878；
   现有源码绑定、非sudo principal、禁止commit/finally rollback必须保留。必要时最小扩展为
   有界函数/查询归因，记录每个关系目标的生成次数、SQL数、累计时间及调用来源，不导出数据值。
   分清必要的主视图、关系权限、层级策略依赖、关系搜索弹窗和与当前页面无关的模型全字段扩张。
   交付可审计的依赖集合，不能因“列表没展示”直接删 form 或字段。若采用按需物化，必须先有
   后端声明的需求与既有受管请求协议，不能前端猜测或返回空弹窗兜底。
2. **R2：事实/策略/物化边界落地，P0与P1各自拥有。**
   接续 run 中 `policy_architecture` 的 AP1/AP2：先从原生/发布配置解析核心字段、关系覆盖、
   视图族与请求面，再共享有效策略，最后物化页面。确认 project.project/res.partner finalize、
   core_fields block/degrade、relation_entry form override、动态列与权限等价。
   禁止假空 form、仅 tree 投影、模型特判缓存、跳过 ACL 或将标准行业规则放入P0。
   stored GET已经不装配页面，保留；effective GET兼容路径与SET仍有全页面依赖，尚未收口。
3. **R3：缓存所有权与复制链，P0，R1可独立归因后择优实施。**
   热请求profile约30万次deepcopy调用；`get()`已给隔离副本，V2随后再次复制ui_data及assembled对象。
   先证明 hot/persisted 两条路径及 source/contract子对象别名关系，再消除重复复制。
   不删缓存隔离边界，不延长TTL绕过新鲜性，不跨用户/公司/角色复用。
   必须用修改返回值→下次读取不污染、source/contract互不污染、token变化/到期拒绝等反例证明。
   对热请求315.920ms观察做同身份多样本复核；单次回落不能作为问题关闭证据。
4. **R4：首次权限约149ms，P0。**
   沿控制器permission分段的真实调用路径，定位能力/角色/记录规则读取或重复编译。
   保持普通用户、切公司、撤权、禁止关系与未登录负例；不使用sudo或已渲染页面推导权限。
   与R1分开计时，内外嵌套阶段不能相加成总时长。
5. **R5：统一偏好策略消费与真实性能基线，P0消费/P4验收。**
   接续AP3/AP4，明确V2偏好顺序合并与前端stored GET应用的唯一职责，保留保存竞争/epoch屏障。
   先受影响纯测试和非零L2，再受管重启/必要构建，最后精确请求集合观察。
   补有记录的表单读取/编辑、显式非默认视图、project/partner、权限拒绝、冷/热及切公司场景。
   当前record not_run不能当通过，先确认受管demo数据与入口，禁止另建数据库/手工凭据。
   形成同环境同身份请求样本分布、SQL/体积/错误率与阶段成本；沿用正式基线文档的预算，
   不为变绿改预算。容量结论须有对应证据，不能用串行单请求代替。
6. **R6：汇总独立复核与交付。**
   仅当上述明确缺口闭合后，汇总受影响测试与真实行为，更新既有性能基线和本run。
   代码收敛后再做生成物准备、最终提交、一次精确HEAD Quick、B线独立复核及受保护PR。
   最新远端CI需要实际回读，不能继承旧SHA的成功；合并、日常部署、产品验收分别报告。
   当前不为保存交接单独制造发布周期。具体部署继续走既有受管职责入口。

### 证据复用与停止纪律

本轮产品文件仅继续修改 `ui_contract_v2.py`、`ui_contract.py` 及对应边界测试；P4扩展既有诊断
脚本、诊断测试与make/dev.mk。上一轮前端stored消费及竞争测试未改，结果沿用；不得为接力再跑
完整浏览器矩阵。源码或断言变化才失效对应结果，不能仅因新提交刷新全部证据。
所有最新日志已一次归档在 `artifacts/main-scheduled-ci-closeout-20261016/`，精确路径见run。
旧浏览器结果已保存在 `local-browser-chain-before-single-assembly.json`；当前结果仍用
`local-browser-chain-performance.json`，下一次覆盖前先保留并更新run引用。

### R1 执行结果：关系源装配归因（2026-10-16，接力执行器）

身份：写树 `/home/lidefend/workspace/sce-backend-odoo-local-env`，分支
`fix/main-scheduled-ci-closeout-20261016`，HEAD `56f5096422d967d582c2b25ab9a4bfaa03173534`
+ 未提交范围，仍 dirty；未冻结、未提交、未推送、未部署，未改动主 checkout
`/home/lidefend/workspace/sce-backend-odoo`。

方法（P4，最小扩展既有诊断，不改产品代码）：`scripts/verify/local_dev_runtime_performance.py`
新增 `relation_attribution` 模式，用有界包装器记录既有 `PageAssembler._inject_relation_entry_contract`、
`_build_relation_entry_for_field`、`_build_relation_search_dialog_contract` 的生成次数、SQL 增量、
累计耗时与直接调用来源；保留禁止 commit、非 sudo principal、finally rollback 与源码哈希绑定，不导出
任何数据值。入口沿用受管 `local.dev.runtime.performance.observe`
（`PRODUCT_PERFORMANCE_MODE=relation_attribution PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID=878`）。

观测（action878/payment.request，finance demo principal + company1，本地 demo 后端单进程）：

- 进程内首次样本 3921.71ms / 1163 SQL；温样本 523.62ms / 22 SQL（与既有 1163 计数一致）。
- 主视图声明字段 74；关系字段 31 → 24 个关系目标 → 24 个搜索弹窗。
- 关系域 SQL 合计 438（其中弹窗 375、累计 1168.92ms），其余 63 SQL 属非弹窗的关系条目装配。
- 页面可达关系目标 17 个（31 个关系字段中 18 个出现在主视图）；仅由“整模型字段扩张”可达的目标 7 个：
  `mail.activity`、`mail.activity.type`、`mail.followers`、`mail.message`、`rating.rating`、
  `res.users`、`tier.review`（来自 create_uid/write_uid/activity_user_id/reviewer_ids 等审计与动态字段）。
- 未进入主视图字段的关系域 SQL 183，进入主视图 255。
- 层级策略弹窗依赖为 0：本页 `include_relation_search_dialogs` 取默认 True，弹窗按模型全部关系字段生成，
  与请求面无关。
- 单点离群：`res.currency` 弹窗 16 SQL / 548.73ms，第二个独立进程复现 538.45ms；其余弹窗 15–100ms。
- 两独立进程复现：弹窗数 24、弹窗 SQL 375 完全一致；首次样本 3921.71/3865.75ms。

边界与结论：本轮只交付可审计依赖集合，不做按需物化——不删字段、不返回假空弹窗；按需物化必须先有后端
声明需求与既有受管请求协议（R2）。归因证据：
`artifacts/main-scheduled-ci-closeout-20261016/r1-relation-dependency-set.json`、
`r1-relation-attribution.json`、`sce-r1-relation-attribution{,-b}.log`。

验证：`make ci.local.iteration` PASS（coverage=L1_only，receipt=none）；
`python3 -m unittest scripts.verify.test_local_dev_runtime_performance` 15 passed（新增
`relation_attribution` 用例，含 owner 复原与不泄漏断言）；`git diff --check` PASS。

局限：本地 demo 后端单进程观测，非 HTTP/浏览器/SLO/容量证据；阶段嵌套不可相加；温样本响应摘要与首次
样本不同（易变封装身份未隔离）；仅 action878 finance 列表页，不外推其他页/角色/公司。下一步为 R2
事实/策略/物化边界；不得为缩小集合放宽 ACL、层级策略或关系权限。

### R2 执行结果：关系需求声明 → 按声明物化 → 反例与实测收益（2026-10-16，接力执行器）

身份：写树 `/home/lidefend/workspace/sce-backend-odoo-local-env`，分支
`fix/main-scheduled-ci-closeout-20261016`，HEAD `56f5096422d967d582c2b25ab9a4bfaa03173534`
+ 未提交范围，仍 dirty；未冻结、未提交、未推送、未部署，未改动主 checkout
`/home/lidefend/workspace/sce-backend-odoo`。R3（缓存复制）、R4（首次权限）保持独立待办，未被夹进本轮。

交付形态：**后端需求声明 → 按声明物化 → 消费与行为反例 → 实测收益**。产品文件只改
`addons/smart_core/app_config_engine/services/assemblers/page_assembler.py`（P0）及其边界测试；其余为 P4
诊断/受管 local.dev 包装的最小扩展。

#### 第 1 步：`res.currency` ~540ms 归因（P4 诊断）

结论：**不是每次请求成本，而是进程内首次 Odoo 代码翻译加载**，与具体模型无关。

- 冷链：弹窗 648.71ms → view_read 625.09ms → `res_currency.py::_get_view` 550ms →
  `translate._read_code_translations_file` 545ms → `polib.pofile` 491ms。
- 判别对照：同进程首次读取 partner / users / currency 都含该代码翻译加载；重复读取后同一批弹窗降到
  6–17ms。
- 温样本阶段：view_generate 670ms/257SQL、view_read 541ms/127SQL、contract_acl_governance
  368ms/200SQL、field_parse 133ms/112SQL；阶段互相嵌套，**不可相加**。
- 边界：不据此删除 R1 的 7 个扩张型目标，也不把这部分收益归给按需物化。
  证据 `sce-r2-stage-probe{.log,-cold.log,-currency-cold.log,-discriminate.log}`。

#### 第 2 步：P0 唯一关系需求声明

`RELATION_DEMAND_STAGES = (permission, navigation, hierarchy_fact, search_dialog)`；
`PageAssembler._relation_demand_declaration`（配 `_collect_view_field_names`）只从**已解析事实**生成
「来源 → 目标 → 所需能力 → 使用阶段」：

- 来源：已解析原生/发布视图字段、显式 `relation_entry` 覆盖、层级策略字段；另保留
  `model_field_expansion` 作为来源标记，不做模型特判。
- 阶段：`permission`/`navigation` 恒定；`hierarchy_fact` 仅层级策略字段；`search_dialog` 只服务被视图、
  显式覆盖或层级策略引用到的关系字段。
- 声明给出 `dialog_required_fields`，并新增 `stage_timings.relation_entry_overrides` /
  `relation_demand_declaration`，把「声明」阶段从既有 `relation_base_map` 基准中拆出。

#### 第 3 步：先保持接口，按声明物化

- 规则：`include_search_dialog = (field in hierarchy_dialog_fields) or
  (include_relation_search_dialogs and field in dialog_required_fields)`；只有
  `include_search_dialog and can_read` 才构建并下发 `search_dialog`。
- 不可读目标**不下发** `search_dialog`（键缺失，不是空结构），前端既有 fail-closed（`canRead !== true`
  直接返回、`ContractGapError`）不变，禁止返回空弹窗蒙混。
- 接口不变：`can_read/can_create/can_open/create_mode/default_vals/default_from_fields/inline/reason_code/
  delete_policy/options_limit/page_size` 等权限与导航事实全部保留。

#### 第 4 步：反例与消费边界

- `res.users` 专项：4 条可达路径（`create_uid`、`write_uid`、`activity_user_id`、`reviewer_ids`）全部
  `can_create=False`、`create_mode=disabled`、`default_vals=[]`、`inline_create=False`，并保留
  `can_read/can_open/reason_code`；不存在默认值、创建或动态可见消费者，因此只取消未被消费的弹窗构建。
- `mail.activity`/`mail.activity.type`/`mail.followers`/`mail.message`/`rating.rating`/`tier.review` 只丢
  `search_dialog`，权限与导航事实保留。
- 层级依赖：未在树视图渲染的层级策略字段仍物化弹窗（`read_fields`/`order`），后端层级策略消费点不变。
- 显式视图覆盖：离屏但有 `relation_entry` 覆盖的字段仍要求弹窗。
- 治理分支：`project_id` 保留 `RELATION_ENTRY_OVERRIDE_AUTHORITY_DENIED`、`partner_id` 保留
  `RELATION_ENTRY_NOT_PUBLISHED` 且弹窗不变；`sc.business.category` 专用弹窗分支保留。
- 消费者矩阵：前端唯一 `search_dialog` 消费者是打开搜索弹窗路径
  （`relationDescriptor.ts` → `useRecordRelationships.loadRelationSearchColumns/fetchRelationSearchRows`）；
  `canRead!==true` 直接返回 `[]`，缺弹窗时回退声明的 V2 tree 契约；未渲染字段两条路径都不会运行。

#### 第 5 步：归一化比较与实测收益

同一产品代码、同一 principal（finance/company1、action878、`payment.request`）的三次探测：

| 观测 | 弹窗数 | SQL | 耗时 |
| --- | --- | --- | --- |
| 改动前 `sce-r2-demand-before.log` | 24 | 1163 | 2006.39ms |
| 改动后 `sce-r2-demand-after.log` | 17 | 1041 | 1845.68ms |
| 同代码重建改动前语义 `sce-r2-demand-baseline-reconstructed.log` | 24 | 1163 | 2008.92ms |

- 重建忠实性：before 与 reconstructed 的 `relation_base_sha256`（95b0de6b…）、`relation_entry_sha256`
  （93c1f8db…）、`search_dialog_sha256`（e9daa7b7…）三处摘要**完全相同**。
- 权威关系面：字段集 31==31；`relation_base_surface` 相等；**非弹窗 relation_entry 差异 0**；
  `dialog_present_fields` after=18 / baseline=31，baseline-only 13、after-only 0；18 个共同字段的弹窗载荷
  完全一致；声明相等（能力计数 `{hierarchy_fact:0, navigation:31, permission:31, search_dialog:18}`）。
- 等价口径：`dialog_present_fields == relation_fields_in_view == dialog_required_fields`（18）。
- 被排除 13 字段（全部未在已解析视图/覆盖/层级策略引用）：`activity_ids`、`activity_type_id`、
  `activity_user_id`、`create_uid`、`message_follower_ids`、`message_ids`、`message_partner_ids`、
  `rating_ids`、`review_ids`、`reviewer_ids`、`settlement_currency_id`、`website_message_ids`、`write_uid`；
  完全消失的 7 个目标：`mail.activity`、`mail.activity.type`、`mail.followers`、`mail.message`、
  `rating.rating`、`res.users`、`tier.review`（`res.currency`/`res.partner` 因其他字段在视图内保留）。
- 差异口径：只排除登记的请求身份（`_VOLATILE_ENVELOPE_KEYS`），保留并比较 `contractSha256`/`sourceSha256`；
  全信封 diff 的 6 条差异路径全部落在 `/data/meta/lifecycle/**` 内容摘要。
  有界限制：`envelope_path_digests` 深度 6、每层 400 节点。

受影响 HTTP（受管 `make local.dev.restart` 后，`local.dev.runtime.performance.browser` 新增有界
`relation-dialog` 范围；**未跑完整页面矩阵**）：

- 列表 action878 `ui.contract.v2 action_open`：交付的关系列只有 `attachment_ids`，其 `search_dialog`
  存在；该面上其余关系字段本就未交付。
- 记录表单：交付 18 个关系字段，**全部带 `search_dialog`**。
- 关联行为：声明的 many2one 面板动作「搜索更多」在首个视图内字段（`project_id`）成功打开搜索弹窗，
  7 个中文表头、15 行、无 `ContractGapError`，触发一次 `api.data project.project list`
  （HTTP 36.087ms / 服务端 15ms）。
- 计时：记录表单契约温请求 HTTP 1075.169ms / 服务端 1027ms；同请求进程首次为 1896.825/1845（代码翻译冷启动），
  与进程内 2007→1846 收敛一致。

#### 验证（本轮）

- `make ci.local.iteration` PASS（coverage=L1_only，receipt=none）；`git diff --check` PASS。
- L1 守卫：`verify.frontend.contract_basis.unit` 15 passed（open_defects=0）；
  `verify.frontend.relation_entry.contract_guard` 23 passed；`professional_relation_lifecycle` 7 passed；
  `hierarchical_worksheet` 10 cases passed。
- L2：`test_relation_entry_contract` 23 passed；`test_ui_contract_id_boundaries` 9 passed；
  `verify.business_config.formal_list.unit` 145/12/62/5 passed；
  `test_page_assembler_view_orchestration_versions` 23 passed；
  `verify.unified_page_contract.v2.runtime` 23/126 passed + guard score=6；
  `scripts.verify.test_local_dev_runtime_performance` 18 passed。
- ORM：`smart_core` 定向批次（TestRelationEntryOverrideFailClosed / TestRuntimeViewContractFailClosed）
  16 post-tests、0 failed。
- 已知既有失败（非本轮引入、不为变绿而修改）：`smart_construction_core` 全类批次 19 failed / 19 error
  （菜单 xmlid、业务域、税务中心、投标报名字段等 P1 漂移）；把 `page_assembler.py` 还原到 HEAD 重跑三个代表
  用例（`sce-r2-orm-sc-core-reverted-3.log`）复现同样失败；R2 相关的
  `test_expense_deposit_application_contract_scopes_business_category_relation` 通过。

#### 局限与边界

- 本地 demo 后端单进程探测 + 单页有界 HTTP 观测，非 SLO/容量/跨角色证据；阶段嵌套不可相加。
- 单 principal、单 action（878）；只做受影响面无界，不外推其他页、角色、公司。
- 本轮**不**宣布整体收口：热请求波动、缓存复制（R3）、首次权限（R4）、统一偏好消费（R5）与最终独立复核/
  Quick/合并/部署（R6）保持独立待办；未冻结、未提交、未部署。

### R2 追加收口：装配缓存身份守卫重钉（回答「是不是弹窗契约有问题」）

本轮主动补跑 L1 建议目标时，`verify.unified_page_contract.v2.assembler` 失败。**结论：弹窗/关系契约本身
没有问题，这不是弹窗断言失败。**

守卫守的逻辑：`check_assembled_contract_cache_pin` 把 handler 实际服务的
`ASSEMBLED_CONTRACT_CACHE_VERSION` 字面量与一段「装配输入代码」的 sha256 绑定成同一个 pin。装配结果是代码
产物，一旦代码变了而 pin 不动，交付面就可能继续吐旧装配；漂移即 fail-closed，迫使作者显式重钉，而不是让缓存
把改动吞掉。守卫报的两条都只关于这个身份，不涉及 `search_dialog`/`relation_entry` 内容。

归因证据（逐字节对照，非推测）：

- 原 12 个输入里**只有** `addons/smart_core/handlers/ui_contract_v2.py` 与 HEAD 不同（本批次单源装配轮改了
  版本字面量 `authoritative-record-preflight → single-source-assembly`、`put` → `put_generated`、菜单入口
  只解引用 `subject=menu`）；其余 11 个输入与 HEAD 完全一致。
- 用 HEAD 的该文件字节 + 记录字面量重算摘要 = 记录值 `4cc78993…`；用当前字节重算 = 失败信息给出的
  `5c95b0a6…`。即摘要漂移可完全归因于该文件。
- `page_assembler.py` 原本**不在**输入集合内，所以本次失败不是 R2 弹窗改动触发的；反过来也暴露了一个真实
  缺口：v2 handler 在 `_handle_contract` 内装配/写缓存前经 `PageAssembler` 注入业务类别策略与关系条目
  （`_inject_business_category_form_policy` → `_inject_relation_entry_contract`），它是真实装配输入却未被
  纳入指纹。

同一批次内的处置（未放宽任何断言，只收紧）：

1. 守卫 `ASSEMBLED_CACHE_VERSION` 同步为 handler 实际值
   `ui-contract-v2-2026-10-16-single-source-assembly`（handler 不动，理由见下）。
2. `ASSEMBLED_CACHE_INPUTS` 纳入
   `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py`；装配前的 source 契约属于另一层，
   仍由持久化 runtime source asset 的 token 负责其新鲜度。
3. 由守卫自身算法（`_assembled_cache_digest`）重算
   `ASSEMBLED_CACHE_INPUTS_SHA256 = 7b94190390459fb847947e18ab7bec850aec3d546d7b575dc965cc069a46fbe7`（13 个
   输入，不手算、不猜）。
4. `scripts/verify/frontend_dev_incremental.py`（含其测试）把 `page_assembler.py` 路由到
   `verify.unified_page_contract.v2.assembler` 等四个后端目标，避免该漂移只能在 Quick 才被发现。

反向验证（只读、内存扰动，不写任何仓库文件；`sce-r2-host-assembler-guard-reverse.log`）：baseline 无错；
扰动 `page_assembler.py` 字节 → 摘要漂移 fail-closed；handler 服务未登记字面量 → 字面量失配 fail-closed；
还原后无错。fail-closed 机制对新纳入的输入同样成立。

为什么没有再 bump handler 字面量：字面量表达的是「装配代码身份」，本批次相对上一个被固定的身份（HEAD 的字面量）
已经更换。经核实，装配后的载荷只存在于进程内
`CONTRACT_PROJECTION_HOT_CACHE`（TTL 30s，`_assembled_v2` 仅此一处写入），而持久化的 runtime source asset 存的
是装配**前**的 source 契约：v2 的关系/策略注入发生在该写入之后，且 stored 投影显式传
`include_relation_search_dialogs=False`，因此 R2 没有可跨进程复用的旧身份需要作废；守卫现已跟随 handler 实际
字面量，任何后续输入变化（含 `page_assembler.py`）都会 fail-closed 并要求重钉。

产品源码哈希未变，本轮 R2 运行证据不被作废：
`handlers/ui_contract_v2.py = 09b79bd1…`、`assemblers/page_assembler.py = 99dddef2…`。

结果：`make verify.unified_page_contract.v2.assembler` PASS（sources=4）；
`verify.frontend.dev.incremental.unit` 30 tests OK；`make ci.local.iteration` PASS（dirty，coverage=L1_only，
receipt=none）。本轮仍 dirty，未冻结/未提交/未推送/未部署；R3/R4/R5/R6 仍为独立待办，不受本轮处置影响。

### R2 收尾追加：持久 source 缓存身份闭环 + 证据对账（2026-10-16，接力执行器）

上一节「装配前 source 契约由持久化 runtime source asset 的 token 负责新鲜度」需要收紧一处，并补齐
反例。结论：**弹窗契约没有问题；本轮发现并修掉的是持久 source 缓存的代码身份覆盖缺口。**

**（1）R2 方法相对 source 缓存写入的位置。**
新 P4 只读探针 `scripts/verify/local_dev_runtime_cache_identity_probe.py`（wrapper
`make local.dev.runtime.cache_identity.probe`）对 action878 的 list 与 form 两个面记录事件序列：

| seq | 事件 | 位置 | 备注 |
| --- | --- | --- | --- |
| 1 | `source_asset_read`（miss） | `ui_contract_v2.py:_handle_contract:683` | |
| 2 | `relation_entry_inject` | `page_assembler.py:assemble_page_contract:646` | **R2 声明/物化，写之前** |
| 3 | `source_asset_write`（persisted） | `ui_contract_v2.py:_handle_contract:759` | |
| 4 | `relation_entry_inject` | `ui_contract_v2.py:_inject_business_category_form_policy:1657` | 仅 form 面，写之后 |

即：R2 在 `assemble_page_contract:646` 的物化**先于**持久 source 写入，所以持久载荷本身携带 R2 关系面
（探针实测持久 payload：`fields_with_relation_entry=31`、`fields_with_search_dialog=18`）。上一节
「R2 没有可跨进程复用的旧身份需要作废」只对 **handler 字面量**成立；持久 source 资产是另一条缓存，
其新鲜度**只由 source token 决定**——探针确认该资产**没有到期列**（`ttl_not_involved`：拒绝只按
`asset_version`（source token）+ status，不是 30 秒到期）。

**（2）token 是否覆盖代码身份 → 发现缺口 → 修复。**
`build_projection_source_token` 把 `["code_fingerprint", contract_code_fingerprint()]` 作为
`runtime_source` 行绑定进 token，因此代码身份变化应当改变 token。但旧的 `contract_code_fingerprint()`
身份行是 `(path, mtime_ns, size)`：**等尺寸、还原 mtime 的内容改写不会改变 token**，旧 source 会继续命中，
且该持久资产没有 TTL 兜底。

反例（同尺寸内容改写 + `utime` 复原 mtime；`old source cached → code identity changes → old source rejected`）：

- 修复前（`sce-r2-cache-identity-pre.log`）：`token_unchanged_by_content=true`、
  `legacy_row_tuple_unchanged=true`、**`old_source_still_served=true`**。
- 修复后（`sce-r2-cache-identity-post.log`）：`token_unchanged_by_content=false`、
  **`old_source_still_served=false`**、`old_source_rejected_after_identity_change=true`、
  `same_size_content_change_reaches_the_token=true`；`mtime_only_change` 同样变化并拒绝。

修复（P0，最小同层）：`addons/smart_core/utils/load_contract_response_cache.py` 的身份行改为
`path + mtime_ns + ctime_ns + size`，并写清理由——任何内容写入（含 `utime`）都会推进 ctime，故同一
`(mtime, size)` 下的内容变化仍会改变 token。为让反例进入受治理门禁，`test_load_contract_response_cache.py`
新增自包含单测 `TestContractCodeFingerprintIdentity`（临时身份根 + 复位进程内指纹缓存）：旧 `(mtime,size)`
行下指纹不变（测试会失败），ctime 行下指纹变化（测试通过）。

> **2026-10-17 取代（所有者裁定）**：本段的「身份行改为 `path + mtime_ns + ctime_ns + size`」不再是当前实现。
> 所有者的裁定是「`ctime` 仍只是文件变化检测信号；若直接充当代码身份，不能称为可靠的内容身份闭环，正式部署
> 仍应绑定不可变构建或内容摘要」，因此让 `ctime` 直接充当身份属判定驳回项。历史结论与本段保留不改，当前实现
> 见下方「代码身份内容绑定（2026-10-17）」一节。

**守卫范围判定**：`load_contract_response_cache.py` **不在** 13 个 `ASSEMBLED_CACHE_INPUTS` 内，守卫注释已
声明「装配前 source 契约是另一层，由持久 source asset token 覆盖」，因此
`ASSEMBLED_CACHE_INPUTS_SHA256` / `ASSEMBLED_CONTRACT_CACHE_VERSION` **无需重钉**；
`make verify.unified_page_contract.v2.assembler` 在当前 dirty 树重跑 **PASS（sources=4）** 佐证 pin 完好。

**（3）本轮验证（L1/L2，dirty、未冻结）。**
`git diff --check` 干净；`make ci.local.iteration` **PASS**（dirty，coverage=L1_only，receipt=none）；
`make verify.business_config.formal_list.unit` **PASS**：Ran 145 / 13 / 62 / 5 OK（缓存模块 12→13）；
`make verify.unified_page_contract.v2.assembler` **PASS**（sources=4）。探针 exit=2 属设计（`odoo.shell.exec`
拒绝 commit 的 fail-closed 守卫在报告打印后触发），不是失败。

**（4）证据对账（同一 run，不重跑未变化项）。** R2 六项问询已全部落在
`backend_runtime_investigation.relation_demand_boundary`：声明者/消费者（`declaration` /
`counterexamples.consumer_matrix`）；24→17 弹窗及保留原因（`three_way_comparison` / `benefit`）；层级依赖、
隐藏但必要关系、权限拒绝、显式视图、project/partner 治理与 `res.users` 四路径消费者（`counterexamples.*`）；
SQL/源装配/HTTP 前后（`three_way_comparison` / `http_observation`）；`res.currency` ~540ms 归因
（`step1_currency_attribution`：进程首次 code-translation 加载，非每请求成本、不归因按需物化）。
新增 `source_cache_identity_closure`（身份闭环）与 `evidence_reconciliation`（对账索引）。
守卫 PASS 不替代上述结果，这里只做对账与缺口补齐，不重复跑未变化验证。

**（5）阶段状态。** 仍 dirty，未冻结/未提交/未推送/未部署；R3（`cache.get()` 之后的重复复制所有权链）
为下一个独立待办，R4/R5/R6 保持独立。不提前 Quick、不扩浏览器矩阵、不宣布整体收口。

### R3 执行结果：`cache.get()` 之后重复复制的所有权收口（2026-10-16，接力执行器）

证据维护于同一 run 的 `backend_runtime_investigation.source_handoff_ownership_closure`，不新开台账。

**（1）先证明所有权与别名关系（未动代码）。**
`ui_contract_v2` 取到 `cached_source` 的两条路径都已经是**独占**对象图：

- 热路径 `CONTRACT_PROJECTION_HOT_CACHE.get()` 在读取时 `copy.deepcopy(response)`（受治理反例
  `test_hit_returns_isolated_copy`：改动嵌套列表后条目不变）。
- 持久路径 `get_runtime_source_asset()` 用 `json.loads(record.payload_json)` **每次重建**对象图；
  且 handler 使用前还会把一份独立副本 `put` 进热缓存。
- `_assembled_v2` **从不持久化**（持久 payload 只有 `source_type/ui_data/ui_meta`），因此只可能来自
  热缓存，即来自 `get()` 的隔离副本。

断言矩阵（对 handler 真实 payload 形状，进程内只读验证）：`get()` 结果 ≠ 条目；`ui_data`、`ui_meta`、
`_assembled_v2.contract`、`_assembled_v2.source_contract` 逐一不别名；对这些对象就地修改后，条目与下一次
`get()` 均不受影响。结论：`get()` 之后 handler 再做 `deepcopy` 属于**重复复制**。

**（2）按证明删除（最小、同层，P0）。**

- cached-source 分支：`deepcopy(cached_source["ui_data"]/["ui_meta"])` → 直接赋值（本请求拥有该图，
  就地修改安全）。
- assembled-hit 分支：`deepcopy(assembled_cached["source_contract"]/["contract"])` → 直接赋值（该图在
  seal 之后即被丢弃）。

**保留**：缓存隔离边界（`get()` 仍每次复制）、持久 payload 仍由 `json.loads` 重建、TTL、source token、
uid/角色/公司/语言缓存键、写入路径 :1127 的生产者复制（缓存绝不接收请求内活对象）。

**识别但本轮不夹带**：miss 路径 `ui_contract_v2.py:751` 的 `deepcopy(ui_data)` 是**必要**的（`ui_data`
之后会被 record overlay 与各注入就地修改），但 `put()` 又对这份刚生成的 payload 复制一次；这一处需要独立的
「owned put」API，属于另一条改动，保持为后续项。

**（3）保留反例（受治理 L2）。** 返回值污染 `test_hit_returns_isolated_copy`；跨请求污染
`test_handler_generated_snapshot_keeps_component_and_request_isolation`；身份变化
`test_source_change_invalidates_entry` + `test_ttl_expiry_invalidates_entry` + `TestContractCodeFingerprintIdentity`。
本轮新增 `TestHandlerHandOffOwnsTheGetCopy`：AST 守卫禁止 handler 再次 `deepcopy(cached_source/assembled_cached)`
（反向注入旧写法会被判失败），并断言就地移交不污染条目与下一次读取。

**（4）装配缓存 pin 随之重钉（fail-closed 机制，非放宽）。** 改动的 `ui_contract_v2.py` 既是
`ASSEMBLED_CACHE_HANDLER` 又是 13 项输入之一，守卫按设计拒绝。处置：handler 与守卫的字面量同步为
`ui-contract-v2-2026-10-16-owned-source-handoff`，并用守卫**自身算法**重算
`ASSEMBLED_CACHE_INPUTS_SHA256`（不手算）。只读反向验证：baseline 无错；扰动 `page_assembler.py` 字节 →
fail-closed 并给出新摘要；handler 未登记字面量 → fail-closed；还原 → 无错。

**（5）运行期等价（有界观测，一次重启 + 一次 relation_demand_probe）。** 与 R2 after 对比：
`dialog_build_count 17 == 17`、`dialog_target_count 17 == 17`、`sql_count 1041 == 1041`、`relation_field_count 31`、
`declared_field_count 169`、`view_field_count 74`，且 `relation_base_sha256` / `relation_entry_sha256` /
`search_dialog_sha256` / `declarations` / `dialog_present_fields` / `dialog_targets` / `relation_surface` / `owner_hashes`
**全部相等**；`dialog_builds` 17 行结构相同、仅时延不同。差异仅来自设计上变化的装配缓存版本字面量与 source token
（envelope 摘要因此变化），总耗时 1845.68→1829.68ms 属波动。结论：**行为保持、R2 收益（24→17 弹窗 / 1163→1041 SQL）保留**；
本轮**不宣称** R3 的时延收益——单次首请求观测并不隔离被删的热路径复制，热请求 deepcopy 计数画像属于 R3/R5 验收。

**（6）验证（dirty、未冻结）。** `git diff --check` 干净；`make ci.local.iteration` PASS（L1_only）；
`make verify.unified_page_contract.v2.assembler` PASS（sources=4）；`make verify.business_config.formal_list.unit`
PASS 145/15/62/5；`make verify.unified_page_contract.v2.runtime` PASS（23+126，score=6）。

**（7）身份说明。** R2 曾记录 `ui_contract_v2.py` 未变（`09b79bd1…`）；R3 改了该文件，故 R3 的
`contract_handler_sha256 = eb599824…`，R2 运行期证据仍绑定 R2 阶段身份，R3 以第(5)项的等价性重新覆盖
受影响面。仍 dirty，未冻结/未提交/未推送/未部署；R4（首次权限 ~149ms）、R5（统一偏好消费 + 真实性能基线）、
R6（独立复核与交付）保持独立待办，不夹进本轮，不提前 Quick、不扩浏览器矩阵、不宣布整体收口。

### R4 执行结果：首次权限 ~215ms 归因（2026-10-16，接力执行器）

本节回答「首次契约权限 215ms vs 热请求 2.3ms 究竟是一次性初始化还是每请求冗余」。结论与反例只维护于
同一 run 的 `backend_runtime_investigation.permission_gate_attribution`，不新开台账。

**（1）诊断手法（P4 只读）。** 新增 `scripts/verify/local_dev_runtime_permission_probe.py`，用忠实 shim 替换
`odoo.http.request`，直接运行**未修改**的 `check_intent_permission(ctx)`；以 `__wrapped__` 对未改动的 helper 计时/计数。
`registry.clear_cache()` 只清该 throwaway shell 进程，绝不触碰常驻 worker。principal
`smart_construction_demo.user_demo_role_finance` uid=45 company1 sudo=false；intent `ui.contract.v2` action 878 `action_open` menu_id 559。

**（2）归因结果（探针 7 号报告）。**

- 冷启动（清 registry 缓存后，带 `menu_id`）门耗时 **132.648ms**；无 `menu_id` 仅 **0.505ms**。
- 冷启动主成本 = `_published_menu_decision` **131.941ms** == `build_runtime_route_authority` **131.906ms** ==
  `_build_runtime_route_authority` **130.431ms**（`published_route_authority_is_the_cold_owner=true`）。
  内部：`MenuService.build_nav` 58.207、`build_route_authority` 56.242、`ProductPolicyService.get_policy` 7.785、
  `_normalize_delivery_nav_refs` 5.68、`user_group_xmlids` 1.368、`principal_group_signature` 1.431、
  `_load_platform_release_gate` 0.888；`check_access_rights` 133 次。
- **一次门内恰好 1 次构建**（冷 `with_menu_cold=1`，热 `warm_1=0`）→ `no_redundant_duplicate_authority_build_in_one_gate=true`。
- **热请求带 `menu_id` 中位 1.658ms**（样本 1.492–1.692），**无 `menu_id` 中位 0.407ms**（0.267–0.416）；
  热请求唯一主要成本是 `principal_group_signature` ≈ 1.049ms（即 `user_group_xmlids`）。
- 进程首次触碰（缓存已热）2.373ms。**结论：观测到的 215ms 控制器段 = 发布路由权威的首次构建 +
  进程首次模块/ORM 冷，一次性成本，不是每请求成本，且无冗余重复调用 → R4 无优化空间，不改产品代码。**

**（3）边界反例（探针实测）。**

| 反例 | 期望 | 实测 | 说明 |
| --- | --- | --- | --- |
| `unpublished_menu_pair` | 拒绝 | 拒绝 ✓ | `AccessError`：无权访问该菜单 |
| `nonexistent_model` | 拒绝 | 拒绝 ✓ | `MissingError`：模型不存在 |
| `synthetic_navigation_menu` | 允许 | 允许 ✓ | `menu.navigation` 设计上不走动作门 |
| `action_group_excluded` | 拒绝 | **未拒绝 ✗** | 既有缺口，见（4） |
| `company_scope_switch` | 拒绝 | **未执行** | demo finance 仅一个公司（`second_company_id=null`），如实登记为未覆盖 |

**（4）登记一个既有 P0 授权缺口（不在 R4 内顺手修）。** `_resolve_action` 在 `action_type` 缺失时先试
`ir.actions.actions`，而该模型**没有 `groups_id`**，`getattr(action,"groups_id",None)` 返回 None →
跳过 groups 交集校验（action 72 的 `ir.actions.act_window.groups_id=[4]` 未被强制）。真实 `ui.contract.v2
action_open` 请求确实不传 `action_type`，故走此分支。**该行为在 HEAD 即存在**（`git show
HEAD:addons/smart_core/security/intent_permission.py` 同一段），非本轮引入。影响面实测：`act_window_total=738`、
`act_window_with_groups=419`、`act_window_group_excluded=174`；但 `action_72_published=false`、
`excluded_but_published=[]`、`published_action_count=45` → 本样例中组排除动作均不在该 principal 的已发布导航内，
**尚未构成当前可利用漏洞，但门本身对该分支不设防**。处置：登记为独立 P0 安全边界待办，需单独授权与其自身反例集。

**（5）验证（dirty、未冻结）。** 探针自带受治理单测 `scripts/verify/test_local_dev_runtime_permission_probe.py`
**8/8 PASS**（拒 commit、绑定 `sc_dev_demo`、非 sudo、恢复所有被打补丁的 hook、只归因声明场景、守卫承重、仅导出声明键）；
`make ci.local.iteration` PASS（`change_state=dirty, coverage=L1_only, receipt=none`）；探针运行 L3 PASS。
本轮只新增 P4 探针/runtime wrapper，未改动任何产品文件（`security/intent_permission.py` 与
`delivery/runtime_route_authority.py` 哈希与 HEAD 一致；`page_assembler.py` 仍为 R2 的 `99dddef2…`）。

**（6）边界与下一步。** R4 为限定归因，不是 SLO/容量/跨角色/发布结论；216ms 段里除 132.6ms 权威重建外的
其余部分为进程首次模块/ORM 冷，探针已先付，未再重测（如实登记）。R5 需一次有界观测同时覆盖 R3 热缓存收益、
R4 权限成本与 R2 当前 HTTP（固定用户/公司/动作/参数，区分首次与热请求，记录样本数、分布、SQL、阶段耗时与错误），
并解释此前热请求 176.984→315.920ms 的异常；随后收口偏好职责；R6 才独立复核/冻结/交付门禁。miss 路径双重复制继续登记。
仍 dirty，未冻结/未提交/未推送/未部署，不提前 Quick、不扩浏览器矩阵、不宣布整体收口。

### R5 执行结果：热路径/权限/HTTP 统一有界观测 + 热请求异常归因（2026-10-16，接力执行器）

证据只维护于同一 run 的 `backend_runtime_investigation.r5_unified_observation`，不新开台账。身份未变
（写树 `/home/lidefend/workspace/sce-backend-odoo-local-env`，HEAD `56f50964…` + dirty 范围；未冻结、未提交、
未推送、未部署；未动主 checkout）。

**（1）手法（P4 只读，不新增 API、不改产品文件）。** `scripts/verify/local_dev_runtime_contract_request_probe.py`
扩展为一次有界观测：固定身份 `user_demo_role_finance` uid45/company1（`sudo=False`）、固定请求
`ui.contract.v2` op=`action_open` action=878 menu=559，重复取样看分布而不是最快样本；忠实 shim `io.request`
与 `intent_router.request`，直接跑真实 `check_intent_permission` + `route_intent_payload`。本轮新增三件判别工具：
`authority_and_cache_lookup` 的内部成员计时、`gc.callbacks` 采集，以及**配对同进程的 gc 关闭对照组**
（同一请求、同一进程、仅关闭自动回收）。入口沿用受管 `make local.dev.runtime.contract_request.probe`。

**（2）一次观测同时给出的三件事（7 号报告）。**

| 项 | 结果 |
| --- | --- |
| R3 热缓存收益 | 24/24 温样本 `assembled_v2_hot_cache_hit`，投影身份恒 `11e770c4b2ae`、源 `8c5d1259eb77`，SQL 恒 25、deepcopy 恒 26 |
| R4 权限成本 | 温请求 12 样本中位 **2.890ms**（2.660–3.305）；冷重建（清 registry+热缓存）**133.308ms**，与 R4 归因 132.648 交叉印证 |
| R2 当前 HTTP | 沿用既有 Server-Timing，不重跑：list 契约冷 **2095.412→1553.605ms**（source_projection 1566→1157）；query 契约温 **176.984→315.920ms** |

温请求结构（中位）：dispatch 83.465ms = `authority_and_cache_lookup` 60ms
（`CONTRACT_PROJECTION_HOT_CACHE.get` 38.1ms 隔离副本 + `_validate_scene_action_binding` 16.4ms +
`build_projection_source_token` 7.8ms）+ `v2_projection_and_seal` 22ms（`seal_runtime_contract` 23.3ms）。
首次（miss）1504.369ms / 682 SQL / 90 deepcopy；身份变体 miss 773.611ms / 210 SQL，同身份重启即回到 85.147ms / 25 SQL。

**（3）R3 收益的直接测量（不是推断）。** 在活的缓存条目上重放「handler 过去会做的两次复制」：
`_assembled_v2.source_contract` 15.614–18.628ms（中位 16.954）、`_assembled_v2.contract` 1.878–2.489ms
（中位 2.035）→ **约 19.0ms/温请求 = 温 dispatch 中位的 ~23%**。保留的隔离副本仍在（`get()` 约 36–38ms/请求），
未延长 TTL、未跨用户/公司/角色复用。只给「被删除工作的实测成本」，不宣称旧版本的墙钟 A/B。

**（4）热请求 176.984→315.920ms 异常的归因（本轮必答项）。** 结论：**是 CPython 二代 GC 暂停，不是缓存语义或
产品代码回归。**

- 排除：两次浏览器样本都是 `hot/assembled_v2_hot_cache_hit`（非 hit→miss）；温样本 deepcopy 恒 26（与 R3 删除的
  复制无关）；SQL 恒 25（无额外查询）；permission 2.132→1.990ms（无权限变化）。
- 正证：同一进程内离群落点会**变**——`hot_10` 落在 `authority_and_cache_lookup`（163ms vs 稳态 57–62ms，seal 正常
  22.3ms），`hot_4` 落在 seal（`seal_runtime_contract` 135.4ms vs 稳态 21.4–23.6ms，lookup 正常 60ms）；幅度恒
  102–114ms。早期 2/3/5 号落在 lookup，6/7 号 lookup 与 seal 都出现——即「阈值被跨过时哪个阶段在分配内存」。
- 反例：离群样本 `gc_ms` 114.787 / 106.308 且恰有 1 次二代回收，与超中位的 114.554 / ~102ms 吻合；
  **配对关闭自动回收后，同一请求的最大超中位只剩 6.706ms，`gc_ms` 恒 0**。
- 浏览器读数：after 单样本把 +133ms 放在 `v2_projection_and_seal`（43→176），而 `authority_and_cache_lookup` 未变
  （80→81）——属同一类停止在更大堆上落在 seal。两次浏览器值都是**单样本**，不是分布；探针温请求 p95 187.25ms，
  该量级的热离群仍在观测分布内。
- 边界：`gc.freeze()`/关回收属运行时决策，需要自身证据；本轮登记为独立性能项，不改产品代码。

**（5）易变身份与限制。** 24 个温响应在 113916 字节封套上有 20 个不同 sha256（trace/request id、elapsed 等易变封装），
因此等价比较用投影身份 + SQL 计数 + deepcopy 计数 + 字节数，不用原始摘要；该限制 R1 已登记，仍未关闭。
探针只覆盖一个身份/一个请求，shim 之外的控制器入口与传输不在内；不构成 SLO/容量/跨角色/发布结论。

**（6）验证。** `make ci.local.iteration` PASS（dirty，coverage=L1_only，receipt=none）；探针 6/7 号两次运行均
`exit=0` 且报告完整（`acceptance_pass=false` 为设计：探针不宣称验收）；`git diff --check` 干净。L3 结果与日志已入
run（`sce-r5-contract-request-probe-7.log`）。

**（7）下一步。** 偏好职责收口：effective GET/SET 对完整页面装配的依赖，以及 V2 与前端重复应用偏好的唯一责任归属，
保留禁止列/锁定列/切公司/撤权/保存竞争反例；其后才做 R6（独立复核、冻结、交付门禁、精确 HEAD Quick、受保护 PR）。
miss 路径双重复制与 gc 停止项继续独立登记。仍 dirty，未冻结/未提交/未推送/未部署，不提前 Quick、不扩浏览器矩阵、
不宣布整体收口。

### R6 前置：系统性能基线建立（2026-10-16，接力执行器）

证据只维护于同一 run 的 `backend_runtime_investigation.system_performance_baseline`，不新开台账。身份未变
（写树 `/home/lidefend/workspace/sce-backend-odoo-local-env`；主 checkout 只读）。本轮**未改动任何 P0–P3 产品文件**，
只增加 P4 采集/归一化载体，因此不触发产品契约快照与浏览器影响面重跑。

**（1）目标。** 把分散的性能记录收敛为「可复测、身份完整、缺口诚实」的正式基线载体，覆盖规则要求的三个互不替代
的验收层（受控回归 / 日常体验 / 上线容量），并明确哪些层当前**尚未**达标。

**（2）载体（新增，全部 P4）。**

| 文件 | 作用 |
| --- | --- |
| `scripts/verify/system_performance_baseline.py` | 唯一归一化引擎，schema `system-performance-baseline/v1` |
| `scripts/verify/test_system_performance_baseline.py` | 单元测试，经 `make verify.system.performance.baseline.unit` 执行（23 tests） |
| `scripts/verify/local_dev_performance_baseline.sh` | 受管采集包装，只复用登记的 `local.dev.*` 运行身份 |
| `scripts/ops/local_dev_performance_identity.py` | 只读身份采集器（docker / env-file），不写运行环境 |
| `make/dev.mk` | 新增 `local.dev.runtime.performance.baseline`、`verify.system.performance.baseline.unit` |
| `docs/ops/audit/system_performance_baseline.md` | 记录生成视图（生成物，非手改） |

**（3）归一化铁律（由单测固定，不由人保证）。** 缺计时记为缺口而非零值（`unknown_is_gap_never_zero`）；
嵌套阶段永不相加（`stage_sum_forbidden`）；样本观察数与保留数不相等即断言失败、不静默丢样本；
17 个必备身份字段可解则记 provenance、不可解为显式 gap，有 gap 即 `status=incomplete`；
三层互不替代，`daily_experience` 恒 `not_run`、`capacity` 恒 `target_unresolved`，直到各自身份被核定。
identity 按探针声明的产品 sha256 与当前 worktree 比对，只有 `match` 才进入受控回归层。

**（4）本轮实测（受管入口一次运行，EXIT 0）。**

- 记录：`artifacts/backend/system_performance_baseline.json`，`--strict` EXIT 0，
  `status=baseline`、`gaps=0`、样本 `11/11`（观察数 = 保留数）。
- SLA 三层 p95 / payload：`system.init` 617.39ms / 238317B，`ui.contract` 795.44ms / 621388B，
  `execute_button` 24.44ms / 683B；预算 8000/5000/3000ms 与 3.5MB/3.5MB/600KB，**均达标**。
  （`execute_button` 状态为 403 的权限路径探针，`sample_note` 已注明，属混合结果。）
- `observe` web_startup：进程首次 1807.65ms / 3006 SQL；随后 5 次 373.40–499.59ms / 各 629 SQL。
  首次样本已声明最大阶段 `build_nav` 1321ms、`finalize_startup_surface` 268ms。
- `contract_profile` action_open：首样本 3831.67ms / 1040 SQL（含进程首次代码翻译加载），热样本 256.70ms / 22 SQL。
- 前端产物：`frontend_index_sha256` 与 nginx 实际服务的 `served_index_sha256` 一致（`dist` 与线上不一致 = false）。
- 可见规模：project.project 15 / payment.request 67 / construction.contract 54；company 1。
- 环境身份：compose `sc-local-dev` / db `sc_dev_demo` / principal `user_demo_role_finance`（uid 45, company 1）/
  action 878 / `odoo17-odoo:latest` 容器 `ec95a747…` / 18 CPU，无 CPU、内存限额。

**（5）三层状态（本轮必答项，不许含糊）。**

| 层 | 状态 | 理由 |
| --- | --- | --- |
| 受控回归 | `passed` | 2 个带计时的 entry（observe / contract-profile）产品哈希 `identity_match=match` |
| 日常体验 | `not_run` | 需绑定部署、前端产物、真实网络路径与代表性角色/数据规模 |
| 上线容量 | `target_unresolved` | 目标并发、数据规模、吞吐与错误预算尚未核定 |

`platform-sla-guard/v1` 不声明产品哈希，故 `sla-guard.json` 的层身份恒为 `unknown`，属设计而非缺口；
这一点同时说明**「守卫 PASS」不等于基线完整**。

**（6）限制（登记，不掩盖）。** 单 principal / 单 action（878）/ 单页，不是全产品基线；仅进程内观测，
不含 HTTP、浏览器、认证、SLO 或容量；阶段为声明的嵌套阶段，数值不可相加；记录身份绑定采集时的 dirty worktree，
交付前必须重冻结；`permission` 与 `cache_identity` 两类探针**本轮未采集**，同一入口用
`PRODUCT_PERFORMANCE_BASELINE_SOURCES=` 追加即可，不另造入口。

**（7）验证。** `make ci.local.iteration` PASS（dirty，`coverage=L1_only`，`receipt=none`，`outside_scope=[]`）；
`make verify.system.performance.baseline.unit` 23 tests PASS（含正例达 `baseline`、反例记 gap 或 fail-closed）；
`make verify.agent.ledger.unit` 15 tests PASS。本轮同时补齐 run `scope`：新增 `docs/ops/audit/platform_sla_report.md`、
`docs/ops/audit/system_performance_baseline.md`、`scripts/ops/local_dev_performance_identity.py`（此前落 `outside_scope`）。

按影响面选定的 L2 定向用例另加两项：`make verify.local.env.readiness.unit`（新增采集器直接依赖受管 `local.dev.*`
环境身份）15 tests PASS；`make verify.frontend.dev.incremental.unit`（要求 L2 的计划器本体）30 tests PASS。
计划器列出的 `verify.frontend.*` 目标来自相对基线 `41c7a9dd` 的**累计** dirty 差异，本轮未改任何前端或产品文件，
其输入未变，因此按影响面复用而非重跑；本轮不含产品面改动，不扩浏览器矩阵。

**（8）下一步与边界。** 受控回归基线载体已建立，但**整体性能未收口**：日常体验层 `not_run`、容量层
`target_unresolved`，不能据此宣布达标。R6 仍为：提交本轮台账与载体 → 重冻结完整 tracked+untracked 指纹（旧
`f758779d…` 绑定 `0af04237`，已被新增文件作废）→ 一次精确 HEAD `make ci.local.quick` → 独立复核与外部归档 →
`pr.push`。R3 缓存复制、R4 权限耗时、关系弹窗列派生等既有候选保持独立登记。仍 dirty，未提交、未推送、
未部署、未宣布主线集成或产品验收。

### R6：热路径缓存读取隔离克隆（P0，2026-10-16，接力执行器）

证据只维护于同一 run 的 `backend_runtime_investigation.warm_cache_clone_optimization`，不新开台账。身份未变
（写树 `/home/lidefend/workspace/sce-backend-odoo-local-env`，分支 `fix/main-scheduled-ci-closeout-20261016`）。

**（1）职责边界。** 正式产品层 P0 平台内核产品；层目标 `addons/smart_core/utils/load_contract_response_cache.py`
的 `LoadContractResponseCache.get()` 读取隔离克隆；模块 `smart_core`；平台机制，不含行业/客户语义。
在此层是因为契约响应缓存与它的读取隔离契约属于平台契约运行时；实测成本来自 `copy.deepcopy` 在缓存所存的
JSON 形状 payload 上的逐对象分派。不在别处：**不做模型特判、不改前端、不放宽权限、不扩大缓存或 TTL**；
对缓存所存 payload 必须与 `copy.deepcopy` 行为一致。

**（2）改动。** `get()` 由 `copy.deepcopy(response)` 改为 `isolated_clone(response)`。`isolated_clone` 直接以同一套
memo 记账克隆 `dict`/`list`（共享子对象在副本中保持共享，与 `deepcopy` 完全一致），原子标量
（`None`/`str`/`bool`/`int`/`float`）原样返回，其余类型（tuple/set/bytes/子类/自定义对象）**连同同一 memo 委托
`copy.deepcopy`**，因此元组、集合、自引用等语义不变。

**（3）隔离不可删。** 调用方 `handlers/ui_contract_v2.py` 会就地改写取回的图（R3 已在此处删掉第二次复制），
若返回共享引用就会把请求内写入泄漏进缓存。本轮只换等价克隆实现，**隔离契约本身不变**。

**（4）A/B 实测（受管 `local.dev.runtime.contract_request.probe`，uid45/company1，action 878 / menu 559 / `ui.contract.v2`，每组 n=12）。**
身份绑定：探针身份集合中唯一变化的文件就是 `utils/load_contract_response_cache.py`
（前 `d5ce5896…d13`，与 HEAD blob `0af04237` 逐字节相同 → 后 `1ed6ffad…c0a`），其余 5 个身份哈希前后一致。

| 指标 | before | after | 说明 |
| --- | --- | --- | --- |
| hot dispatch median / p95 | 88.759 / 201.688 ms | 69.945 / 180.963 ms | median −18.814 ms |
| hot gc-off dispatch median | 84.319 ms | 66.835 ms | 配对进程内对照，去掉一次性 GC 后同样 −17.484 ms |
| hot lookup median | 63 ms | 43 ms | −20 ms |
| `CONTRACT_PROJECTION_HOT_CACHE.get`（该样本） | 39.963 ms | 20.707 ms | 直接阶段归因 |
| hot `deepcopy_sites` | `{convert_to_record:25, load_contract_response_cache.py:get:1}` | `{convert_to_record:25}` | 缓存克隆点消失（26→25） |
| hot SQL / bytes / `cache_identity_ref` | 25 / 113916 / `11e770c4b2ae` | 25 / 113916 / `11e770c4b2ae` | 不变 |
| cold_rebuild dispatch | 207.125 ms | 203.978 ms | 无退化 |
| r3_removed_copy（contract / source_contract） | 1.833–2.081 / 17.242–18.371 ms | 1.792–2.347 / 16.153–18.850 ms | 运行噪声内 |

**（5）等价性与语义。** `make verify.business_config.formal_list.unit` 234 tests PASS（146+21+62+5）；新增
`TestIsolatedCloneStaysDeepcopyEquivalent` 6 例：与 `deepcopy` 等值且 JSON 序列化一致、共享别名保持一致、
嵌套写入不回流源图、set/tuple/bytes/OrderedDict/complex 委托 `deepcopy` 且类型一致（原子元组保持同一对象）、
自引用图、热读路径对 JSON payload **从不回退调用 `copy.deepcopy`**。运行面：响应字节、缓存身份、SQL 数、
权限耗时前后一致，唯一行为变化是少一次容器图深拷贝。

**（6）限制与残留（登记，不掩盖）。** 单 principal / 单 action / 单请求、进程内观测，非 HTTP/浏览器/认证/SLO/容量；
`acceptance_pass=false` 是有界观测设计而非门禁结论；记录绑定 dirty worktree，交付前须重冻结；A/B 为同环境配对比较，
不是总体基准。**残留**：miss 路径仍对同一图深拷贝两次（cold_rebuild `deepcopy_sites` 仍见
`load_contract_response_cache.py:<lambda>:1`），已登记、本轮不修、也未证明是关键成本。

**（7）验证。** `make ci.local.iteration` PASS（dirty，`coverage=L1_only`，`receipt=none`，`outside_scope=[]`）；
`make verify.agent.ledger.unit` 15 tests PASS（新嵌套键与 7 条新增 `validation_results`、7 条新增
`evidence_index` 哈希使 run 保持自洽）；`make local.dev.runtime.cache_identity.probe` verdict 全 true。

**（8）结论口径。** 本轮热路径取得约 18–19 ms/请求的**受控回归**收益，且等价性由单测固定；但这只是有界观测，
**整体性能未收口**（日常体验层 `not_run`、容量层 `target_unresolved`）。批次结论为「批次验收完成」，不代表
主线集成、部署或产品交付。R6 交付仍为：提交台账/载体/P0 改动 → 重冻结完整 tracked+untracked 指纹 → 一次精确
HEAD `make ci.local.quick` → 独立复核与外部归档 → `pr.push`。

## 成熟系统对标目标判定（2026-10-16，本轮；性能不收口）

**（1）目标与职责。** 所有者要求"判断一个性能目标，对标成熟系统"。本轮把该判定写成**可机器校验的声明**，
而不是叙述：历史 SLA 预算（`platform_sla.json` 的 8000/5000/3000 ms）只是本系统对自身历史的回归门，
**不是产品目标**；它明显宽于成熟企业系统对同类操作的要求。P4 拥有目标声明与评估，P0–P3 必须满足该目标；
本轮**不改任何产品代码、不放松任何阈值、不覆盖任何已测数据**。

**（2）声明载体。** 仍是唯一归一化器 `scripts/verify/system_performance_baseline.py` 内的
`BENCHMARK_SOURCES` / `BENCHMARK_LADDER` / `MATURE_SYSTEM_TARGETS`，schema
`mature-system-performance-targets/v1`，与受控回归记录同一次生成；单测经
`make verify.system.performance.baseline.unit`。采集包装新增可选 `contract_request` 源
（`PRODUCT_PERFORMANCE_BASELINE_SOURCES=sla,observe,contract_profile,contract_request`）。

**（3）外部参照（每条目标至少引用一条，声明含 publisher/title/url 与原文口径）。**
Google RAIL（0–100 ms 视为即时）、Core Web Vitals INP（p75 ≤200 ms good）、
Nielsen Norman Group（0.1 / 1.0 / 10 s 三界）、TTFB（≤800 ms good）、LCP（≤2.5 s good）、
Salesforce Experience Page Time（健康 <3 s）、SAP Fiori Timing（1–3 s，>3 s 打断心流）。
7 个阶梯层、8 个来源；目标值必须等于其阶梯层预算，未知来源 / 值不一致 / 容差低于目标即 fail-closed。

**（4）判定规则。** `met`（≤target）/ `within_tolerance`（≤tolerance）/ `failed`（>tolerance）/
`not_evaluated`（样本不足：永不记为通过、永不记零）。p95 用 nearest-rank 且带最小样本数下限；
`overall` 取已评估目标中的最差判定；`capacity` 恒为 `target_unresolved`。

**（5）现状对照**（受管采集；uid45 / company1 / action878，`sc-local-dev` / `sc_dev_demo`）：

| 目标 | 阶梯层 | 聚合 | 样本 | 观测 ms | 目标 / 容差 ms | 现行历史门 ms（门宽比） | 判定 |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `warm_contract_dispatch` | instant_interaction | p95 | 24 | 180.77 | 100 / 200 | 5000（50x） | `within_tolerance` |
| `cold_contract_assembly` | keeps_flow | max | 1 | 197.20 | 1000 / 3000 | 5000（5x） | `met` |
| `profile_first_contract_assembly` | keeps_flow | first | 2 | 3774.39 | 1000 / 3000 | 5000（5x） | `failed` |
| `startup_system_init_first` | good_ttfb | first | 1 | 1800.64 | 800 / 3000 | 8000（10x） | `within_tolerance` |
| `startup_system_init_http` | good_ttfb | p95 | 1 | 604.13 | 800 / 3000 | 8000（10x） | `met` |
| `warm_startup_repeat` | keeps_flow | p95 | 5 | 513.16 | 1000 / 3000 | 8000（8x） | `met` |

**（6）判定结论。** 现行 SLA 门比成熟系统对标目标宽 **5–50 倍**。唯一硬越界项是
**进程首次 ui.contract 装配**（3774.39 ms > 3000 ms 容差），而现行 5000 ms 门会直接放行它；
这正是"历史门宽掩盖真实体验问题"的实例。热请求 dispatch p95（180.77 ms）虽在容差内，仍高于
"即时"目标（100 ms）。`cold_contract_assembly`（197.20 ms）说明**暖注册表下的重建已达标**，
与首次装配的差距指向进程级首次初始化，而非单次装配算法。

**（7）验证。** `make verify.system.performance.baseline.unit` 38 tests PASS（原 23；新增
`MatureSystemTargetTests` 覆盖 met / within_tolerance / failed / not_evaluated、nearest-rank p95 非均值、
选择器不跨组借样本、SLA 聚合按 intent 绑定、历史门比值实测、最差判定 overall、非法声明 fail-closed）；
受管采集 `SYSTEM_PERFORMANCE_BASELINE status=baseline gaps=0 entries=4`，`overall=failed`；
`make verify.agent.ledger.unit` 15 tests PASS；`make ci.local.iteration` PASS（dirty，`outside_scope=[]`）。
副产物 `docs/ops/audit/platform_sla_report.md` 由采集器按本轮观测刷新（限额未变）。

**（8）结论口径。** 这是**产品目标判定**，不放松、不替代历史 SLA 预算，也不是容量/SLO/生产验收；
容量层保持 `target_unresolved`，日常体验层保持 `not_run`，**整体性能未收口**。本轮不冻结、不 Quick、
不 `pr.push`、不合并、不部署。开放项保持独立登记：进程首次契约装配、热 dispatch p95、R3 miss 路径双重复制、
R4 首次权限耗时、偏好职责收口与偏好身份拒绝。

### 进程首次归因追加：一次性初始化 vs 首次缓存构建（2026-10-16，接力执行器；性能仍不收口）

**（1）目标。** 对唯一硬越界项 `profile_first_contract_assembly` 做时间窗归因：区分
**进程级一次性初始化**与**首次缓存构建 + 首次装配**，不做模型特判，也不把收益归给按需物化。

**（2）载体改动（P4，`scripts/verify/system_performance_baseline.py`）。** `_canonical_sample`
新增 `profile_top`（`cumulative_top` 前 40 行）；新增 `FIRST_CALL_ONE_TIME_MARKERS`
（当前仅 `odoo_code_translation_load`，匹配 `translate.py` / `polib.py`）与
`one_time_process_init()`：只取标记帧 cumulative 的**最大值**（嵌套帧永不相加），无可确证标记时记
`not_declared` 而非零。`MATURE_SYSTEM_TARGETS` 中 3 条加 `first_call_boundary: True`
（`profile_first_contract_assembly` / `cold_contract_assembly` / `startup_system_init_first`），
评估时附带 `one_time_process_init`（status / one_time_ms / frame / calls / share_of_observed / basis）。

**（3）本轮受管采集**（`sla,observe,contract_profile,contract_request`；`status=baseline gaps=0 entries=4`；
uid45 / company1 / action878；`sc-local-dev` / `sc_dev_demo`）：

| 目标 | 聚合 | 样本 | 观测 ms | 目标 / 容差 ms | 判定 |
| --- | --- | ---: | ---: | ---: | --- |
| `warm_contract_dispatch` | p95 | 24 | 178.80 | 100 / 200 | `within_tolerance` |
| `cold_contract_assembly` | max | 1 | 203.15 | 1000 / 3000 | `met` |
| `profile_first_contract_assembly` | first | 2 | 3593.40 | 1000 / 3000 | `failed` |
| `startup_system_init_first` | first | 1 | 1775.73 | 800 / 3000 | `within_tolerance` |
| `startup_system_init_http` | p95 | 1 | 617.86 | 800 / 3000 | `met` |
| `warm_startup_repeat` | p95 | 5 | 486.51 | 1000 / 3000 | `met` |

`overall=failed`；上一节的 3774.39 ms 是上一轮采集，本轮重采为 3593.40 ms，差异来自采集时刻，
历史结果不回改；手工载体 `docs/ops/runtime_performance_baseline_v1.md` 使用本轮最新值。

**（4）归因结果（`one_time_process_init` 仅对含剖析的样本可测）。**
`profile_first_contract_assembly` 的唯一确证一次性进程初始化是 `translate.py:545 __call__`
**560.26 ms（占观测 15.6%）**，826 次调用，来源为 `_get_code_translations` 524.83 ms →
`polib.parse` 472.89 ms，即 Odoo 代码翻译（PO 文件解析）的进程级一次性加载。
`cold_contract_assembly` 与 `startup_system_init_first` 的匹配样本不含剖析，记 `not_declared`。

**（5）`res.currency` 约 540 ms 确定归因。** 该帧为 `res_currency.py:332 _get_view` 523.68 ms，
是上述 `_get_code_translations` / `polib.parse` 的**外层**：它是首个"需要翻译"的视图读取，
触发了一次性翻译文件解析。因此这 ~540 ms **不是 currency 模型成本，不是每请求成本**，
不得按模型特判修复，也不得归给按需物化。

**（6）其余首次成本的归属。** `ui_contract_v2.handle` 3572.50 ms 中，除上述 560.26 ms 外，
主项是**首次原生视图读取 + 首次契约编译 / 关系弹窗装配**（首次填充视图与投影缓存）：
`_inject_relation_entry_contract` 1600.46 ms、`_build_relation_search_dialog_contract` 984.88 ms
（17 次）、`deepcopy` 710.85 ms（765542 次）、`ir_ui_view.get_view` 734.86 ms（22 次，内含
523.68 ms 翻译）。这些帧互相嵌套（`stage_sum_forbidden=true`），**不得相加**，也不得当作互斥预算。
同流程第二次请求 143.97 ms（SQL 1040 → 22）、同进程冷重建 197.20 ms，证明**缓存就绪后成本骤降**：
该硬越界既不等于"进程初始化"，也不等于"每请求成本"，不能据此删除或特判任何装配步骤。

**（7）验证。** `make verify.system.performance.baseline.unit` 45 tests PASS（原 38；新增
`FirstCallBoundaryTests` 7 例覆盖标记帧取最大不叠加、无标记记 `not_declared` 而非零、
`first_call_boundary` 目标附带注解、非边界目标不带注解、`profile_top` 截断与缺省，
以及生成报告渲染 First-call boundary 小节）；生成视图 `docs/ops/audit/system_performance_baseline.md`
含该小节（`profile_first_contract_assembly` measured 560.26 ms / `translate.py:545 __call__` / 826 / 0.1559）；
受管采集 `gaps=0 entries=4`；日志 `artifacts/main-scheduled-ci-closeout-20261016/sce-perf-firstcall-unit.log`。

**（8）结论口径。** 本轮只做归因，不冻结、不 Quick、不 `pr.push`、不合并、不部署，整体性能未收口。
开放项保持独立登记：进程首次视图读取/契约编译预热（本轮已归因，未优化）、热 dispatch p95、R3
miss 路径双重复制、R4 首次权限耗时、偏好职责收口与偏好身份拒绝。

### 角色维度契约变化纳入性能分析（2026-10-16，接力执行器；性能仍不收口）

**（1）目标。** 所有者要求：**不同角色的契约动态变化必须纳入性能分析**。此前所有基线
观测都是单 principal（uid45），看不到契约身份、契约面、导航能力与耗时是否随角色变化。
本轮新增一个只读的角色维度探针，把角色维度接入**同一个**唯一归一化器与同一条 record，
不做模型特判，也不据此改写任何历史测量。

**（2）载体改动（P4，无产品代码改动）。**

- 新增 `scripts/verify/local_dev_runtime_contract_role_matrix_probe.py`（只读、禁 commit）。
- `make/dev.mk` 新增 `local.dev.runtime.contract_role_matrix.probe`（`guard.prod.forbid` +
  `local.dev.ready` + `ODOO_SHELL_RUN_ISOLATED=1`）；该目标的 `py_compile` 清单纳入新探针。
- `scripts/verify/local_dev_performance_baseline.sh` 新增 `role_matrix` 源，输出
  `artifacts/backend/system-performance-baseline/role-matrix.log`。
- `scripts/verify/system_performance_baseline.py`：新增
  `CONTRACT_ROLE_MATRIX_PROBE_REPORT ` 前缀与 `runtime-contract-role-matrix-probe/v1` schema、
  `_role_matrix_samples()`（逐 role/case 展平并计入样本账目）、`_role_contract_variation()`
  （只读原始 payload 的 `findings` / `case_analysis`，**不重算不放松**），渲染新增
  `## Role-dimension contract variation` 小节。

**（3）探针口径。** 9 个已登记 demo principal，两个请求场景：`list_action_open`（action 878 +
该角色**自己**发布路由的 menu carrier）与 `form_action_open`（action 878 + 该角色**自己**可读的
`payment.request` record；无记录者记 `unavailable`，**不借用他角色记录**）。三阶段：
`assembly_first`（首触，首个角色付进程首次成本并如实记账）→ `hot_N` → `assembly_cold_role`
（**只清进程本地 `CONTRACT_PROJECTION_HOT_CACHE`**，原生视图/翻译保持热）。拒绝语义严格区分：
门禁拒绝记 `denied_by_permission`，handler 抛错/`ok=false` 记 `handler_error`。

**（4）本轮实测（`role-matrix.log`，EXIT=0）。**

| 场景 | dispatched | refused | unavailable | identity/surface 数 | cold ms (min/median/max) | hot ms 中位数 | SQL |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: |
| `list_action_open` | 6 | 3 | 0 | 6 / 6 | 201.43 / 342.02 / 347.42 | 66.5–72.3 | 23（finance 25） |
| `form_action_open` | 4 | 0 | 5 | 4 / 4 | 583.47 / 773.51 / 837.94 | 773.51 | 67 |

- `list_action_open`：`cap_e2e_smoke` / `role_owner` / `role_pm` 为 `handler_error`
  （`requests` / `payment.request` 的 search 视图不可解析 → **fail-closed**，不返回空弹窗）。
- `form_action_open`：`cap_e2e_smoke` / `cap_project_read` / `cap_project_user` / `role_owner` /
  `role_pm` 为 `unavailable`（本角色无可读 `payment.request` 记录，其中 3 个抛 `AccessError`）。

**（5）关键结论。**

- `contract_identity_varies_by_role=true`、`contract_surface_varies_by_role=true`、
  `surface_digest_stable_within_dispatched_role=true`（已派发角色热重复 `comparable_samples=6`、
  `diff_paths` 为空）→ **差异由角色驱动，不是噪声**。
- `navigation_capability_varies_by_role=true`：**仅 `role_finance` 有 action 878 的发布 menu
  carrier（menu 559）；其余 8 个 absent**。
- **关系面随角色变化（本轮关键）**：form 场景 4 个已派发角色都有 3 个 relation target 与
  3 个 search dialog，但 `with_navigation_authority` **只有 `role_finance`=3，其余=0**；同时
  `relation_field_map_varies_by_role[form]=true`（`payment_execution_ids` 的
  `can_read` / `can_create` / `reason_code=PAGE_ENTRY_READONLY` 有角色差异）。列表场景关系面一致
  （各 2 target / 2 dialog / 2 nav，与角色无关）。
- `all_refusals_are_explicit=true`、`refused_roles_never_report_a_contract=true`。

**（6）归一化与样本账目。** 复用唯一归一化器（不新增第二套口径）：
`role-matrix` entry `observed=96` / `retained=96`、`identity_match=match`；
record `status=baseline`、`entries=5`、`gaps=0`、`samples=142/142`、`no_sample_dropped=true`。
mature target `overall=failed`（met 3 / within_tolerance 2 / failed 1），唯一硬越界仍是
`profile_first_contract_assembly`；`capacity` 保持 `target_unresolved`。
（2026-10-17 取代：剖析样本已退出绝对目标评分，该硬越界改为 `not_evaluated`、
`overall=within_tolerance`，首个可比目标 `first_contract_assembly=1567.16ms` 仍未达标；
见下节「剖析可比性口径修正」）新增单测
`RoleContractVariationTests` 9 例（逐 role/case 样本全部保留并带标签、缺计时记 gap 而非零、
role 身份哈希绑定 `addons/smart_core`、无角色输入时不产出该段且**不臆造取值**、schema 不匹配返回
None、只读声明 findings、报告渲染该小节）。

**（7）证据索引漂移登记。** 本轮 record / report / capture 因**合法新增输入**而重新生成，
因此 3 个上一轮 `sce-perf-firstcall-*` 指针的字节身份与当前文件不再相等；另有 3 个
（`docs/contract/cases.yml` 与两个 `user_view_preference_*_intent_admin.json` 快照）为既有
待澄清漂移。处理方式：**不改写历史指针**，在
`backend_runtime_investigation.evidence_index_drift_registered` 逐条登记
`recorded_sha256` / `current_sha256` / 分类 / 原因，历史测量结果不回改。

**（8）验证。** `make verify.system.performance.baseline.unit` 54 tests PASS（原 45）；
`make verify.agent.ledger.unit` PASS（goals=106 runs=84 pinned_residuals=2
open_run_allowlist=2）；`ci.local.iteration` PASS（`change_state=dirty scope=unclassified_by_design
coverage=L1_only receipt=none`）。受管采集 `gaps=0 entries=5`。

**（9）结论口径。** 本轮把角色维度纳入分析：**后端需求声明 → 按声明物化 → 消费与行为反例 →
实测收益**中的"角色可变"部分已具备反例证据（导航权威、关系面、字段事实三者按角色分离）。
这不收口整体性能、不证明 R2/R3/R4 收益、不冻结、不 Quick、不 `pr.push`、不合并、不部署。
开放项保持独立登记：首次视图读取/契约编译预热、热 dispatch p95、R3 miss 路径双重复制、
R4 首次权限耗时、偏好职责收口与偏好身份拒绝、缓存身份内容摘要化。

### 剖析膨胀校准：剖析数字不是稳态基线（2026-10-16，同一轮）

**（1）事实。** 同环境同请求交替采样得到：干净**未剖析**首次 `1962.52 ms`（SQL 1040）对
**剖析**首次 `3814.6 ms`（SQL 1040）→ 首次装配被 cProfile 放大约 **1.94×**；同进程热配对
剖析 `271.35 / 147.22 / 148.74 ms` 对未剖析 `74.91 / 76.35 / 194.65 ms`（中位对中位
`148.74` vs `76.35`，约 **1.95×**）。两组 SQL 完全相同（首次 1040、热 22），说明膨胀是
剖析器自身开销，**不是额外查询、不是产品成本**。

**（2）口径。** 剖析样本只作分析工具：**任何 HTTP / 浏览器 / SLA 比较都不得使用剖析数字**，
也不得把剖析首次数值与 HTTP 数值直接比较。该结论已登记在
`backend_runtime_investigation.profiler_inflation_calibration`，供后续执行器复用。

**（3）验证。** 证据：`contract-profile-unprofiled-first.log`（未剖析首次 + 剖析热 + registry 冷）与
`contract-profile.log`（剖析首次 + 交替配对）。本轮不改写其任何样本。

## R5 偏好职责收口（2026-10-17，同一 run）

**（1）定位边界（不是初始化契约缺模型）。** 该缺陷是偏好接口接受非法身份，不是 `system.init`
不给模型。`system.init` 对每个导航叶都投影 `action_id` + `model`
（`addons/smart_core/handlers/system_init.py:1079-1105`、`delivery/menu_service.py:138-175`），
前端也据此 fail-closed 解析（`stores/session.ts:1687-1691`、`app/menu.ts:18-42`、
`resolvers/actionResolver.ts:27-70`）；`ui.contract.v2` 的 `op in {action, action_open, menu}`
本就合法地省略 `model`，由动作记录解析 `res_model`。因此**不调整启动链，也不要求所有意图都携带
`model`**。

**（2）后端强校验身份。** 由 `addons/smart_core/core/list_preference_policy.py:resolve_identity`
（P0）解析权威身份；`handlers/user_view_preference.py:_identity` 在其上拒绝非法身份：

| 情形 | 观测码 |
| --- | --- |
| 缺合法 `action_id` 或 `model`、传入未知 action、`ir.actions.act_url` 非列表表面 | 400 |
| 有目标但调用者无 `read` 权限（`project`/`_readable_fields` 用调用者 env 校验） | 403 |
| 表面无可解析的已声明策略 | 422 |

SET 在**任何写之前**先解析策略，失败即 `self._err`，不落库；有 action 时后端解析权威 model，同时
传 model 且不一致即拒绝，不形成错配身份。`models/user_view_preference.py:build_scope_key` 现在在
`action_id<=0 且 model 为空`时**抛 ValueError**，彻底停止持久化旧 `model:unknown` 哨兵。

**（3）用例与历史哨兵记录。**
- `docs/contract/cases.yml:1278-1293` 的两个空参数契约用例（`user_view_preference_get_intent_admin` /
  `..._set_intent_admin`）已改为**拒绝反例**（`allow_error_response: true`，快照 pin 到 400
  `缺少合法 action_id 或 model`）；成功用例改用**受管、可解析目标** `model: res.partner`。
- **只读确认环境、记录与来源**（未删除、未按 ID 删除）：
  - `sc-local-dev / sc_dev_demo`：仅 1 行 `sc.user.view.preference`，`id=1`，
    scope `ui:list_columns:list:model:res.partner`，属 `admin`(uid 2)，来自 resolved set 用例导出；
    `model:unknown` scope 计数 **0**。
  - `sc-contract-snapshot-v1 / sc_contract_snapshot`（登记的快照库，自 `sc_dev_demo` 播种）：
    3 行，全部属 `sc_test_admin`(uid 51) 且为真实 `action:` scope；`model:unknown` scope **0 行**；
    **`id=1` 现指向 `ui:list_columns:list:action:809`（payment.request）**，而快照自身声明的
    `res.partner` scope **解析为 0 行**。
- 结论：快照里的 `id` 是**环境分配的句柄**，今天连快照自己的目标都不再指向；按固定 ID 删除会误删
  另一个 demo principal 的偏好。处理规则固定为**按 `(user_id, scope_key)` 经受管入口精确解析，
  永不按固定 ID 删除**。本轮**未写、未删任何行**。
- 另登记（开放项）：SET 响应 `data.id` 未出现在前端已声明契约
  `frontend/packages/schema/src/index.ts:466 UserViewPreferenceContract`（仅 `scope_key` + `preference`）
  中，属**未声明、无人消费的环境句柄**；应移除或声明，并配合**按用例声明的响应易变字段归一**。
  该改动只能在**绑定本写树 source mount 的快照重导轮**执行：当前运行的快照容器挂载的是主 checkout
  （另一 commit），此时重导会产生新的漂移指针。

**（4）偏好与页面装配解耦。** effective/stored 均从**共享事实 + 有效策略**读取约束，不再调用完整页面
装配器：stored 分支只返回存储事实（`projection=stored`、`policy_source=current_page_contract`），
不编译页面、不解析 list profile；effective 分支走 `ListPreferencePolicy.project`（已声明策略投影），
**缺策略即 422 明确失败，绝不返回空策略兜底**。

**（5）偏好只应用一次。** 静态守卫证明契约/装配层（`ui_contract_v2*.py`、`ui_contract.py`）**不含任何
偏好 token**；`_apply_list_preference_policy` 仅在 `handlers/user_view_preference.py` 定义且无其他引用；
前端**唯一应用点**为 `views/ActionView.vue:3092 projectStoredListPreference` / `3130
readStoredListPreference`；另有 2 个**只登记为只读审计消费者**
（`handlers/business_config_surface.py`、`handlers/form_field_configuration.py`，仅计数）。
V2 仍声明 `preference_policy` 供前端消费；服务端**不再**把已存顺序写进契约列（`ui_contract_v2`
不再用存储偏好重排），保存合法性仍由后端负责，保存竞争与过期响应屏障保留。

**（6）验收（四项逐一取证）。**

| 验收项 | 结论 | 证据 |
| --- | --- | --- |
| 非法身份不能读写 | pass | 两个空参数用例 pin 400；ORM 反例证明拒绝时**不落库**、`model:unknown`/`unknown`/`ghost.model` 不可写、model/action 不一致拒绝；快照库 `model:unknown` 行数 0 |
| 合法目标行为正确 | pass | resolved 用例用 `model: res.partner`；有 action 时解析权威 model；model-only scope 不带公司分量；`build_scope_key` 对不可解析身份抛错 |
| 偏好路径不再整页装配 | pass | ORM 测试 patch `PageAssembler.__init__` / `assemble_page_contract`，证明两条路径**都未实例化**；stored 分支不编译页面；effective 缺策略 422 |
| 重复应用已消除 | pass | 单应用守卫（契约层无偏好 token、唯一 helper、前端唯一站点）；ORM 证明服务端不把已存顺序写进契约列；P1 已声明的 formal list lock（`a5d0d053`）由偏好投影上报，不再有第二套宽松裁决 |

**（7）证据与验证。**
- `artifacts/main-scheduled-ci-closeout-20261016/sce-r5-preference-orm.log`：10 tests，0 failed
  （受管 `verify.local.dev.user_view_preference.runtime.orm`，库 `sc_dev_demo`）。
- `python3 addons/smart_core/tests/test_user_view_preference_boundaries.py`：34 tests PASS。
- `sce-r5-list-preference-single-application.log`：静态单应用锁 PASS。
- `sce-r5-preference-record-probe.log`（`sc_dev_demo`）与
  `sce-r5-contract-snapshot-preference-record-probe.log`（`sc_contract_snapshot`）：只读、拒绝 commit、
  carrier 回滚。
- `sce-r5-iteration.log`：`ci.local.iteration` PASS，`outside_scope=[]`（首次因两个新测试路径
  在 run scope 之外而失败，已把 `addons/smart_core/tests/__init__.py` 与
  `.../test_user_view_preference_runtime_orm.py` 登记进 `scope` 后复跑通过）。
- `sce-r5-ledger-unit.log`：`verify.agent.ledger.unit` 15 tests PASS（goals=106 runs=84）。

**（8）结论口径。** 本轮**通过 R5 四项验收**，**不以守卫 PASS 替代产品证据**；**不收口整体性能**、
不冻结、不 Quick、不 `pr.push`、不合并、不部署、**不进入 R6**。**R4 首次权限耗时的关闭证据在本节撰写时仍未正式
引用，故当时 R4 保持开放（此状态已于 2026-10-17 由下方 R4 关闭章节取代）**；R3 miss 路径双重复制、热路径 gen-2 GC 停顿 100–115 ms、缓存身份 `ctime` 仅作
变化检测信号、偏好 SET 响应 `id` 未声明与按用例响应归一，均继续登记为独立开放项。

### R4 关闭：首次权限 215ms 与 132.6ms 差额的实测分离（2026-10-17，接力执行器）

本节接续 `### R4 执行结果`，只关闭「215ms 控制器段 vs 清缓存冷重建 132.6ms 的差额未再重测」这一项；
结论只维护于同一 run 的 `backend_runtime_investigation.permission_gate_attribution.closure`，不新开台账。

**（1）此前遗留的问题。** 旧结论把差额记为「进程首次模块/ORM 冷」，并如实登记「探针已先付，未再重测」。
本轮把这一差额**实测**出来，且不按模型特判、不用 sudo、不扩缓存、不跳检查。

**（2）手法（P4 只读，最小扩展）。** 旧探针的 `first_touch_of_process`（2.373ms）其实已经不是进程首次：
setup 里推导菜单 carrier 时调用 `sc.product.policy.published_route_authority()`，而它是 `@tools.ormcache`
进程级缓存，已经把权威建好了。因此给探针加一个**受治理的 carrier 入参**
（`PRODUCT_PERFORMANCE_PERMISSION_CARRIER`，走既有 `PRODUCT_*` 转发白名单），让**真正的第一次门禁**在
任何其他 ORM 预热之前运行。`make/dev.mk` 的 `local.dev.runtime.permission.probe` 显式透传该变量。

**（3）四个量级（同一 principal / 同一请求形状，含 `menu_id=559`）。**

| 量级 | 门耗时 | ACL | SQL | 说明 |
| --- | --- | --- | --- | --- |
| 热请求（每请求成本） | 中位 **1.81–1.96ms** | 2 | 3 | 无 `menu_id` 时 0.242–0.262ms |
| 清 registry 缓存后重建 | **125.286ms** | 133 | 288 | 权威主体重建 |
| **进程首次门禁（真）** | **484.830ms** | 219 | 371 | 含进程级模型/字段首次装配 |
| 控制器实测首段（重启后首个契约请求） | **215.173ms** | — | — | 浏览器链证据，`warmups=0` |

**（4）拆解与归因。**

- 进程首次门禁 484.830ms = `runtime_route_authority.principal_group_signature` **263.464ms**（缓存键/角色集合指纹）
  + `runtime_route_authority._build_runtime_route_authority` **218.245ms**（权威主体）。
  主体内：`MenuService.build_nav` 107.078、`MenuService.build_route_authority` 86.167、
  `ProductPolicyService.get_policy` 13.694、`_load_platform_release_gate` 3.123、`user_group_xmlids` 5.237、
  `_normalize_delivery_nav_refs` 5.617ms。
- **进程首次溢价** = 484.830 − 125.286 = **359.544ms**，全部落在 `principal_group_signature`
  （占首次门禁 **54.3%**）：即 `registry.clear_cache()` **无法复现**的进程级模型/字段/组集合首次装配
  （同一个调用在清缓存后只要 1.03ms、热态 1.09ms）。
- 观测的 **215.173ms 落在实测包络 [125.286, 484.830] 内**，且与**进程首次的权威主体 218.245ms**相差仅
  −3.072ms（98.57%）：与「serving worker 在同一请求的 auth/context 阶段已先付掉一部分组集合 ORM 冷」一致。
- **无重复调用**：一次门禁内 `build_runtime_route_authority` 1 次、`_build_runtime_route_authority` 首次 1 次、
  热态 0 次、`principal_group_signature` 1 次 → `no_redundant_duplicate_authority_build_in_one_gate=true`。
  ACL 219（首次）对 2（热）、SQL 371 对 3。

**（5）结论。** 215ms 段是**一次性的进程首次初始化**（发布路由权威 + 进程首次模型/字段装配），**不是每请求成本**；
热态保持 1.8–2.0ms（带 `menu_id`）/ 0.24–0.26ms（不带）。**R4 无优化空间，不改产品代码**：
`security/intent_permission.py`（`54f2b8fa…`）与 `delivery/runtime_route_authority.py`（`ebe4e453…`）哈希与 HEAD 一致；
唯一改动是 P4 只读探针的可选入参与 `make/dev.mk` 透传。

**（6）仍开放、不夹进 R4。** 既有 P0 `ir.actions.act_window.groups_id` 在省略 `action_type` 时未被强制（已登记，需单独
授权与自身反例集）；company 切换未覆盖（demo finance 仅一个公司，`second_company_id=null`，如实记为未执行）；
控制器 ingress/session/transport 残差未归因；R3 缓存复制、gen-2 GC 停顿、`ctime` 仅作变化检测、偏好 SET 响应 `id`
未声明，继续独立登记。

**（7）验证（dirty、未冻结）。** 探针单测 `scripts/verify/test_local_dev_runtime_permission_probe.py` **9/9 PASS**
（新增用例 pin 进程首次 / 清缓存冷 的分离与 carrier 入参）；两次 L3 探针运行 EXIT=0；`make ci.local.iteration`
与 `verify.agent.ledger.unit` PASS。未冻结、未提交、未推送、未部署、未 Quick、未进入 R6。


**（8）闭证引用（2026-10-17，接力执行器；R4 至此关闭）。** 所有者调度纠正指出：本报告给了 R4 的测量，却没有正式
引用其关闭证据，故 R4 仍被列为开放。现按「若已完成，在 run 中引用结果」处理——测量早已完成，故**引用并关闭**，不重跑：
证据与复用影响分析登记于 `backend_runtime_investigation.permission_gate_attribution.closure.evidence_citation`。
影响分析对全部 9 项已声明输入（探针、探针单测、`make/dev.mk`、两个未修改产品文件、四份探针日志）逐字节复核当前工作树，
结果 `PASS unchanged_inputs=9 drift=0`，四份日志在 `evidence_index` 中全部可解析；**命令输入、受管环境身份与相关文件集均未变化**，
故该结果按影响分析复用，而非重测。结论：215.173ms 是发布路由权限的**进程首次**构建（首次权限主体 218.245ms = 98.57%；
溢价归属 `principal_group_signature` 263.464ms = 54.34%），热态每请求 1.66–1.96ms（带 `menu_id`）/ 0.22–0.30ms（不带），
每道门恰好 1 次权限构建，**无冗余调用、无需改产品代码**。R4 关闭后仍开放且未夹入：company 切换覆盖、独立登记的
P0 `ir.actions.act_window.groups_id` 缺口、控制器 ingress/session/transport 残差。

## 剖析可比性口径修正（R2 证据对账，2026-10-17）

**（1）问题。** 上一轮唯一"硬越界"`profile_first_contract_assembly` 取的是**剖析样本**
（`profiled:true`，`3814.60 ms`），而同一份 record 的 `contract-request` entry 里已有**未剖析**的
`process_first=1567.163 ms`。把 cProfile 放大的数值判给绝对毫秒目标属口径错误（同一份文档自己声明
"剖析约 1.94×，不得与 HTTP/浏览器数字比较"），因此**修规则而不是修阈值**：阈值、ladder、
`historical_budget` 一律未动。

**（2）改动（P4 只读工具层）。** 唯一归一化器 `scripts/verify/system_performance_baseline.py`：

- 剖析样本只上报不评分（`profiled_values_ms` / `profiled_basis_ms`）；目标可声明
  `measurement_basis=unprofiled|profiled` 与 `diagnostic_only`，剖析/诊断目标永不产出通过或失败；
- `diagnostic_only` 必须声明 `measurement_basis=profiled`，否则声明校验 fail-closed —— 防止用该标志
  把**本可判定的未剖析测量**藏起来；
- 新增可比目标 `first_contract_assembly`（`selector.sample_labels=[process_first]`，同 `keeps_flow`
  1000/3000），承接同一个"首个契约装配"问题；
- 完整性改为 `complete_over_comparable_targets` + `ungradeable_by_declaration`（按声明不可评分者
  绝不计入通过）；
- 修 `share_of_observed` 在 `observed_ms=None` 时除零的隐患（改按 `profiled_basis_ms` 计并标注
  `share_basis`）。

**（3）判定变化（同一批 payload，仅评分口径变）。**

| 目标 | 旧 | 新 |
| --- | --- | --- |
| `profile_first_contract_assembly` | `failed` 3814.60（剖析） | `not_evaluated`（剖析值仍上报） |
| `first_contract_assembly` | 不存在 | `within_tolerance` 1567.16 |
| overall | `failed` | `within_tolerance`（met 3 / within 3 / failed 0 / not_evaluated 1） |

未变：`entries=5`、`samples=142/142`、`gaps=0`、`stage_sum_forbidden=true`、
`capacity=target_unresolved`。**首个契约装配 1567.16ms 仍高于 1000ms 目标 → 仍未达标**，
只是不再由剖析数值充当证据。

**（4）生成方式（可复算，未重采）。** 本轮**没有**重新采集 payload（capture 步骤未执行、未发 HTTP）；
只用唯一归一化器对同一批 hash 绑定 payload 重放，使判定变化只能归因于规则。重放命令、输入
sha256、前后判定、`not_re_run` 声明见
`artifacts/backend/system-performance-baseline/comparability-rule-replay.json`（`494ff82b…`）。
重放两次除 `generated_at` 外逐字节一致。制品：`artifacts/backend/system_performance_baseline.json`
（`ec786168…` → `f894ccee…`）、报告 `docs/ops/audit/system_performance_baseline.md`
（`728500ff…` → `20f2ccfc…`）；`identity.probe_and_budget_digest` 随之绑定本轮归一化器与 R4 探针
（`56a5d73b…` → 新值）。

**（5）反例与验证。** `make verify.system.performance.baseline.unit` **61 tests PASS（原 54）**，
新增：剖析-only 匹配 → `not_evaluated` 且 `observed_ms is None`（不是 0/通过）、
未剖析 `process_first` → `within_tolerance` 且不被标志藏起、`diagnostic_only` + `unprofiled` 声明
必须被拒、完整性只按可比目标计（去掉一个可比样本即重新开放）。
`git diff --check` 通过；`ci.local.iteration` / `verify.agent.ledger.unit` 见下条。

**（6）边界与仍开放。** 无产品代码改动、无收益主张（规则修正不产生提速）、不改 ladder、不是容量或
发布结论；完整重采（全部 source）在任何交付冻结前仍需执行。继续独立登记：R3 miss 路径双重复制、
gen-2 GC 停顿、`ctime` 仅作变化检测信号、偏好 SET 响应 `id` 未声明、company 切换未覆盖、
P0 `act_window.groups_id` 缺口。未冻结、未 Quick、未推送、未合并、未部署、未回改历史结果。

## 代码身份内容绑定（2026-10-17，接力执行器）

本节接续 `### R2 收尾追加：持久 source 缓存身份闭环 + 证据对账`，只处理所有者对该段的裁定：
「`ctime` 仍只是文件变化检测信号；若直接充当代码身份，不能称为可靠的内容身份闭环，正式部署仍应绑定
不可变构建或内容摘要。」因此 R2 把 `ctime` 放进身份行的做法被限定复核，须在同一 run 内改为**内容绑定**。
历史结论保留不改，R2 段落已加日期化取代标注指向本节。

**（1）裁定与边界。** 本轮是**正确性修复，不产生时延收益**：不改产品行为、不按模型特判、不扩缓存、
不延 TTL、不跳检查，也不改变 `profile_first_contract_assembly` / `first_contract_assembly` 的任何目标判定。
正式部署的权威身份仍应由 `SC_SOURCE_REVISION` / `SC_SOURCE_FINGERPRINT` 绑定不可变构建，本函数是同一部署内
代码内容身份的进程内兜底。

**（2）实现（P0，最小同层，`addons/smart_core/utils/load_contract_response_cache.py`）。**
- 新增 `_code_content_digest()`：受管源码根（`SC_SOURCE_ADDONS_ROOT`，默认 `/mnt/source-addons`）下每个
  `.py`/`.xml` 按 `sorted(paths)` 取 `path + "\0" + 内容 + "\0"`（1 MiB 分块读取）做 sha256 聚合；跳过
  `__pycache__`/`tests`/`.git`；不可读文件以 `<unreadable>` 占位而非静默跳过。
- `contract_code_fingerprint()` 的身份**只取内容摘要**。`size`/`mtime_ns`/`ctime_ns` 一律不参与：它们是文件
  系统变化信号，`touch`/`utime`、目录重建或镜像层差异都会让其漂移而与代码无关，混入身份会产生**假失效**；
  只依赖 `mtime+size` 又会漏掉就地改写。两个方向都不是可靠内容身份。
- 摘要按进程缓存（`{"value", "content_recomputations"}`）：运行中的解释器不会重新加载已导入模块，进程内重复
  读源码无意义；跨进程/重启由新进程按内容重算。

**（3）正反例（自包含单测，`addons/smart_core/tests/test_load_contract_response_cache.py`，缓存模块 21 → 24 tests）。**
- 正向（旧身份必须被拒）：`test_same_size_same_mtime_content_change_changes_the_fingerprint`（保留 R2 反例）；
  `test_old_source_entry_is_refused_once_the_code_identity_moves`（旧 token 写入，内容改写后新 token 取不到）。
- 负向（不许假失效）：`test_metadata_only_drift_does_not_move_the_identity`——`utime` 后**必须重新读内容**
  （`content_recomputations` +1）但身份不变；`test_process_cached_digest_is_not_recomputed_per_call`——热路径
  不得每次重读全部源码。

**（4）运行时探针（P4，`scripts/verify/local_dev_runtime_cache_identity_probe.py`，三问）。** `make
local.dev.runtime.cache_identity.probe` EXIT=0：`same_size_content_change_reaches_the_token=true`、
`old_source_rejected_after_identity_change=true`、`metadata_only_change_keeps_the_identity=true`、
`metadata_only_change_does_not_force_a_rebuild=true`、`ctime_changed=true`（但已不参与身份）、
`legacy_row_tuple_unchanged=true`。修正了原探针把 `mtime_only` 基线错比初始 token 的问题（改为与内容变更后的
`tmp_token_2` 比对），并新增「在 `tmp_token_2` 下写入 source 行」以证明元数据漂移**不产生假失效、不需要重建**。

**（5）成本（进程内一次性，非每请求）。** 冷算聚合摘要 **21.5 ms**（1246 文件 / 13.12 MiB），热调用
`<0.001 ms`，`content_recomputations` 仅 1。该成本在每进程启动时一次性发生，**不进入每请求路径，不构成收益**。

**（6）验证（L1/L2，dirty、未冻结）。** `git diff --check` 干净；
`make verify.business_config.formal_list.unit` **PASS**（146 / 24 / 62 / 5 OK）；
`make ci.local.iteration` **PASS**（`outside_scope=[]`，coverage=L1_only，receipt=none）；
`make verify.agent.ledger.unit` PASS。**不冻结、不 Quick、不推送、不合并、不部署、不改历史证据、不声明整体收口。**

**（7）仍开放（未并入本轮）。** R3 miss 路径双重复制、热路径 gen-2 GC 停顿 100–115 ms、偏好 SET 响应 `id`
未声明与按用例响应归一、company 切换未覆盖、P0 `ir.actions.act_window.groups_id` 缺口；R4 首次权限归因的正式
关闭见「R4 关闭」章节并引用台账 `backend_runtime_investigation.permission_gate_attribution.closure`。完整重采
仍须在任何交付冻结前执行。

## R3 miss 路径重复复制测量（2026-10-17，接力执行器）

本节接续「代码身份内容绑定」章节，处理所有者裁定：「miss 路径的双重复制继续登记，未证明它是关键成本前，
不新增 API 扩大本轮」。上一轮只登记了「no latency win claimed」而无直接测量，本轮补上测量本身，并保持
R3 缓存复制、R4 权限耗时、R5 偏好收口各自独立，不夹带、不提前冻结。

**（1）裁定与边界。** 本轮是 **P4 只读诊断 + 一次归一化器重放**，不改产品代码、不加 API/协议、不删复制、
不扩缓存、不延 TTL、不跳权限。测量结论**不产生收益主张**，也不并入 R2 的「按需物化」收益。

**（2）被测量的冗余与改动（仅 `scripts/verify/local_dev_runtime_contract_request_probe.py`）。**
- 冗余点：`addons/smart_core/handlers/ui_contract_v2.py:712-723` 先自建带 `ui_data`/`ui_meta` 拷贝的
  `cached_payload`，再交给 `CONTRACT_PROJECTION_HOT_CACHE.put()`；`put()`
  （`addons/smart_core/utils/load_contract_response_cache.py:90`）在 `:95` 又 `deepcopy` 一次 → 第二次复制即登记项。
- 探针只加计数与计时包装（`put` / `put_generated`）；因 `put()` 内部调用 `put_generated()`，一次 `put` 计为
  1 `put` + 1 `put_generated`，miss 时另有一次 assembled `put_generated`。新增
  `REPORT.miss_path_redundant_copy_ms`，只取 `cache_reason=asset_not_found` 的真 miss 样本。

**（3）实测（`sce-r3-misscopy-contract-request-probe.log`，EXIT=0）。**
- 真 miss（`process_first`）：`dispatch_ms=1588.024`、`put_calls=1`、`put_ms=15.755`、
  `put_generated_calls=2`、`put_generated_ms=50.205`、`share_of_observed=0.009921`（≈0.99%）；
  独立隔离 deepcopy 中位 **18.423 ms**（17.734–19.632），与在请求内数值同量级，排除包装器假象。
- 第二个 miss（`variant`）：`dispatch_ms=794.278`、`put_ms=16.401`（≈2.07%）。
- 热路径：`hot put calls` n=12，min=median=p95=max=**0** → 热读**零次**支付该成本，它是
  「每 `(身份, source token)` miss 一次」的冷身份成本，不是每请求成本。
- 同日志的 `cold_rebuild` 实为 `runtime_source_asset_hit`（`process_first` 已写入 asset），不支付该成本；
  基线标签含义是「无 assembled 快照的冷重建」，不是身份 miss。

**（4）判定。** **非关键成本**：请求内约 15.8 ms、隔离核验约 18.4 ms、占该 miss 请求 <2.5%、热路径为 0。
因此**不删复制**：若要删除，须先由消费侧断言失配来证明价值（禁止生产者替消费者推断），空结构蒙混仍然禁止。
本轮不新增 API、不扩范围。附带登记（不计入本项）：热 `dispatch_ms` 中位 70.657 / p95 181.684 / max 193.538，
配对 GC 关闭组中位 66.249 / p95 68.630 / max 71.140，两个热离群（181.684/193.538）为 gen-2 GC 停顿
（`gc_ms` 114.658/124.569，相对中位多出 122.881，发生在 `hot_4`），GC 关闭组消除该一次性停顿。

**（5）记录重放的副作用与登记（重要，未声称完全可比）。** 探针是归一化器 `PROBE_SCRIPTS` 输入之一，其改动使
已记录 `probe_and_budget_digest` 失效，故用**同一批已记录 payload 的确定性重放**重算记录与报告（**未发任何
HTTP**、未重采、未改产品代码）：记录 `f894ccee…` → **`54bdccdc…`**，报告 `20f2ccfc…` → **`3a99073a…`**，
probe 摘要 `ec819fc2…` → `4d593339…`。重放同时暴露：`contract-request.log` 与 `role-matrix.log` 变为
`identity_stale`，`layers.controlled_regression` 计时条目 **4 → 2**。**根因不是探针**，而是
`addons/smart_core/utils/load_contract_response_cache.py`：这两份捕获声明的是 HEAD 版本
`1ed6ffad…`，当前工作树为 `22c531a7…`（R3 缓存身份内容摘要改动尚未提交），故二者早于该改动、与当前树不可比。
因此 `warm_contract_dispatch`/`cold_contract_assembly`/`first_contract_assembly` 三个目标与 96 样本的角色层
**均带身份保留意见**；记录仍报 `overall=within_tolerance`、`complete_over_comparable_targets=true`，但该完整性
不含「源条目 stale」这一情形——本轮**不改归一化器判定语义**，只在此登记。新采的**带插桩**探针日志
**未**喂入记录（测量基准会被污染，正是可比性规则所禁止）。完整重采在任何交付冻结前仍需执行。

**（6）验证（L1，dirty、未冻结）。** `git diff --check` 干净；`make verify.system.performance.baseline.unit`
**61 tests PASS**（归一化器本轮未改，且该套件不读记录文件）；`make ci.local.iteration` **PASS**
（`outside_scope=[]`）；`make verify.agent.ledger.unit` PASS。**不冻结、不 Quick、不推送、不合并、不部署、
不改历史证据。**

**（7）仍开放（未并入本轮）。** 首个原生视图读取/首次契约编译预热、热 `dispatch` p95 与 gen-2 GC 停顿、
R4 首次权限关闭证据的正式引用（见「R4 关闭」章节与台账 `permission_gate_attribution.closure`）、
偏好 effective GET/SET 剩余项与未声明 SET 响应 `id`、company 切换覆盖、P0 `ir.actions.act_window.groups_id`
缺口，以及交付冻结前的全源重采。R3 miss 复制继续登记（已测量，非关键成本，未删除）。R6 仍未进入。

## 偏好 SET 响应 `id` 收口（R5 剩余项，2026-10-17，接力执行器）

**（1）声明（后端唯一事实）。** SET 响应的唯一声明面是 `{scope_key, preference}`，与 GET 的两个投影一致。
`id` 是产生该快照的环境所分配的数据库行句柄：`frontend/packages/schema/src/index.ts:466
UserViewPreferenceContract` 只声明 `projection / policy_source / scope_key / preference`；前端
`api/preferences.ts` 仅做类型化调用，`app/runtime/listPreferenceProjection.ts` 只读
`projection / policy_source / preference`；候选页面 smoke 的 SET 影子响应只回 `{preference}`，说明缺 `id`
时前端行为不变。因此 `id` 属**未声明、未消费、环境分配**的句柄，不得成为身份契约。同时登记一处既有不一致：
HEAD 的生成目录 `docs/contract/exports/intent_catalog.json` 仍把 `id` 声明为 SET 的响应字段。

**（2）实现（范围最小，先保接口）。**
- P0 产品：`addons/smart_core/handlers/user_view_preference.py` 的 SET 分支移除 `data.id`；写入路径、
  身份校验、策略校验与返回的 `scope_key/preference` 全部不变。
- P4 工具：`scripts/contract/gate_contract.sh` 新增 **per-case `volatile_keys`** 声明（additive 于全局
  `IGNORE_KEYS`，只作用于该用例；非法声明 fail-closed，永不接受通配符），新增可选 **`CASE_FILTER`**
  （声明的用例限定：逐个导出、比较仅限所点名的用例、未声明名 fail-closed；默认为空＝行为逐字节不变），
  以及 `EXPORT_ALL_CMD` 注入点供确定性自测使用；`scripts/verify/intent_cases_integrity_guard.py` 把
  `volatile_keys` 纳入 `ALLOWED_CASE_KEYS` 并校验（非空列表、非空字符串、去重、禁 `*`/`**`）。
- 声明载体：`docs/contract/cases.yml` 中**仅** `user_view_preference_set_resolved_intent_admin` 声明
  `volatile_keys: ["id"]`（全量用例扫描确认再无别处声明，见反例）。
- 快照：用受控 lane 把该用例重导出进 tracked ref（`make ENV=dev CONTRACT_CASE_ONLY=… local.dev.contract_snapshot`），
  ref 不再携带 `id`。生成目录按受影响面重导出：`make contract.catalog.export`。
- 新增受控入口 `local.dev.gate_contract.bounded`（限定用例的受影响面 gate，复用注册的 local.dev profile 与
  sc_dev_demo，不写 tracked ref，也**不是**完整交付门 `gate.contract` 的替代）；新增单测
  `scripts/verify/test_contract_gate_case_normalisation.py`（13 tests）与目标
  `verify.contract.gate_case_normalisation.unit`。

**（3）反例（三类，全部实测）。**
- **门语义反例（真实 `gate_contract.sh` 执行，stub 导出，无需数据库）**：声明存在 → PASS；把声明从用例里去掉
  → 同一漂移 FAIL（证明它不是默认忽略）；带声明但另有未声明漂移（`scope_key` 改变）→ FAIL；同一用例内
  未声明的兄弟键（`preference` 内容）改变 → FAIL；通配 / 空 / 重复声明 → fail-closed。
- **环境级反例（真实采集载荷重放）**：ref = 变更前采集（含 `id`）、cur = 当前源输出（无 `id`）→
  有声明 PASS；从派生用例文件移除声明 → **只**在 `ui_contract_raw.id` 处 FAIL（单用例、单键）。
- **产品反例（ORM）**：SET 仍落库（按 `(user_id, scope_key)` 可解析、`value_json` 正确），但响应 `data`
  的键集合恰为 `{preference, scope_key}`；既有非法身份反例（空参 / `model:unknown` / 动作与模型不一致 /
  未知动作 / 非列表动作）保持并继续通过。
- **快照反例**：4 个偏好快照在**任意深度**都不再有名为 `id` 的键；tracked ref 的 `ui_contract_raw` 恰为
  `{scope_key, preference}`。

**（4）实测与验证（dirty、未冻结）。** 变更前后载荷对比：4 个用例中**仅** set_resolved 变化，且只少
`ui_contract_raw.id` 一行，其余 3 个逐字节不变（同时证明 local.dev lane 先前的复现是忠实的——变更前 4/4 与
tracked ref 逐字节一致）。`make ENV=dev verify.local.dev.user_view_preference.runtime.orm` → **11 tests
（原 10 + 新 1），0 failed / 0 error**。受影响面 gate（worktree 源、限定 4 用例）→ **4/4 PASS**，
set 用例报 `volatile=id`。L1：`verify.contract.gate_case_normalisation.unit` **13 tests PASS**、
`intent_cases_integrity_guard` PASS、生成目录的两个守卫 PASS。**重导出同时关闭了 HEAD 已存在的覆盖缺口**
（`intent_catalog_case_coverage_guard` 在 HEAD 用例+HEAD 目录上复现 FAIL：resolved 用例已进 cases.yml 但目录未重导出）。

**（5）登记与边界（未声称完全可比）。** 本轮**不是时延收益轮**：不声明任何 HTTP 时延收益，也不把本项收益
并入 R2/R3/R4。`contract.catalog.export` 是生成载体，其 diff 同时吸收工作树中前几轮未提交的测试与探针
（`test_refs`、部分 `request_schema_hint`），并非只含偏好改动。快照 tracked ref 的生产者由 snapshot profile
改为注册的 local.dev lane（本工作树源）；snapshot profile 仍挂主 checkout 的旧提交，其 env 文件注册在主
checkout，故本工作树的 `local.contract-snapshot.require_env` 不可用。任何交付冻结前的**全源重采**仍需执行。
本轮不改历史证据、不冻结、不 `ci.local.quick`、不推送、不合并、不部署；R6 仍未进入；R3/R4/R5 残余项继续登记。

**（6）台账范围卫生修复（同轮，2026-10-17 接力执行器）。** 本轮首次 `ci.local.iteration` 以 exit=2 结束：
`scripts/ops/agent_run_context.py` 把三个**本 PFL 真实变更面**判为 `outside_scope` —— `make/contract.mk`
（新增 bounded gate 目标）、`scripts/contract/gate_contract.sh`（per-case `volatile_keys` 与 `CASE_FILTER`）、
`docs/contract/exports/intent_catalog.json`（受影响面重导出的生成载体）。处理方式是把这三条**按文件粒度**补进
`run.scope`（不放大到目录、不忽略、不改产品内容），随后在台账定稿状态下复跑 `ci.local.iteration` 与
`verify.agent.ledger.unit`，使内嵌 checkpoint 面板与复用输入绑定最终台账。失败尝试的原始日志保留为
`sce-pref-set-id-iteration.outside-scope-attempt.log`（sha256 `b9a4f026782e89ae6f30ea8618e3796db4f2588c3d44c618126e0df6699642a4`），
登记为**已修复的台账卫生缺陷**，不作为通过门；`docs/contract/cases.yml`、偏好快照与 `scripts/verify/` 本就在
scope 内，故未受影响。
同轮登记簿（bookkeeping）更新一处：`evidence_index` 里 `docs/contract/cases.yml` 的漂移登记 current 身份由
`4aab4fdf…` 推进到 `9b8e471d…`，成因就是本轮那条 `volatile_keys: [id]` 声明；被登记的历史指针逐字节保留、不重写，
没有覆盖任何产物、没有重推任何历史测量。本轮重导出的偏好快照与 `intent_catalog.json` 在 `evidence_index` 中没有旧指针，
因此不需要漂移登记。

## 热路径每请求场景绑定归因与最小守卫（P0，2026-10-17，接力执行器；性能仍不收口）

**（1）声明（先把 ~15ms 每请求花费钉死，不按模型特判）。** 热 `ui.contract.v2` 请求此前在
`UiContractV2Handler._validate_scene_action_binding` 上稳定花 ~14–15 ms，先前假设是「请求内重复加载」。
探针 `scripts/verify/local_dev_runtime_contract_request_probe.py` 新增**场景注册表归因块**（每样本
`load_scene_configs_with_timings` 调用次数、注册表自身内部阶段拆分，以及 handler 包装
`load_scenes_from_db_or_fallback`）后，在固定请求（uid 45、company 1、`action_id 878`、`menu_id 559`、
无 `scene_key`）上**实测否证**重复假设：12/12 热样本 `load_calls == 1` 且 `outer_calls == 1`。
真正的形状是：那一次调用是**整表重建**而非查表——`sc.scene` 已发布场景查询（~3.1 ms）、逐用户 tile 过滤
`to_public_dict(env.user)`、磁盘 `.scene.yaml` 发现 + YAML 解析（~6.2 ms）、content module exec（~0.9 ms）；
中位 13.7–14.1 ms，含 handler 包装 15.1–15.2 ms。12 次热请求阶段合计：`load_from_db` 37 ms、
`load_scene_asset_entries` 75 ms、`load_scene_registry_content_entries` 28 ms、`direct_module_exec` 11 ms。
**消费证明**：唯一消费者 `ui_contract_v2_authority.validate_scene_action_binding` 只经 `_scene_target_action_id`
读 `scene['target']`（及其 entry_target action id），**从不读**用户过滤后的 tile——而 tile 正是整包中唯一用户相关的
部分；且它在**无场景键时自身前置条件即返回 None**：
`scene_key = str(params.get("scene_key") or params.get("sceneKey") or "").strip(); if not scene_key: return None`。
即无场景键的请求把整包加载后又整体丢弃。

**（2）实现（P0，最小、保接口、不跳校验）。** `addons/smart_core/handlers/ui_contract_v2.py` 的
`_validate_scene_action_binding` 现于请求未携带 `scene_key`/`sceneKey`（strip 后为空）时直接 `return None`，
否则原样下走；复用适配器自身的两个键，不新增键名。**未加缓存、未改 TTL、未跳任何身份/权限校验、未做模型特判。**
P4 探针同步新增场景归因块与六形状等价块（`SCENE_GUARD_EQUIVALENCE`）。

**（3）反例（判别性与等价性，全部实测）。**
- **单测反例（+3 tests）**：`test_scene_action_binding_skips_registry_load_without_scene_key`、
  `..._for_blank_scene_key`（含 `scene_key="   "` 与 `sceneKey=""`）证明无/空场景键不再触发注册表加载；
  `..._still_loads_and_rejects_for_scene_key` 保留既有 409 语义（含 camelCase 键）。
- **判别性对照（guard off）**：把 P0 守卫 stash 掉、只留本轮新测试 → 边界模块 149 tests 中**恰好 2 failed**
  （就是两个 skip 反例），`still_loads_and_rejects` 在两态皆过。证明新测试确实判别守卫，不是默认忽略。
- **运行时六形状等价（guarded、guarded-hot、pre-guard-hot 三态 × 6 形状，同一 hot 身份）**：
  `scene_less`、`variant_limit(limit=40)`、`blank_key("   ")`、`camel_blank_key(sceneKey="")`、
  `unknown_scene_key`、`registry_scene_no_action` —— 六者 outcome / cache status / cache reason 全部匹配，
  掩码机械发现的易变时长路径后**规范化载荷逐字节相等**，`unexplained_diff_paths_total=[]`。
- **SQL 边界反例**：四个判定为「无场景」的形状 SQL delta **恰好 −3**，两个带非空 `scene_key` 的形状 delta
  **恰好 0** —— 证明有场景键时守卫**不会**跳过加载。

**（4）实测收益（相邻同构建 A/B，hot n=12 固定请求；dirty、未冻结）。** `dispatch` 中位
**73.882 → 56.281 ms（−17.601 ms，−23.8%）**；`authority_and_cache_lookup` 中位 **46 → 29 ms**；
SQL 中位 **25 → 22**；`fields.py:convert_to_record` deepcopy 中位 **25 → 0**；配对 gc-disabled 对照中位
**69.045 → 50.770 ms**；`scene load_calls` **1 → 0**。`cache_reason` 恒为 `assembled_v2_hot_cache_hit`、
`permission` 基本持平、响应载荷不变 —— 收益来自移除的那次重建，不是策略或身份变化。

**（5）验证与未声称（收窄边界，不夸大）。** `make ENV=dev verify.business_config.formal_list.unit` →
**240 tests PASS**（149 + 24 + 62 + 5）、`make ENV=dev verify.backend.scene_surface_boundary.unit` →
**22 tests PASS**、guard-off 判别对照 → **149 tests / 2 failed（预期）**；`make ENV=dev ci.local.iteration`
→ exit=0、`status=resolved`、`outside_scope=[]`。证据日志：`sce-r6c-scene-guard-{baseline,final,probe,
formal-list,scene-boundary,discrimination,iteration}.log` 与 `sce-r6c-warmprobe-after.log`（哈希见 run 台账
`evidence_index`）。**未声称**：热 `p95`（~170–190 ms）仍是 gen-2 GC 暂停，登记为**未改善**；除无场景键外
的 409 绑定分支**未在运行时跑**（本库无带具体 `target.action_id` 的注册场景，`bound_scene=null`），该分支由
单测而非运行时探针固定；**R3 miss 路径双重复制**、**R4 首次权限检查**、**首次原生视图读取 / 首次契约编译
预热**（唯一硬违约 `profile_first_contract_assembly`）与**偏好 effective GET/SET 解耦及单次应用**仍开放且
本轮未改。本轮不冻结、不 `ci.local.quick`、不推送、不合并、不部署；R6 仍未进入。

## 系统性能基线刷新与角色维度纳入（P4，2026-10-17，接力执行器；性能仍不收口）

**（1）声明（唯一源集，先声明后采集）。** 治理入口
`make ENV=dev ENV_FILE=<主检出的 .env.dev> PRODUCT_PERFORMANCE_PREFERENCE_ACTION_ID=878
PRODUCT_PERFORMANCE_BASELINE_SOURCES="sla,observe,contract_profile,contract_request,permission,cache_identity,role_matrix"
local.dev.runtime.performance.baseline`。源集是**声明输入**，逐项理由：`sla`/`observe` 是
`visible_scale` 身份与 SLA 目标的来源；`contract_profile` 是首次/冷契约的一次性归因来源；
`contract_request` 是固定热请求（uid 45、company 1、`action_id 878`、`menu_id 559`、无 `scene_key`）的每请求来源；
`permission` 提供 R4 首次权限与每请求权限的归因结论；`cache_identity` 提供持久化 source token 的身份结论；
`role_matrix` 纳入**不同角色契约动态变化**（9 个声明 demo 角色）。归一化器
`scripts/verify/system_performance_baseline.py` 只读既有载荷，不跑探针、不写治理运行时；`local.dev.performance.baseline`
不启动环境、不建库/端口/卷/凭据、不改产品代码。

**（2）实现与实测（一次采集 + 一次归一化）。** `SYSTEM_PERFORMANCE_BASELINE={"status": "baseline", "gaps": 0,
"entries": 7}`；`samples 142 / 142`、`no_sample_dropped=true`、`stage_sum_forbidden`。条目身份：
`observe`/`contract-profile`/`permission`/`contract-request`/`role-matrix` 全部 `match`（各带 product-code hash 数目与
`mismatches=[]`）；`sla-guard.json` 与 `cache-identity.log` 为 `unknown` —— 二者声明中不含产品代码哈希，按
`unknown_is_gap_never_zero` 记为未知而**不是 0**，也不冒充通过。层状态：`controlled_regression=passed`、
`daily_experience=not_run`、`capacity=target_unresolved`。
产物：`artifacts/backend/system_performance_baseline.json`（ignored）、`docs/ops/audit/system_performance_baseline.md`
（tracked，重写）；证据日志 `artifacts/main-scheduled-ci-closeout-20261016/sce-r7-baseline-refresh.log`（sha256
`9fab4166d69fced00bbcf7df2cdf6703f9383d4ffac717e1050388881fe0523c`，exit=0）。

**（3）反例（覆盖退化，已判定并纠正）。** 本轮先按 `contract_profile,contract_request,permission,cache_identity`
四源采集，结果 `entries 4 / samples 37 / gaps 1`，唯一 gap 为 `visible_scale: not resolvable from the given inputs`，
并直接把 `controlled_regression` 打成 `blocked`。即：**去掉 `sla,observe` 会让基线在身份层退化为不完整**
（`visible_scale` 的来源是 `observe` 的可见记录计数），且会**丢掉已提交载体中的条目**（原载体为 5 条、
142 样本，`docs/audit/performance_baseline_governance.md` 已登记）。因此按完整源集重采，条目集变为
**已提交载体的超集**（7 ⊇ 5，样本数同为 142/142，新增 `permission` 与 `cache_identity` 两个身份结论条目）。
这条反例同时说明：基线报告的重写必须以「条目集不缩小」为前提，不能只看 `status`。
该反例**不再依赖一次性采集**，可由登记的重放机械复现（只重跑归一化器、不跑探针、不改 tracked 报告）：
`python3 scripts/verify/system_performance_baseline.py --identity-file <identity.json> --inputs <上述四源载荷>`
`--out/--report` 指向 `artifacts/`，产物 `artifacts/main-scheduled-ci-closeout-20261016/sce-r7-baseline-narrow-sources.log`
（sha256 `b9ad9dafc59141fd4fe4c18400fb2f146b8a91706f6686eed8307561a07ff3d2`）与同名 `.json`
（sha256 `e20c325d22967b3a502f7ec61e3e2ea1823e3aece235bbd75c8dfdcdd0e12664`）：重放得
`status=incomplete / entries 4 / samples 37 / gaps 1` 且 `controlled_regression=blocked`；重放前后 tracked 报告
sha256 恒为 `85baf13a639354d0cacc9ab937875456a24fce5b284b8c3a20ee0e563a61671c`，证明该反例未触碰交付报告。

**（4）角色维度反例（不同角色契约动态变化，纳入同一基线）。** 9 个声明角色；
`contract_surface_varies_by_role=true`、`surface_digest_stable_within_dispatched_role=true`、
`all_refusals_are_explicit=true`、`refused_roles_never_report_a_contract=true`。`list_action_open`
`dispatched 6 / refused 3 / unavailable 0`，`form_action_open` `dispatched 4 / refused 0 / unavailable 5`
（不可用角色保留 AccessError 原因，**不用空契约替代**）。如实记录一条**不支持推断**的观测：
`relation_surface_varies_by_role` 为 `form_action_open=true`、`list_action_open=false` —— list 的关系面在
6 个被派发角色间**没有**随角色变化，基线不为它编造差异。

**（5）实测收益与目标（同构建、dirty、n 明确；不声明未测得收益）。** 成熟系统目标：
`overall=within_tolerance`（met 3 / within tolerance 3 / failed 0 / not_evaluated 1）；
`warm_contract_dispatch` p95 **172.88 ms**（目标 100 / 容差 200，24 样本）`within_tolerance` ——
**仍高于 100 ms 目标，不称 met、不称改善**；`cold_contract_assembly` max 245.56 `met`；
`first_contract_assembly` max **1711.16** `within_tolerance`（仍高于 1000 ms）；
`startup_system_init_first` 2208.29 `within_tolerance`；`startup_system_init_http` p95 633.36 `met`、
`warm_startup_repeat` p95 628.09 `met`；`profile_first_contract_assembly` profiled 4018.56 `not_evaluated`（diagnostic-only）。
热契约请求（n=12）：`dispatch` 中位 **63.084**、p95 **172.876**、max 192.783；`sql_count` 恒 **22**；
`convert_to_record` deepcopy **12/12 = 0**；`permission` 中位 3.413；`lookup` 中位 33（p95 48、max 146）。
`hot_gc_ms` 中位 3.931 但 p95 **118.323**、max **131.902**，判定 `hot_outlier_is_a_python_gc_pause=true`、
界外样本在 `hot_4`、比中位多 **129.699 ms**；配对 gc-disabled 对照中位 54.442、p95 58.945、max 60.282
（`hot_gc_off_removes_the_one_off_pause=true`）。这与台账既有的
**176.984→315.920 ms 热契约界外样本归因（CPython 二代 GC 暂停）一致**：本轮在同一固定身份上以 n=12 重现，
并由 gc-disabled 对照消去；**热 p95 仍未改善，继续登记**。
权限（R4 闭合证据的同源结论）：`warm_gate_ms` 1.968（with menu）/ 0.408（without）、
`cold_with_menu_gate_ms` 155.454、`process_first_gate_ms` 3.193、`denied_action_gate.gate_ms` 0.429；
`per_request_gate_is_not_the_215ms_segment=true`、`published_route_authority_is_the_cold_owner=true`、
`no_redundant_duplicate_authority_build_in_one_gate=true`、`first_touch_is_one_time=true`。
缓存身份：`persisted_source_token_tracks_code_fingerprint=true`、`same_size_content_change_reaches_the_token=true`、
`old_source_rejected_after_identity_change=true`、`metadata_only_change_does_not_force_a_rebuild=true`、
`ttl_not_involved`（持久化 runtime source asset 无 expiry 列，拒绝靠 `asset_version`/status，**不依赖热缓存
30 秒到期**）。角色维度时延：`list_action_open` 热per-role 53.7–61.2 ms（cap_project_manager 56.9、
role_project_a_member 54.0、cap_project_user 53.7、role_executive 59.2、role_finance 60.8、cap_project_read 61.2）、
cold min/median/max 185.824/198.425/345.061；`form_action_open` 热 791.8–908.6、cold 713.86/1026.456/1027.776。

**（6）边界与未声称（必须与结果同时读）。** `controlled_regression=passed` 只是**既有托管探针载荷的归一化
视图**，不是浏览器、SLO、容量或生产验收；`daily_experience=not_run` 需要已绑定部署、真实服务前端产物与
真实网络路径，`capacity=target_unresolved`。`role_matrix` 探针自身 `acceptance_pass=false` 是其严格位
（9 个角色中 5 个无可读 `payment.request` 记录 → case 记 `unavailable`），其 findings 只证明**拒绝是显式的**，
**不据此宣布角色权限面通过**。本轮不改历史证据、不改历史哈希、不重写已登记指针；不冻结、不 `ci.local.quick`、
不推送、不合并、不部署；**R6 仍未进入**。继续开放并登记：热 p95 的 gen-2 GC 暂停（未改善）、首次原生视图
读取/首次契约编译预热（唯一硬违约 `profile_first_contract_assembly`）、R3 miss 路径双重复制（已测量、非关键）、
偏好 effective GET/SET 解耦的残余与单次应用责任面。

## R7 热路径身份与确定性收口（2026-10-17，接力执行器；性能仍不收口）

本节回答一个问题：**同一身份、同一请求，为什么 `sourceSha256` 会在不同进程/不同请求之间变化，而交付契约摘要
`contractSha256` 恒定？** 结论：源信封 meta 里混进了「本请求的测量值」。同时给出两条同族收口（seal 语义摘要 memo、
`layout_fields` 成员顺序）以及一条**诊断工具**侧登记修正。**不声明任何未测得的时延收益**。

### （1）声明（边界与职责，先于改动）

- **Formal Product Layer**：P0 平台内核产品（契约身份）。
- **Layer Target**：`addons/smart_core/core/contract_lifecycle.py`（身份归一化：什么属于身份）、
  `addons/smart_core/handlers/ui_contract_v2.py`（源信封 meta 的取用、缓存写入与 `source_meta` 组装）。
- **Module**：`smart_core`。
- **Standard vs User-Specific**：平台机制，不含行业/客户语义。
- **Why Here**：`sourceSha256` 由平台身份模块对「同一处理器自己缓存并持久化的源信封」计算；
  把每请求测量带进该载荷的载体正是源信封 meta，所以身份规则与载体都在 `smart_core` 内闭合。
- **Why Not Elsewhere**：不是模型特判、不是前端兜底、不是低代码声明、不改启动链、不要求所有意图携带 `model`；
  `elapsed_ms` 由投影自身产生，装配器只**读** `source_meta`，故身份与载体之外无需改动。
- **Blast Radius**：被哈希的源载荷 + 持久化/热缓存条目的 `ui_meta`。交付契约不含 `source_meta`，
  因此**交付契约不变**（下文的 `contractSha256` 恒定即为其证据）。

### （2）产品改动 A：seal 语义摘要 memo（每请求 3 次重算 → 1 次）

- **声明**：`sourceSha256`/`contractSha256` 是**装配缓存条目对同一存储图的纯函数**；请求级身份
  （requestId/traceId/etag/校验）必须每请求独立保留，只有「同一条目、同一图」的纯函数摘要可以 memo。
- **实现**：`core/contract_lifecycle.py` 增 `_reusable_digest()`（只接受 64 位小写 hex sha256，否则空串，回退重算），
  `build_lifecycle_evidence(..., reuse_digests=None)` / `seal_unified_page_contract(..., reuse_digests=None)` 透传；
  `handlers/ui_contract_v2_authority.py::seal_runtime_contract` 透传；`handlers/ui_contract_v2.py` 增
  `ASSEMBLED_SEMANTIC_DIGESTS_KEY`、`sealed_semantic_digests()`、`_reusable_assembled_digests()`，
  热命中传 memo、miss 路径把 seal 结果写回 `assembled_digest_slot`。**memo 只是提示，不是权威**：
  `verify_unified_page_contract_integrity` 每请求仍从**实际交付对象**重算校验。
- **反例（memo 必须与重算一致）**：探针在每次 seal 调用上，用**同一批载荷对象**重算两个摘要并与 memo 比对，
  六次进程运行全部 `reuse_source_matches_recomputation=[true]`、`reuse_contract_matches_recomputation=[true]`、
  `binding_errors=[]`；交付对象复核（临时恢复未包装原始函数）各组 `ok==checked`
  （`hot 12/12`、`hot_gc_off 12/12`、`variant 2/2`、`process_first 1/1`、`cold_rebuild 1/1`）。
- **实测收益**（同构建、同身份、`action_id 878`、company 1、uid 45，n=12；探针自身带插桩，数字只作同工具前后对比）：

  | 指标 | BEFORE（`sce-r7-seal-digest-invariance-probe.log`） | AFTER（`sce-r7-digest-memo-after2-probe.log`） |
  | --- | --- | --- |
  | 热 `dispatch` 中位 / p95 | 60.251 / 177.095 ms | **35.663 / 36.843 ms** |
  | 热（关 GC）`dispatch` 中位 / p95 | 54.482 / 56.113 ms | **32.151 / 32.628 ms** |
  | 每请求 `payload_sha256` 调用 / 耗时 | 3.0 次 / 12.413 ms | **1.0 次 / 1.145 ms** |
  | 每请求 `strip_request_transport_identity` 调用 / 耗时 | 3.0 次 / 32.596 ms | **1.0 次 / 1.396 ms** |
  | 热 SQL 数 | 22 | 22（未变） |

- **不得归因的部分**：BEFORE 热组 p95 偏高包含一次 gen-2 GC 尖峰；关 GC 组无尖峰，且 **p95 的改善不归给 GC**
  （尖峰在 AFTER 的热组仍偶发，见 R5/基线的既有登记）。

### （3）产品改动 B：`layout_fields` 成员顺序确定性

- **现象（反例）**：`app_config_engine/services/assemblers/page_assembler.py` 的
  `"layout_fields": list(seen_fields)`（`seen_fields` 为 `set`）使 `list(set(str))` 的顺序随进程字符串 hash seed 变化。
  修复前两进程 `layout_fields` **成员相同**（`count=68`，sorted 成员一致）而 `order_digest` 不同
  （`ed5e4da22e9faf86` vs `5984aa691c48c1c0`）。
- **消费者检查**：`ui_contract_v2.py` 的布局字段过滤、`ensure_business_policy_layout_fields_visible`、
  `contract_governance_surface_mapping.diff` 全部只用 `in`/`set` 成员比较，**不依赖顺序**。
- **实现**：改为 `"layout_fields": sorted(seen_fields)`（纯成员事实不携带 set 迭代顺序；顺序有语义的列表不得照此处理）。
- **反例（修复后）**：3 次运行 `order_digest` 恒为 `60b33572e04dfafd`、`member_set_digest` 恒为 `7bc168cecb8e3b52`、
  `count=68`。

### （4）产品改动 C：源信封 `elapsed_ms` 退出源身份（本轮收口项）

- **症状**：`contractSha256` 恒定 `b90852db1fce92b49585e338450a3f181fee881359f43bede7c0054572a5f367`，
  而 `sourceSha256` 逐进程变化（`ff70e121…` / `74081823…` / …），`response_bytes` 随之差 1–3 字节。
- **定位方法**：既有路径摘要 map 有界（深度 4、1400 节点、列表只取前 24 项），且未排序扫描只覆盖**纯标量列表**，
  两者都错过该值。本轮在探针中加**无截断的全量路径摘要索引**（每个子树自底向上折叠成 1 个诊断摘要，按路径记录，
  不导出值），跨进程对账。
- **反例（BEFORE）**：两进程同身份同请求，37223 个路径中**恰有 3 条不同**：
  `$`、`source_meta`、**`source_meta.elapsed_ms`**（BEFORE 证据：
  `sce-r7-source-volatility-before-A.log`、`…-before-B.log`）。
- **消费检查**：`elapsed_ms` 是**本请求投影耗时**，是请求属性而非源属性；装配器只读
  `source_meta` 的 `model/view_type/render_profile/context/domain/order/limit/action_id/res_model`，
  **没有任何消费者读 `source_meta.elapsed_ms`**；且交付契约不含 `source_meta`（`contractSha256` 在 `sourceSha256`
  变化期间保持恒定，这只有在交付契约未携带它时才可能）。
- **实现**：`core/contract_lifecycle.py` 登记 `SOURCE_META_PER_REQUEST_KEYS = ("trace_id","request_id","elapsed_ms")`
  与 `source_meta_for_identity(meta)`（返回新 dict、不改调用方对象、非 dict 返回 `{}`）；
  `handlers/ui_contract_v2.py` 在**热读、原生表单分支、入口契约分支**三处取用点走该过滤，
  缓存写入不再重复列举键。**这是身份层登记，不是模型特判**；被过滤的键只有「传输身份 + 每请求测量」，
  其它键（含 `intent/model/op/etag/schema_version` 等声明事实）全部保留。
- **反例（AFTER，跨 6 个进程）**：`sourceSha256` 恒为
  `42d7bb3fa002084ae280660175c7f5418eb86aca2ea4f5a23d0ff27368ff2d20`，
  `contractSha256` 恒为 `b90852db…`；全量路径索引 37222 节点**两两差异 0**；
  交付对象复核 `ok==checked`；memo 与重算一致。
- **负向对照（证明过滤窄，不是整块丢弃）**：单测 `SourceMetaIdentityTests` 断言
  「仅 `elapsed_ms` 变化 → 身份不变」且「`model`/`op` 变化 → 身份改变」，并断言调用方 meta 未被就地修改。
  入口：`make verify.backend.contract_lifecycle.authority`（20 tests，PASS）。
- **局限**：改动前**已持久化**的源资产在数据库里可能仍带 `elapsed_ms`；读取时过滤使身份稳定，
  但本轮**不重写**已存载荷（不按固定 ID 删除、不做数据修复）。

### （5）诊断工具侧登记修正：场景守卫等价比较

- **症状**：`scene_guard_equivalence` 比较的是**两个不同请求**的响应（含响应侧每请求测量），
  于是某个阶段耗时在前两次守卫采样里恰好相同、在 pre-guard 采样里不同时，会被报成
  `unexplained_diff_paths`。**这是既有抖动**，同一 run 的旧日志已各自出现：
  `sce-r7-layout-order-fix-run1.log → meta.projection_cache.stages_ms.v2_projection_and_seal`、
  `…-run3.log → meta.projection_cache.stages_ms.authority_and_cache_lookup`。
- **修正**：登记 `RESPONSE_MEASUREMENT_PATHS = ("meta.elapsed_ms", "meta.projection_cache.stages_ms")`，
  按**前缀**匹配排除（差异路径是叶子，登记在容器上）。
- **不放松强度**：原始 `guarded_hot_vs_pre_guard_diff_paths` **仍如实上报**；只有登记过的测量子树被排除。
  修正后 4 次运行原始差异非空（恰为 3 条测量路径）而 `unexplained_diff_paths_total=[]`，
  说明比较器**仍能发现差异**，只是不再把测量算成载荷差异。

### （6）边界与未声称

- 上述收益是**同工具同身份的前后对比**，探针每次请求都被插桩，**不是稳态基线**；基线数字仍以
  `docs/ops/audit/system_performance_baseline.md` 为准。
- 本节**不声明**整体性能达标：成熟系统对标仍 `failed`（唯一硬违约 `profile_first_contract_assembly`），
  热 p95 仍在容差内但高于即时目标；R3 miss 双重复制、首次原生视图读取/首次契约编译预热、
  偏好 effective GET/SET 解耦残余继续独立登记。
- 不冻结、不 `ci.local.quick`、不推送、不合并、不部署、不进入 R6；不回改历史证据与哈希。
- 证据：`artifacts/main-scheduled-ci-closeout-20261016/sce-r7-source-identity-evidence.json`（含逐进程摘要、
  逐对路径差异、归因与局限），原始日志 `sce-r7-source-meta-identity-run1..6.log`。

## R8 热读克隆共享 memo 收口（2026-10-17，接力执行器；性能仍不收口）

本节回答一个问题：**热请求的昂贵环节是装配还是复制？** 结论：是**复制**。装配落缓存时把
`ui_data` 与 `source_contract` 各用一份独立 memo 深拷贝，而 `source_contract` 只是
`dict(ui_data)` 的浅拷贝，两者装配期本共享子树，于是**同一子树被复制了两份**。改成**同一份 memo**
后收益成立。**不声明任何未测得的时延收益，也不把基线样本波动算作本改动的功劳。**

### （1）声明（边界与职责，先于改动）

- **Formal Product Layer**：P0 平台内核产品（契约运行时机制）。
- **Layer Target**：`addons/smart_core/handlers/ui_contract_v2.py` 装配命中缓存写入段落。
- **Module**：`smart_core`。
- **Standard vs User-Specific**：平台机制，不含行业/客户语义。
- **Why Here**：开销是 `copy.deepcopy` 对「同一缓存条目内本就共享的对象子图」重复遍历；
  两个 dict 的所有者是该处理器，因此修复点在此。
- **Why Not Elsewhere**：不是模型特判、不是前端兜底、不改缓存/TTL、不放宽权限、不改契约/协议；
  交付字节必须完全一致。
- **Blast Radius**：每一次 assembled-v2 热缓存写入；等价性由
  `addons/smart_core/tests/test_load_contract_response_cache.py`（双所有权分组）与契约请求探针的
  `scene_guard_equivalence` 共同固定。

### （2）改动与所有权分组

- **改动**：装配落地缓存时，`ui_data` 与 `source_contract` 用**同一 memo**（`source_snapshot_memo`）克隆；
  `contract_v2` 仍用**独立 memo**。
- **为什么 `contract` 必须独立**：seal 会向 `contract` 写入每请求 meta 身份，必须与源图隔离；把它并进源 memo
  会破坏 seal 隔离与其摘要。
- **双所有权分组**：
  - **源组**：`ui_data` 与 `_assembled_v2.source_contract` **共享**（构造上即同一对象图）；
  - **装配组**：`contract` 与源组**互斥**。
  - 读图与缓存条目仍**完全隔离**：值污染、跨请求污染、身份变化反例保留在单测中。
- **诚实边界**：`contract` 顶层浅拷贝仍与 `ui_data` 共享至多 218 个容器（1038+218=1256，对单图 1038）；
  合并它没有收益且会破坏 seal 隔离，**本轮不再做复制减法**。

### （3）拓扑与实测收益

- **拓扑探针**（`make … PRODUCT_PERFORMANCE_MODE=cache_clone_split`，`sce-r8-clone-split*.log`）：

  | 指标 | 改前 | 改后 |
  | --- | --- | --- |
  | `clone_full_ms` | 17.597 | **8.507（-51.7%）** |
  | 整图容器数 `graph_full.containers` | 17250 | **9311** |
  | `shared_ui_data_vs_source_contract.shared_containers` | 0 | **7939** |
  | `json_bytes_full` | 2049131 | 2049131（不变） |

- **受控 A/B**（`local.dev.runtime.contract_request.probe`，同进程配对，n=12，`sce-r8-crprobe-*.log`）：

  | 指标 | 改前 | 改后 |
  | --- | --- | --- |
  | 热 `dispatch` 中位 | 85.726 ms | **79.046 ms（-6.68）** |
  | 热（关 GC）`dispatch` 中位 | 85.265 ms | **75.504 ms（-9.76）** |
  | 热 `lookup` 中位 | 28 ms | **20 ms** |
  | 热 SQL 数 | 22 | 22（未变） |
  | 热 `permission` 中位 | 2.876 ms | 2.959 ms（噪声内） |

- 唯一变化的身份文件是 `handlers/ui_contract_v2.py`：`3d4341c0…` → `b7adfe86…`；其余五个身份哈希两轮一致。

### （4）语义等值（先于收益比较）

- 交付契约摘要 `contractSha256` 两侧恒为 `b90852db…`；源身份 `sourceSha256` 两侧恒为 `42d7bb3f…`
  （与 R7 恒定基准一致）；`source_full_digest_index` 两侧相同。
- `scene_guard_equivalence` 全 True（缓存原因/状态/结果/SQL 增量/归一化载荷），`unexplained_diff_paths_total=[]`。
- seal 交付对象复核 `ok==checked`；摘要不变、源绑定无错误。
- 单测：`make verify.local.dev.runtime.performance.unit` 19 tests OK。

### （5）基线刷新与**样本波动**警示

- 7 源基线重采集：`entries=7`、`gaps=0`，身份重绑 `ui_contract_v2.py=b7adfe86…`
  （`sce-r8-baseline-refresh.log`；承载 `artifacts/backend/system_performance_baseline.json`）。
- 成熟对标 `overall=within_tolerance`（met 4/within 2/failed 0/not_evaluated 1）：
  `warm_contract_dispatch` **met p95 99.711ms**（n=24，中位 76.838，唯一尖峰 190.483 是那个 GC 暂停），
  `cold_contract_assembly` met 253.63，`first_contract_assembly` within 1666.581，`startup_system_init_first`
  within 1830.31，`startup_system_init_http` met 704.83，`warm_startup_repeat` met 460.53，
  `profile_first_contract_assembly` not_evaluated（profiled 3644.37）。
- **必须写明**：`warm_contract_dispatch` p95 `172.876 → 99.711ms` 的差别**主要由样本波动驱动**——
  那次 gen-2 GC 暂停落在早先 24 样本窗口内、落在本次窗口外。**不得**把约 73ms 归因于克隆优化；
  本改动的可归因收益只有受控 A/B 的 6.68–9.76ms。

### （6）边界与未声称

- 本轮**未修**热 p95 的 gen-2 GC 暂停（candidate 热尖峰 195.173ms / `gc_ms=114.058`），**不声明 p95 已修好**。
- R3 miss 双重复制（`15.755ms`，≈0.99%）继续登记为**开放但不关键**；`test_put_isolates_caller_owned_input`
  仍需 `put()` 的 deepcopy（缓存返回引用必须与调用方新鲜图隔离）。
- 早先 `source_handoff_ownership_closure.ownership_proof.alias_matrix` 声称四组件两两互斥，现由本轮
  **双所有权分组 supersede**（`ui_data` 与 `source_contract` 有意共享）；**历史条目保留不改写**。
- 上文收益是**同工具同身份受控 A/B**（探针带插桩），**不是稳态基线**；基线数字仍以
  `docs/ops/audit/system_performance_baseline.md` 为准。
- 本节**不声明**整体性能达标；偏好 effective GET/SET 解耦残余、首次原生视图读取与首次契约编译预热继续独立登记。
- 不冻结、不 `ci.local.quick`、不推送、不合并、不部署、不进入 R6；不回改历史证据与哈希。
- 证据：`artifacts/main-scheduled-ci-closeout-20261016/sce-r8-clone-split.log`、
  `…-clone-split-after.log`、`…-crprobe-pre.log`、`…-crprobe-candidate.log`、`…-baseline-refresh.log`；
  台账条目 `backend_runtime_investigation.hot_read_clone_shared_memo_optimization`。

## R9 热路径分配与 gen-2 GC 归因（2026-10-17，接力执行器；无产品改动）

本节回答一个问题：**热 p95 的尖峰到底由什么驱动，能否靠减少复制消除？** 结论：**频率由分配量驱动，时长由长寿命堆
大小驱动**；并提出一个**需要先做只读证明**的下一步设计。本轮**不写产品代码**，所有结论来自同一份已落盘证据
（`sce-r8-crprobe-candidate.log`），不新增运行、不改历史。

### （1）GC 行为（每请求 CPython 计数器）

| 组 | 请求数 | gen-0 | gen-1 | gen-2 | 环状回收对象 | `gc_ms` 合计 |
| --- | --- | --- | --- | --- | --- | --- |
| hot | 12 | 295 | 28 | **1** | 3636 | 138.56（其中 114.058 是唯一 gen-2） |
| hot_gc_off | 12 | 0 | 0 | 0 | 0 | 0.0 |
| process_first | 1 | 321 | 29 | **2** | 48177 | 257.81 |
| cold_rebuild | 1 | 99 | 9 | 0 | 2519 | 12.19 |
| variant | 2 | 48 | 5 | **1** | 619 | 156.15 |

- 每个热请求约 **24–25 次 gen-0**、**2–3 次 gen-1**、约 303 个环状对象，平时 `gc_ms` 仅 2–3 ms；
  每隔几个请求 gen-1 计数触顶（默认阈值 10）→ 触发**一次完整 gen-2 扫描，114–154 ms**（`hot_7` 114.058）；
  `process_first` 期间触发 2 次（合计 257.81），这也是首次成本的一部分。
- **关 GC 可消除**（`hot_gc_off` 全 0，dispatch 中位几乎不动）→ 该尖峰是**回收停顿**，不是投影工作。

### （2）归因

- **频率由分配量驱动**：热请求的分配主要来自读隔离克隆（一次约 9311 个容器 → 约 24–25 次 gen-0）。
  分配越少，gen-0/gen-1 晋升越少，gen-2 触发越少。
- **时长由堆大小驱动**：gen-2 是**全堆**扫描，长寿命堆主要是进程内缓存条目（多个身份 × ~9311 容器），
  请求本身不创建它们；只有缩小或将其排除才能缩短停顿时长。

### （3）纠正一个错误假设（重要）

- **假设**：装配命中时 `get()` 克隆整个条目（`ui_data`+`ui_meta`+`_assembled_v2`），但分支只用 `_assembled_v2`，
  于是 `ui_data` 被克隆后丢弃，约占克隆的 47%。
- **为什么看起来成立**：探针 `hot_entry_graph_nodes`（`entry=17581`）用的是**不去重的朴素递归计数**
  （`_graph_nodes` 无 visited 集），把 `ui_data` 与 `source_contract` **共享的子树重复计了两次**。
- **纠正**：用同一探针**去重**拓扑（`sce-r8-clone-split-after.log`）算，条目**唯一**图是 **9311**
  （`union(ui_data, source_contract)=8305`，其中共享 7939，加 `contract=1000`）；装配命中消费的
  `_assembled_v2` 唯一图约 9301，所以**真正被克隆但未消费的唯一容器只有 `ui_data` 的非共享 8127−7939=188（约 2%）**。
- **结论**：**R8 的共享 memo 已经消除了装配命中的重复**；不存在“47% 未用分片”。剩余热克隆（~9311 容器的 8.507 ms）
  是**读隔离契约要求**的复制，**不得**用“未用分片”拆分去砍。

### （4）登记为下一步的设计（本轮不实现）

- **候选**：装配命中时把**只读**的 `ui_data` / `_assembled_v2.source_contract` **按引用返回**，只深拷贝
  seal 会改写的 `contract`（~1038 容器）。条目里 `contract` 本就与 `source_contract` **互斥**（独立 memo）。
- **为什么这是真杠杆**：热克隆 ~9311 容器是每请求分配主源；只克隆 `contract` 可把克隆 **~8.5 → ~1 ms**，
  并把 gen-0/gen-1 量**降约 5 倍**，从而**直接降低产生 p95 尖峰的 gen-2 频率**。
- **实现前必须先做的证明（缺一不可）**：
  1. 证明装配命中**所有**消费者对 `ui_data`/`source_contract` **只读**（seal 只往 `contract` 写每请求 meta；
     核查 `_project_v2_source_policies`、`apply_runtime_record_overlay`、`_enforce_business_list_config_projection`
     与源策略投影）；
  2. 保留 `contract` 的隔离（seal 会改写它）；
  3. 把 `test_load_contract_response_cache.py` 的值污染/跨请求污染/身份变化反例**扩展到共享引用分片**；
  4. 证明请求结束后**没有任何对共享图的原位写入**（例如热命中成批前后对条目做 JSON 摘要往返必须一致）。

### （5）边界与未声称

- 本节**不修** gen-2 尖峰，**不声明 p95 已改善**；`hot_7` 尖峰仍是 `gc_ms=114.058`。
- 不冻结、不 `ci.local.quick`、不推送、不合并、不部署、不进入 R6；不回改历史证据与哈希。
- 证据：`artifacts/main-scheduled-ci-closeout-20261016/sce-r8-crprobe-candidate.log`、
  `…/sce-r8-clone-split-after.log`；台账条目
  `backend_runtime_investigation.hot_p95_gc_pause_characterization`、
  `…hot_read_clone_unused_section`、`…hot_read_clone_share_immutable_sections_next`。

## R10 热读共享只读分片（2026-10-17，接力执行器；性能仍不收口）

本节把 R9 登记的「下一步设计」落地：**装配命中只 READ 缓存源分片，只克隆 seal 会改写的
`contract`**。R9 已用去重拓扑证明装配命中无「未用分片」；R10 因此不再做复制减法，而是**改所有权**——
对只读分片按引用借用，对 seal 会原位改写的那一份保留隔离克隆。**只声明受控 A/B 的实测收益，
不把 gen-0 降幅当延迟承诺，也不声称 p95 已关闭。**

### （1）声明（边界与职责，先于改动）

- **Formal Product Layer**：P0 平台内核产品（契约运行时缓存机制）。
- **Layer Target**：`addons/smart_core/utils/load_contract_response_cache.py`（新增
  `get_assembled` / `assembled_snapshot_gate_matches`）＋ `addons/smart_core/handlers/ui_contract_v2.py`
  （热读路由、`shared_source` fail-safe 守卫、分支闸门改由共享 helper 判定）。
- **Module**：`smart_core`。
- **Standard vs User-Specific**：平台机制；**无行业/客户语义，无模型特判**。
- **Why Here**：装配命中只 READ 源载荷、只对 `contract` 盖章，拥有该缓存条目的 accessor 正是唯一
  能「借出」源分片而非重复复制的层。
- **Why Not Elsewhere**：不是缓存/TTL 扩大、不是权限捷径、不改客户端协议与前端；**交付字节必须完全一致**。
- **Blast Radius**：每一次 assembled-v2 热命中；由
  `addons/smart_core/tests/test_load_contract_response_cache.py` 固定。

### （2）改动与所有权分层（借用 vs 独占）

- **accessor**：新增 `get_assembled(...)`。命中时 `source_type` 原引用、`ui_data` **原引用（只读借用）**、
  `ui_meta` 深拷贝、`_assembled_v2.contract` **深拷贝（seal 会原位改写）**、
  `_assembled_v2.source_contract` **原引用（借用）**、digests 浅拷贝。**未命中/过期/gate 不符/缺 entry 一律
  返回 `None`**，调用方回退到全量隔离的 `get()`。
- **单闸门**：`assembled_snapshot_gate_matches(response, *, cache_version, client_type, delivery_profile, limit_params)`
  成为**唯一**闸门判定（accessor、lookup 后守卫、装配分支三处共用），条件是 `_assembled_v2` 为 dict、
  四元组相等、`contract`/`source_contract` 为 dict。
- **handler**：仅 `not runtime_record_id and not is_create_request` 时走 `get_assembled`，成功置
  `shared_source = True`；否则 `get()` 全量隔离。lookup 后新增 **fail-safe 守卫**：若 `shared_source`
  且 `cached_source` 非空却不满足闸门，则换成 `get()` 全量隔离并 `shared_source = False`——
  **按引用借出的图绝不允许落到会写入它自身的装配路径**。装配分支内**仅 READ** `source_contract`，
  对 `contract` 做 seal 深拷贝后**立即 return**。
- **分层说明（修正过时注释）**：源分片「借用」、`contract`「独占」；原「独占所有权」注释不再准确。

### （3）只读证明与反例（先于收益）

- **控制流**：装配分支 seal 后立即 return；`_handle_contract` 中对 `source_contract`/`ui_data` 的写入
  （`source_contract.pop/update` 963/965/988、`source_contract['record']` 1078）**全部在该 return 之下**，
  且作用于装配路径新建的 `dict(ui_data)`。
- **seal 对源只读**：`seal_runtime_contract` 只读 `source_payload['model']`、`resolve_published_version_ref`、
  `strip_request_transport_identity`（copy-on-write，返回新 dict/list）；**唯一写入是 `contract['meta']`**。
- **静态守卫**：`TestSharedReadConsumerGuards` 以 AST 断言——分支内对借用名无下标赋值/变更调用/删除，
  分支以 return 结束，闸门唯一，分支重写等值矩阵成立，热读经 `get_assembled` 且内层守卫含
  `not runtime_record_id`/`not is_create_request`。
- **burst 稳定性（真实 seal 反例）**：8 次连续热读后条目的 JSON 摘要不变、条目 `contract` 未被盖章、
  `memo == 重算` 且摘要唯一。
- **借用是消费者自守**：单测固定「经借用分片写入确实会触达 entry」——accessor 不是保护层，
  安全由**静态守卫 + fail-safe 路由**保证。

### （4）语义等值（先于收益比较）

- 交付路径 **37222 条 pre/post 0 差异**（无需易变豁免）；`contractSha256` 恒
  `b90852db1fce92b49585e338450a3f181fee881359f43bede7c0054572a5f367`；`sourceSha256` 恒
  `42d7bb3fa002084ae280660175c7f5418eb86aca2ea4f5a23d0ff27368ff2d20`；**28/28** sealed 交付 integrity
  `ok`；每个 seal binding `memo == 重算`；`scene_guard_equivalence` 两侧全 True；`seal_bindings_mismatch=[]`。

### （5）实测收益（受控 A/B + clone 反事实）

- **相邻时间受控 A/B**（`local.dev.runtime.contract_request.probe`，**仅「共享读」一个变量**，请求前备份并
  `sha256sum -c` 校验，n=12；`sce-r10-crprobe-adjacent-*.log`、`sce-r10-ab-compare.json`）：

  | 指标 | 改前 | 改后 |
  | --- | --- | --- |
  | 热 `dispatch` 中位 | 79.804 ms | **71.456 ms（-8.348，-10.5%）** |
  | 热（关 GC）`dispatch` 中位 | 76.956 ms | **66.652 ms（-10.304）** |
  | 热 `dispatch` max | 190.672 ms | **88.630 ms** |
  | 热 gen-0 | 23–25 | **13–14** |
  | 热 gen-1 | 2–3 | **1–2** |
  | 热 gen-2（12 请求） | 1 | **0** |
  | 热 `gc_ms` 中位 | 2.545 | **1.020** |

- **未变控制量**：`process_first` 1620.4/1657.5 ms（gc 321/29/2）、`cold_rebuild` 257.9/251.7 ms（gc 99/9/0）、
  SQL 22、permission ~3 ms；bytes 仅探针 jitter。
- **clone 反事实**（`PRODUCT_PERFORMANCE_MODE=cache_clone_split`）：整条 entry **8.756 ms / 9311 容器**，
  其中源组（`ui_data`+`source_contract`，unique 8305 / shared 7939）**7.648 ms**，`contract` **0.815 ms / 1000**，
  `ui_meta` 0.003 ms；aliasing 全 false——**移除的克隆成本即源组那 7.6–8.7 ms**。

### （6）边界与未声称

- **不把 gen-0 降幅当延迟承诺**：gen-0 只降约 1.8x（**非** R9 预测的 ~5x）；残余每热请求 **13–14 次 gen-0 未归因**，
  继续登记。
- gen-2 暂停在两个 R10 窗口内**都未触发**——与分配量下降一致，但**单窗口缺席 ≠ 关闭** hot p95 项。
- 跨进程 R8→R10 热中位变化（-13.371 ms）仅作**一致佐证**，**不作声明**；本轮只声明相邻 A/B。
- `r3_removed_copy_ms`（15.8–18.6 ms）是 `copy.deepcopy` **基准诊断**，**不是**被移除的生产成本
  （生产用 `isolated_clone`，7.1–8.8 ms）。
- 探针 patch 的是模块属性 `copy.deepcopy`，而 `get_assembled` 用模块级 `_DEEPCOPY` 别名克隆 `contract`，
  故 `hot_deepcopy_count`（0→1）**只反映 `ui_meta` 拷贝**，不计入 contract 克隆——这是**诚实局限**。
- 首次原生视图读取 / 首次契约编译预热（唯一硬缺口）、偏好 effective GET/SET 单次应用残余、
  R3 miss 双重复制、R4 首次权限、`res.users` 等目标默认值/创建/动态可见消费者核查**均未触及**。
- 不冻结、不 `ci.local.quick`、不推送、不合并、不部署、不进入 R6；不回改历史证据与哈希。
- 证据：`artifacts/main-scheduled-ci-closeout-20261016/sce-r10-crprobe-adjacent-pre.log`、
  `…-adjacent-post.log`、`…-ab-compare.json`、`…-clone-split.log`、`…-crprobe-after.log`、
  `…-sha256.json`（原始文件备份 `r10-ab-backup/`）；
  台账条目 `backend_runtime_investigation.hot_read_clone_share_immutable_sections`
  （supersede 设计条目 `…hot_read_clone_share_immutable_sections_next`）。

## R11 热请求残余归因：插桩放大与基线身份重绑（2026-10-17，接力执行器；无产品改动）

本节回答 R10 留下的唯一未归因项：**每热请求残余 13–14 次 gen-0**。结论：**它是 `contract_request` 探针自身
插桩的产物，不是产品热读成本**；同时把已过期的系统性能基线身份重绑为当前探针与当前产品代码。**本轮不写产品
代码**，只新增一个只读探针与一个受管入口，并刷新基线载体。

### （1）问题与身份

- R10 记录：热读共享只读分片后 gen-0 由 23–25 降至 13–14，但**残余 13–14 次未归因**。
- 全部观测绑定同一受管身份与同一请求：`uid 45`（`demo_role_finance`）/ `company 1` / `action 878` /
  `menu 559` / `ui.contract.v2` / `op=action_open`；数据库 `sc_dev_demo`。

### （2）三个独立观测点（先对齐口径，再比数）

| 观测点 | 是否含 `_seal_binding` 载荷重算 | 热 `dispatch` 中位 | 热 gen-0 | 热 gen-1 | 热 `gc_ms` 中位 |
| --- | --- | ---: | --- | --- | ---: |
| `contract_request` 探针（原始） | 是 | **69.176 ms** | 13–14（中位 14） | 1–2 | 0.94 |
| `contract_request` 探针（含 `probe_overhead`） | 是 | **66.706 ms** | 13–14（中位 14） | 1–2 | 0.94 |
| 变体 A：同探针 + `_seal_binding` 打桩 | **否** | **14.299 ms** | 2–3（中位 3） | 0–1 | 0.153 |
| 独立分配归因探针（无 crprobe 包装） | 否 | **13.811 ms** | 2–3 | 0–1 | ~0.15 |

- 变体 A 是**同探针、同一受管入口、同一请求**，唯一变量是 `_seal_binding` 立即返回桩值
  （临时文件，**未写入仓库**）。gen-0 由 13–14 掉到 2–3，与独立探针一致 → **残余 gen-0 来自插桩**。
- `crprobe` 的 `_seal_binding` 在 `finally` 中对**已缓存的源载荷**重算 `strip_request_transport_identity`
  + `payload_sha256`（约 8263 容器）并构建 path-digest/shape 映射，这些都被计入 `dispatch_ms`，也产生
  gen-0/gen-1 分配。`hot_read_clone_unused_section` 已证明该载荷本身在生产路径上**只读且不重算**。

### （3）插桩成本的两次量化（并说明其内部分配不稳定）

同一探针新增 `probe_overhead`（**加法式**，未改既有键）：

| 运行 | 热 `dispatch` 中位 | 其中 `seal_binding_recompute` 中位 | 差值（净） | recompute 占比 |
| --- | ---: | ---: | ---: | ---: |
| `sce-r11-crprobe-overhead.log` | 67.382 ms | 23.016 ms | 45.116 ms | 0.342 |
| `sce-r11-crprobe-overhead2.log` | 66.706 ms | **52.485 ms** | **14.293 ms** | 0.787 |

- **总量稳定、拆分不稳定**：两次运行总 `dispatch` 几乎相同（67.4 / 66.7 ms），但显式 recompute 计时
  一次 23.0、一次 52.5 ms。结合**独立探针净读 13.811 ms** 可知：插桩总增量约 **52–53 ms**，
  只是**其中一部分落在 recompute 计时器之外**（插桩分配触发、却在下一次操作时结算的 GC 停顿）。
  因此**不得**把 `seal_binding_recompute_ms` 当作插桩成本的全量；`*_net_ms` 也不等于产品净成本。
- **产品侧净读口径**以**无插桩**的独立探针为准：**13.811 ms 中位 / gen-0 2–3 / gen-2 0/12 / permission 2.06–3.02 ms**。

### （4）独立探针的每请求独占分配拆分（净容器，gc-off，nesting-aware）

3 样本净容器总数 1921/1593/1591，中位 **1593**，未归因 0/−5；等价于每请求约 **2.28 次 gen-0**：

| 站点 | 中位净容器 |
| --- | ---: |
| `cache.get_assembled` | 852 |
| `handler:build_projection_source_token` | 481 |
| `authority:emit_delivery_observation` | 136 |
| `permission` | 91 |
| `authority:seal_runtime_contract` | 59 |
| `handler:build_projection_cache_key` | 5 |
| `handler._ui_contract_params` | 1 |
| `handler._trim_limit_params` / `_validate_form_record` / `_validate_scene_action_binding` | 0 |

- 交付 1001 容器 / **113914–113915 bytes**；`response_sha256` 有 **8 个不同值**（meta 含 `elapsed_ms`/
  `stage_ms`/`request_id`）——**不满足易变请求身份豁免**，故不据此声称字节级等价。
- 预热首样本 **1555.543 ms**，随后 12.893 / 13.873 ms → **进程首次一次性成本仍在**，本轮不触及。

### （5）R10 相邻 A/B 的有效性不受影响

- R10 的 A/B 在**同一探针版本**下取改前/改后，插桩成本为**共模量**，在差值中抵消；记录的
  **−8.348 ms 中位（−10.5%）保持有效**。
- 但 R10 记录的**绝对**值（79.804 → 71.456 ms）是**含插桩**口径；减去插桩后当前净读约 13.8 ms。
  **绝对热读数字今后一律引用无插桩口径**。
- 诚实局限：以当前净读对 R10 两侧做减法的近似（≈18.5 ms vs 13.8 ms）**不能完全对上**，差额未归因，
  故只声明"差值有效"，**不声明**绝对值的严格换算。

### （6）系统性能基线身份重绑（P4，受管入口）

- **触发**：R11 修改了 `scripts/verify/local_dev_runtime_contract_request_probe.py`（其摘要参与
  `probe_and_budget_digest`），且 **R10 于 08:52 改动的产品代码（`ui_contract_v2.py`、
  `load_contract_response_cache.py`）晚于 08:24 的旧采集**——旧载体在两个维度上都已过期。
- **动作**：用受管入口 `local.dev.runtime.performance.baseline` 以**声明的 7 源集合**（`sla, observe,
  contract_profile, contract_request, permission, cache_identity, role_matrix`）重采集。
- **结果**：`status=baseline`、`entries=7`、`samples 142/142`、`gaps=0`、`controlled_regression=passed`；
  探针摘要 `1d891b7ae7429b49bc2268d432a0dbd9d712f9da383af354e142ff2b365283a5`；
  **产品代码 18/18 配对全部匹配当前树（漂移 0）**。
- **跟踪报告同时被修正**：此前提交版 `docs/ops/audit/system_performance_baseline.md` 只有 3 个源/11 样本
  （与台账"绝不从更窄源集合生成"相冲突），现为完整 7 源/142 样本。
- **新采集的对照目标**（与旧记录并列，不构成收口声明）：

  | 目标 | 旧记录 | 本次采集 | 判定 |
  | --- | --- | ---: | --- |
  | `warm_contract_dispatch` p95 | 172.876（4 源采集，超 100 ms）／**R8 七源采集已是 99.711（met，已声明为样本波动）** | **78.219 ms**（24 样本 63.853–80.324） | met |
  | `first_contract_assembly` 首次未剖析 | 3774.39 ms（4 源采集） | **1742.085 ms** | within_tolerance |
  | `profile_first_contract_assembly` 剖析基准 | 4018.56 / 3018.56 ms | **3660.89 ms**（一次性翻译 556.95 ms，占 15.2%） | not_evaluated（诊断项） |
  | `cold_contract_assembly` max | — | 249.36 ms | met |
  | `startup_system_init_first` / `_http` | — | 1754.91 / 649.01 ms | within_tolerance / met |
  | `warm_startup_repeat` p95 | — | 464.26 ms | met |
  | 总体 | within_tolerance | **within_tolerance**（met 4 / within 2 / failed 0 / not_evaluated 1） | — |

- **不得据此宣布缺口关闭**：`warm_contract_dispatch` 本次 p95 落到 78.219 ms，与 R8 的 99.711 ms 同属
  **样本波动**——24 个样本分布很紧、本窗口无 gen-2 尖峰；旧 172.876 ms 由一次随机 GC 停顿抬高。三者的
  判定都为 met，**没有一次改动被证明消除了 p95 尖峰**，`hot_p95_gc_pause_characterization` **仍开放**，
  R8 已声明的"172.876→99.711 属样本波动、不归因于改动"结论同样适用于本次的 99.711→78.219。
  `first_contract_assembly` 本次 1.742 s 只是**该次进程首次的实测值**，未经多次首启复现，
  **不声称**首次硬缺口已闭合（旧 3774.39 ms 亦为另一采集的口径，两者不可直接相减）。

### （7）边界与未声称

- 不冻结、不 `ci.local.quick`、不推送、不合并、不部署、不进入 R6；不回改历史证据与哈希；不按模型特判。
- 只读探针未加入 `PROBE_SCRIPTS`，**不改变基线摘要口径**（最小影响）。
- 首次原生视图读取 / 首次契约编译预热、gen-2 p95 停顿、R3 miss 双重复制、R4 首次权限、
  偏好 effective GET/SET 单次应用残余、`res.users` 等目标默认值/创建/动态可见消费者核查**均未触及**。
- 证据：`artifacts/main-scheduled-ci-closeout-20261016/sce-r11-alloc-attribution.log`、
  `…sce-r11-crprobe-recheck.log`、`…sce-r11-crprobe-overhead.log`、`…sce-r11-crprobe-overhead2.log`、
  `…sce-r11-variantA-sealbinding-stub.log`（及其 `.py`）、`…sce-r11-baseline-refresh.log`、
  `…sce-r11-baseline-prerebind.sha256.json`、`…sce-r11-baseline-unit.log`、`…sce-r11-runtime-perf-unit.log`；
  台账条目 `backend_runtime_investigation.hot_request_allocation_attribution`、
  `…hot_request_probe_overhead_accounting`、`…system_performance_baseline_rebind`。

## R12 record 表单静态结构复用与四层缓存边界（2026-10-17，接力执行器；不冻结）

### （1）声明（先于改动）

- **Formal Product Layer**：P0 平台内核产品。
- **Layer Target**：`smart_core` 契约运行时（`handlers/ui_contract_v2.py`、`core/unified_page_contract_v2_assembler.py`、`core/unified_page_contract_v2_client.py`、`core/contract_lifecycle.py`）与 `smart_construction_core` 投影归一化 hook。
- **Standard vs User-Specific**：平台机制，不含行业或客户语义。
- **Why Here**：缓存分层与复制所有权属于契约运行时机制；记录事实与权限必须逐请求计算。
- **Why Not Elsewhere**：不得在前端用 key/TTL 推断权限，不得把 record 契约写入持久资产或进程缓存，不得在行业/客户模块特判。
- **Blast Radius**：`ui.contract.v2` 表单/列表装配与终端裁剪；以装配守卫、128 项 compact 测试、23 项 lifecycle 测试、无插桩运行探针与语义等值校验证明收敛。

### （2）四层职责（机制化）

| 层 | 允许保存 | 禁止保存 |
| --- | --- | --- |
| L0 动态计算（每请求） | 记录覆盖、权限/entitlement、业务动作、策略、modifier/status、最终 seal 与 trim | 不缓存 |
| L1 后端进程热缓存 | record-independent 源投影；**仅 record-free** 已装配契约 | 带 `record_id`/create/preview 的已装配契约 |
| L2 后端持久资产 | 仅源投影（`contract_kind=runtime_source`） | 已装配/record-bound 契约、权限裁决 |
| L3 前端缓存 | 仅无 `recordId`、无 `previewToken` 的 create 契约 | 编辑/只读记录契约、预览契约 |

权威说明：`docs/architecture/contract_runtime_cache_layers_v1.md`。

### （3）改动与所有权

1. `smart_core_normalize_projected_contract_data`：先在权威输入上判断 `model == sc.general.contract` 且存在 `tax_id`，仅在 normalizer 真正可改变数据时才 `deepcopy`；其余请求不再为 no-op 复制整图。
2. `trim_unified_page_contract_v2`：顶层已完成唯一一次 `deepcopy`，`_trim_container`/`_trim_widget` 改为在自有副本上原地裁剪，不再逐节点重复复制。
3. `strip_request_transport_identity`：改为 copy-on-write；无传输字段的子树按引用返回。`contract_semantic_payload` 在删除 `meta` 前显式复制顶层，保证调用方对象不被修改。
4. `seal_runtime_contract`：复用装配阶段已算出的 `sourceSha256`；只重算被后处理改变过的 `contractSha256`。
5. `_base_contract`：不再为占位 `meta` 计算全图 `payload_sha256`；占位值改用稳定页面身份，最终 identity 由 seal 生成。
6. `ASSEMBLED_CONTRACT_CACHE_VERSION` bump 为 `ui-contract-v2-2026-10-17-base-identity-no-source-hash`，守卫摘要重钉为 `5470929601b3756a291adaac9445df3df9ecd0db276cb1e5ef0bde487cc24e12`。
7. 装配守卫新增 fail-closed 检查：`get_assembled` 必须 record-free、`_base_contract` 禁止全图指纹、前端 create 缓存键必须绑定 `sessionDb`/`token`/`contextEpoch`；同时钉住 I9（命中分支只 seal 并 return，不得调用 entitlement/字段策略/动作/modifier/trim）和 I10（key 含主体组摘要，token 含 ACL/规则/用户行/业务与字段策略定义）。

### （4）实测（无插桩探针，同探针同场景 A/B）

| 指标 | 基线 | 本轮 | 变化 |
| --- | ---: | ---: | ---: |
| 记录表单首次 dispatch | 2669.028 ms | 2513.162 ms | −5.8% |
| 记录表单热中位（偶数样本中间两项均值） | 688.528 ms | 501.288 ms | −27.2% |
| 记录表单窗口最大值 | 711.902 ms | 551.859 ms | −22.5%（仅本次窗口观察） |
| `v2_source_assembly` 热中位 | 130.0 ms | 121.5 ms | −6.5% |
| `post_trim` 热中位 | 84.5 ms | 21.0 ms | −75.1% |
| `post_runtime_seal` 热中位 | 140.5 ms | 38.5 ms | −72.6% |
| `v2_projection_and_seal` 热中位 | 651.5 ms | 405.0 ms | −37.8% |
| 列表热中位（对照） | 14.396 ms | 14.304 ms | 持平 |

六样本下 nearest-rank p95 等于窗口最大值，只能作为本次窗口观察，不能作为尾部分布结论。
原始 R12 日志的 700.6→520.2 ms 使用了错误的中位数取值；用同批原始样本复算后为
697.437→483.499 ms（−30.7%），窗口最大值 796.509→540.022 ms（−32.2%），无需重跑。

`record_overlay` 仍约 9–10 ms，保持逐请求执行；`v2_projection_and_seal` 的剩余成本主要在源装配、业务类别/关系注入与 seal。

### （5）语义等值（先于收益比较）

旧的“按字段名在任意深度删除 `timing`”过滤器会误删真实业务字段
`data.business.timing.deadline`（1→2 仍被判相等），因此旧 `4bfa3c1a6d2254fe…`
摘要与“完整响应等价”结论**撤回**，`sce-r13-*` 仅保留为计时证据。修正后只豁免 10 条
已登记精确路径（顶层 `meta.elapsed_ms`、`meta.projection_cache`、`data.meta` 的四个
request/trace 身份键、两个 contract `context` 容器中的 `trace_id`/`request_id`）。
新窗口基线与本轮过滤后全树 SHA-256 均为
`ff6db9d1bdd3beb91a2f5f183c87321573677506d19d2141d994dffd010bbefb`，
`contractSha256` 均为 `1673cb0b2f037845…`，section 摘要全部一致；热响应差异路径只有
`meta.elapsed_ms` 与 `meta.projection_cache.stages_ms.*`，没有任何业务子树。
反例已固化为 `scripts/verify/test_local_dev_runtime_record_form_probe.py` 的 9 项非零测试。

### （6）门禁

- `make verify.unified_page_contract.v2.assembler` → PASS（sources=4；含 I9/I10）。
- `make verify.unified_page_contract.v2.client` → PASS（clients=3）。
- `python3 addons/smart_core/tests/test_contract_lifecycle.py` → 23 tests OK。
- `python3 addons/smart_core/tests/test_unified_page_contract_v2_mobile_compact.py` → 128 tests OK。
- `python3 addons/smart_core/tests/test_load_contract_response_cache.py` → 48 tests OK（含角色/策略失效反例）。
- `make local.dev.runtime.projection_cache_identity.probe` → PASS（角色撤销与策略变化均使 key/token 移动，savepoint 回滚恢复，commit 被拒绝）。
- `make verify.system.performance.baseline.unit` → 70 tests OK。
- 证据：`artifacts/main-scheduled-ci-closeout-20261016/sce-r14-record-form-{baseline,after}-precise-semantic.log`、`…sce-r14-projection-cache-identity.log`；`sce-r13-*` 仅保留为原始计时与错误过滤器的历史证据。

### （7）边界与未声称

- 不冻结、不 `ci.local.quick`、不推送、不合并、不部署；不宣称批次验收完成、主线集成完成或产品交付完成。
- 不恢复 record 级整装配缓存；不得用 `write_date`、TTL 或前端 key 代替运行时权限与关联记录事实。
- 首次打开（首次契约约 1.74 s、首次 `system.init` 约 1.75 s）与真实页面端到端等待仍未关闭；gen-2 GC 长尾仍未证明消除。

## R13 证据口径与缓存边界校正（2026-10-17，只读复核后执行；不冻结）

### （1）声明

- **Formal Product Layer**：P0 平台内核产品；P4 仅为测量与验证工具。
- **Layer Target**：`smart_core` 契约运行时缓存身份与命中路径；`scripts/verify` 测量探针。
- **Standard vs User-Specific**：平台机制与验证口径，不含行业/客户语义。
- **Why Here**：缓存命中是否安全由 `cache_key`/`source_token` 与失效机制决定；测量是否可信由探针统计和语义比较决定。
- **Why Not Elsewhere**：不得用前端 key、TTL 或 `write_date` 代替权限/策略事实；不得恢复 record-bound 整装配缓存。
- **Blast Radius**：record-free 已装配命中、源投影身份、测量结论与文档；不改变记录表单的逐请求 overlay/权限/输出语义。

### （2）修正的三项证据问题

1. **中位数口径**：`_stats` 原用 `values[len // 2]`，六样本时取第 4 个值。现改为偶数样本中间两项均值；nearest-rank p95 在六样本时显式标记为窗口最大值，不作为尾部分布结论。同批已有样本正确复算为 `697.437 → 483.499 ms`（−30.7%），窗口最大值 `796.509 → 540.022 ms`，未重跑。
2. **语义比较范围**：旧 `_semantic_copy` 按字段名在任意深度删除 `timing`，已用 `data.business.timing.deadline` 1→2 证明会漏判。现仅豁免 10 条登记精确路径；新增“业务字段改变必须失败”“未登记 `context.trace_id` 必须保留”等 9 项反例。
3. **缓存命中描述**：record-free 已装配命中的实际路径是复用缓存 `source_contract`/`contract`、只执行 runtime seal 后返回；它跳过 entitlement、字段/业务策略、动作、modifier/status 与 trim。seal 只刷新 request/trace 身份与摘要，**不是授权**。安全边界由 `cache_key` 的组摘要/公司/上下文与 `source_token` 的 ACL、规则、用户行、策略定义、代码身份共同保证。

### （3）缓存身份与失效证据

受管运行时探针在 `sc-local-dev/sc_dev_demo`、uid 45、公司 1 上执行：

- 移除组 128 `smart_construction_core.group_sc_role_finance_manager`：`cache_key` 与 `source_token` 同时变化；
- 草稿业务配置契约 id 27（`construction.contract`）`priority` +1：`source_token` 变化；
- 两个 savepoint 回滚后 key/token/组集合逐字节恢复，commit 被拒绝。

非零单测同时覆盖：角色撤销改变 key、公司范围改变 key、ACL/规则/用户行变化改变 token、业务策略定义变化改变 token、旧已装配条目在角色或策略变化后不可达。

### （4）门禁与边界

静态守卫已扩展为 I9/I10 fail-closed：命中分支不得调用 entitlement/策略/动作/modifier/trim；key 必须含主体组摘要；token 必须含 ACL、规则、用户行、业务/字段策略定义。文档、单测与运行时探针三者绑定同一结论。

本段不冻结、不 `ci.local.quick`、不推送、不合并、不部署。首次打开/启动与真实页面“点击→可操作”仍未完成，下一段只做首次视图读取、翻译加载与契约编译的分别归因。

## R15 请求内事实复用与启动响应确定性（2026-10-17，不冻结）

### （1）声明

- **Formal Product Layer**：P0 平台内核产品；P4 仅为受管测量工具。
- **Layer Target**：`smart_core` 导航/路由事实导出与身份投影；`smart_construction_core` 启动扩展事实入口。
- **Standard vs User-Specific**：平台机制，不含行业/客户语义。
- **Why Here**：菜单与组事实是导航裁定的输入，重复导出只增加成本，不产生新语义。
- **Why Not Elsewhere**：不得用跨请求缓存或前端 key 替代裁定；不得把 ACL/模型实现细节搬进前端。
- **Blast Radius**：`system.init` 的 `navigation`、`nav` 与 `user` 投影；路由准入集合不变。

### （2）改动

1. **请求内菜单事实复用**：`MenuService._menu_fact_snapshot(kind)` 让可见事实与授权事实在单个请求内各导出一次，供 contextual routes、route authority 与最终导航复用。两者回答不同问题，不互换。
2. **扩展事实去重**：`smart_core_extend_system_init` 在融合入口已写入 `ext_facts["smart_construction_core"]` 时不再重复调用 `get_system_init_fact_contributions`。
3. **启动响应确定性**：`SystemInitIdentityPayload.build` 对 `groups_xmlids` 稳定排序。该字段原按 Python `set` 顺序输出，同一身份在不同进程产生不同字节；这是等价性证据此前逐次变化的原因。

### （3）探针修正

- 变量改为 `PRODUCT_PERFORMANCE_STARTUP_FACT_REUSE_{MODE,PROFILE,SAMPLES,DETAIL}`，经 `odoo_shell_exec.sh` 的 `PRODUCT_*` 白名单转发。此前 `STARTUP_FACT_REUSE_MODE` 未被转发，标记为 previous 的日志实际跑的是 candidate。
- `previous` 复现必须包裹**包命名空间**的 `smart_core_extend_system_init`；包裹 `core_extension` 模块属性不会被 `run_extension_hooks` 的派发命中。计数同时覆盖包命名空间与模块全局两处 `get_system_init_fact_contributions`。
- 新增 `PROFILE`：`counter` 统计调用并抬高耗时；`timing` 不装计数器，只测时间。中位数由 `statistics.median` 对热样本计算，不再用固定下标。

### （4）A/B 结果（`sc-local-dev`/`sc_dev_demo`，uid 45，公司 1，单主体）

| 指标 | previous | candidate | 变化 |
| --- | --- | --- | --- |
| 热样本耗时中位数（timing，6 样本） | 364.030 ms | 315.095 ms | −13.4% |
| 热样本耗时中位数（counter，4 样本） | 372.339 ms | 324.333 ms | −12.9% |
| 热请求 SQL 中位数 | 629 | 597 | −32（−5.1%） |
| 首请求 SQL | 3022 | 2990 | −32 |
| 首请求耗时 | 1762.204 ms | 1757.683 ms | 冷启动主导，未见差异 |
| 菜单事实扫描/请求 | 4 | 2 | −2 |
| 可见事实导出/请求 | 3 | 1 | −2 |
| 授权事实导出/请求 | 1 | 1 | 0 |
| 扩展贡献计算/请求 | 2 | 1 | −1 |
| 路由权威构建/请求 | 2 | 2 | 0 |
| DeliveryEngine.build/请求 | 1 | 1 | 0 |

### （5）等价性

两种模式、两个独立进程、全部样本的以下摘要完全一致：

- `route_authority_sha256=468fbadd…`（primary 15 / contextual 31 / denied 33 / container 1 / role_home 1）
- `navigation_sha256=487a1232…`
- `data_semantic_sha256=b7ef60dc…`，`data_json_bytes=379649` 逐字节相同，19 个顶层 section 摘要全部相等

结论边界：这是**后端单主体、进程内**的等价与耗时证据；不含 HTTP/浏览器、多角色矩阵，也不证明 GC 长尾。首请求差异不可归因于本轮改动。

### （6）门禁

- `make verify.backend.navigation_delivery.unit` → PASS（含菜单事实复用回归 1 项）。
- `python3 addons/smart_core/tests/test_system_init_payload_builder_semantics.py` → 19 tests OK（新增 `groups_xmlids` 稳定排序反例）。
- `make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestProjectMemberRoleSurface.test_system_init_hook_reuses_merged_extension_facts'` → 1 test，0 failed。
- 证据：`artifacts/main-scheduled-ci-closeout-20261016/sce-r15-startup-fact-reuse-{previous,candidate}-{counter,timing}.log`。

### （7）边界与下一项

- 不冻结、不 `ci.local.quick`、不推送、不合并、不部署。
- 路由入口字段分层与 `entry_key` 迁移口径见 `docs/architecture/route_entry_contract_field_layering_v1.md`；本轮未实施协议迁移、未删除任何字段。
- 前端改造范围较大，已登记为独立计划任务 `.agent/goals/ROUTE-ENTRY-CONTRACT-MIGRATION.yaml`（`status: planned`），按专题处理。当时登记的 4 条开放缺陷已在 R15.2 逐项最小闭环，`openContractDefects=0`，`verify.frontend.contract_basis.enforce` PASS；剩余的 `router/index.ts` 与 `useBusinessConfigNavigation.ts` 模型名查找仍属后续 P0-1/P0-2 迁移，本轮不声称前端已完全摆脱模型名。
- 路由权威条目的静默丢弃属前端协议迁移，已并入独立计划任务，不阻塞本轮后端性能主线；后端性能主线以 R15.1 的系统运行性能基线重采收口。

## R15.1 系统运行性能基线重采（2026-10-17，后端性能主线收口；不冻结）

### （1）收口条件与边界

- 本轮主线是**后端运行性能收口**，收口条件是建立可复现、绑定当前代码身份的系统运行性能基线。
- 测量工具归属 P4；被测机制归属 P0（`smart_core` 启动、导航与契约运行时）。采样政策、阈值政策与平台 SLA 口径均未改变。
- 该收口只覆盖 `controlled_regression`。`daily_experience` 与 `capacity` 未完成时，只能声明“受控回归基线已建立”，不能声明批次验收、主线集成、版本发布或产品交付完成。

### （2）采集身份与环境

- 命令：`ENV=dev ENV_FILE=<main checkout>/.env.dev PRODUCT_PERFORMANCE_BASELINE_SOURCES=sla,observe,contract_profile,contract_request,permission,cache_identity,role_matrix make local.dev.runtime.performance.baseline`
- 环境：`sc-local-dev` / `sc_dev_demo` / dbfilter `^sc_dev_demo$`；运行时 `17.0-20260630`；容器 `sc-local-dev-odoo-1`。
- 采集前重建容器以加载当前工作树代码：`/mnt/source-addons` 在 addons_path 中先于 `/mnt/product-addons`，容器内 `menu_service.py` 哈希与本工作树一致。
- 刷新原因：旧基线生成于 `2026-10-17T01:18:12Z`，早于 R15 改动，其代码身份不能被本轮继承。

### （3）记录结果

- `status=baseline`，`gaps=0`，`entries=7`，`samples observed/retained=142/142`。
- 代码身份：`target_code_identity.head=eda906b3eaac360aa885c46d70247a174c5e1c5f`，`dirty=true`；`source_code_identity` 记录 `addons/smart_core/delivery/menu_service.py=323bce4af9bfd6996470b10aa98153b5aaf3f0d64f1f1c5274718b13e7f56240`，全量 9 个探针声明文件。
- 身份边界：`addons/smart_construction_core/core_extension.py` 与 `addons/smart_core/core/system_init_identity_payload.py` 不在探针声明文件清单内，只由 HEAD+dirty 覆盖；这两个文件的运行效果已由 R15 的 A/B 与等价性证据单独覆盖。
- 记录：`artifacts/backend/system_performance_baseline.json`，sha256 `7ea91f55d50d1adf363979aaaf31e6e6747e891b7726282aecb58873ed50e7fd`。

### （4）三层状态

| 层 | 状态 | 说明 |
| --- | --- | --- |
| `controlled_regression` | `passed` | 5 个身份匹配条目；`sla-guard` 与 `cache-identity` 按声明不承载产品代码身份，记为 unknown |
| `daily_experience` | `not_run` | 需要绑定部署、真实网络路径、代表角色与数据规模 |
| `capacity` | `target_unresolved` | 目标并发、数据规模、吞吐与错误预算未确认 |

### （5）与上一基线差异（同环境、单次观察，不作回归归因）

| 指标 | 旧基线（01:18Z） | 本基线（04:46Z） |
| --- | ---: | ---: |
| `warm_contract_dispatch` p95 | 78.22 ms | 77.81 ms |
| `cold_contract_assembly` max | 249.36 ms | 187.20 ms |
| `first_contract_assembly` first | 1742.09 ms | 1620.22 ms |
| `startup_system_init_first` first | 1754.91 ms | 1724.86 ms |
| `startup_system_init_http` p95 | 649.01 ms | 768.54 ms |
| `warm_startup_repeat` p95 | 464.26 ms | 414.86 ms |

成熟系统目标总体为 `within_tolerance`（met 4 / within tolerance 2 / failed 0 / not evaluated 1）。`startup_system_init_http` 是单样本 p95，仍低于 800 ms 目标；其升高不得归因于本轮改动。`profile_first_contract_assembly`（profiled `3732.94 ms`）按声明仅作诊断，不参与绝对目标评级。

同一次采集重生成的平台 SLA 报告每次意图只有 6 个样本，6 样本 p95 接近最大值，且采集紧接容器重建：`system.init` p95 `768.54 ms`（限 `8000`）、`ui.contract` p95 `1564.38 ms`（限 `5000`）、`execute_button` `23.34 ms`。该次采集全部请求为 2xx、零错误；这些 HTTP 层数字只作观察，不作暖态回归归因。SLA 报告随基线刷新同步更新，后续 R15.2 重采会再次覆盖该报告。

### （6）门禁

- `make verify.system.performance.baseline.unit` → 70 tests OK（含 negative gap 与 positive baseline 用例）。
- `make ci.local.iteration` → PASS（`dirty` / `L1_only` / `receipt=none`）。
- `git diff --check` → exit 0。

### （7）收口结论与残余

- 受控回归基线已绑定当前候选重新建立，后端性能主线按既定条件收口；本记录不冻结、不 Quick、不推送、不 PR、不合并、不部署。
- `daily_experience` 需在目标部署测量真实页面“点击→可操作”，并区分网络、串行请求、后端与前端耗时；旧版体验数据不得归因本轮。
- 前端 `entry_key` 协议迁移继续作为独立计划任务 `.agent/goals/ROUTE-ENTRY-CONTRACT-MIGRATION.yaml` 专题处理，不属于本轮性能收口范围。

## R15.2 审核收口：契约门禁、缓存口径与运行投影（2026-10-17，不冻结）

### （1）范围与边界

- 响应独立审核 `REQUEST_CHANGES` 的 S1（契约门禁阻断）与 S2（缓存分层文档自相矛盾）；不再扩展性能优化，不追求额外毫秒收益，不完成整个 `entry_key` 迁移。
- 本记录只推进“固定范围 → 修正两项审核问题 → 补受影响验证”。不冻结、不 `ci.local.quick`、不推送、不 PR、不合并、不部署。
- 可认可状态仍为**受控回归基线已建立**；批次验收、主线集成、部署与产品交付分别判断。

### （2）S1：契约门禁闭环

1. **声明载体**：后端新增 `build_web_surface_entry_target()`（`addons/smart_core/core/navigation_entry_target.py`），只投影 action 已声明的 `sc_web_surface` / `sc_web_route`，不从模型名、路由拼写或未声明的 context 键推断。
2. **声明补齐**：配置工作台与菜单配置 action 显式声明 `sc_web_surface` 与 `sc_web_route`（`business_config_workbench_views.xml`、`ui_menu_config_policy_views.xml`）。
3. **前端消费**：`actionRoutePolicy.ts` 删除模型名常量比较、Odoo context 字符串正则与模型语法正则，只消费 `entry_target`；缺失或非法声明抛 `ContractGapError`。
4. **不再静默丢弃**：`normalizeRouteAuthorityContract()` 对版本、bucket、条目形状、`route_kind`、`entry_target` 非法均报契约缺口；主体不匹配仍按授权拒绝返回 `null`。
5. **台账**：`docs/architecture/frontend_contract_basis_ledger.json` 的 `openContractDefects=[]`、`closedContractDefects=18`、`declarationBindings=11`；`verify.frontend.contract_basis.enforce` 从 STOP 转为 PASS。
6. **未完成边界**：`frontend/apps/web/src/router/index.ts` 与 `frontend/apps/web/src/views/businessConfigSurface/useBusinessConfigNavigation.ts` 仍有模型名查找；`actionRoutePolicy.ts` 的 `resolveAuthorizedConfigurationRoute` 在 record/model-form 路径上仍比较路由模型与契约声明的 authority 模型。三者均已登记为 `.agent/goals/ROUTE-ENTRY-CONTRACT-MIGRATION.yaml` 的后续项（P0-2/P0-5）。本轮不删除、不声称迁移完成。

### （3）S2：缓存分层口径统一

- `docs/architecture/contract_runtime_cache_layers_v1.md` 统一为：record-free 已装配缓存命中后跳过 entitlement、策略、动作、modifier 与 trim；`seal` 只刷新保存搜索与摘要，不是授权。
- 明确“逐请求”适用于未命中的装配/投影管线；缓存有效性与失效由缓存键、版本与失效机制保证，`re-seal` 不作为权限重算证据。
- 禁止 record-bound 整装配缓存的边界不变。

### （4）运行投影缺陷与修复

- 受管运行验证发现：`business_config` 的 route authority 条目原为 `type=compatibility`，原因是 `DeliveryEngine` 只刷新 `meta.entry_target`，而 `MenuService._nav_target_index` 先读节点级 `entry_target`，旧值覆盖了声明投影。
- 修复：`_normalize_delivery_nav_node_refs()` 同步 `node["entry_target"] = meta["entry_target"]`，保证节点与 meta 同一身份。
- 反例测试：`test_entry_publication_authority.py` 新增“声明 admin_surface 必须同步到节点目标”用例；`test_delivery_menu_entry_target.py` 覆盖声明投影本身。
- 受管升级 `smart_core,smart_construction_core` 后，`sc_dev_demo` 的 published authority 对 `sc_demo_business_config`（uid 21）同时带 `business_config` 与 `menu_config`，对 `demo_full`（uid 55）带 `business_config`；路由分别为 `/admin/business-config` 与 `/admin/menu-config`，`business_config` 带 `root_menu_xmlid=smart_construction_core.menu_sc_root`。

### （5）门禁与证据

| 层级 | 命令 | 结果 | 证据 |
| --- | --- | --- | --- |
| L1 | `make verify.product.entry_publication.unit` | PASS（17 + 13 + 3 tests） | 见命令输出 |
| L1 | `make verify.frontend.navigation_shell.unit` | PASS（110 tests + guard `components=5`） | `artifacts/main-scheduled-ci-closeout-20261016/sce-r15-2-navigation-shell.log`，sha256 `07579947…` |
| L1 | `make verify.nav.pro01r.route_authority.unit` | PASS（10 + 2 + 12 + 16 + 16 cases） | `artifacts/main-scheduled-ci-closeout-20261016/sce-r15-2-route-authority-unit.log`，sha256 `fde51552…` |
| L1 | `make verify.frontend.contract_basis.unit verify.frontend.contract_basis.enforce` | PASS（15 tests；`open_defects=0`） | `artifacts/main-scheduled-ci-closeout-20261016/sce-r15-2-contract-basis.log`，sha256 `bc758177…` |
| L1 | `python3 scripts/verify/test_local_dev_runtime_entry_target_probe.py` | PASS（9 tests） | 含负例：缺面、错路由、缺根菜单、未声明面、相对路由 |
| L3 | `make local.dev.upgrade MODULE=smart_core,smart_construction_core` | PASS（含 authority verify） | `artifacts/main-scheduled-ci-closeout-20261016/sce-r15-2-module-upgrade.log`，sha256 `dc95485d…` |
| L3 | `make local.dev.runtime.entry_target.probe` | PASS（两主体零违规） | `artifacts/main-scheduled-ci-closeout-20261016/sce-r15-2-entry-target-probe.log`，sha256 `f6c42c5d…` |
| L1 | `make ci.local.iteration` | PASS（dirty / L1_only / `outside_scope=[]`） | `artifacts/main-scheduled-ci-closeout-20261016/sce-r15-2-iteration.log`，sha256 `7c6ea8f5…` |
| L1 | `git diff --check` | PASS（exit 0） | 见命令输出 |

- 本地升级属于受管 `local.dev` 生命周期写入，不是部署；只刷新 `sc-local-dev`/`sc_dev_demo` 的模块视图数据。
- 运行探针只读：`commit` 被拒绝、事务回滚，不写产品数据、schema、fixture 或 ACL。

### （6）收口结论与剩余

- 两项审核阻断已按最小范围处理；本轮不新增性能结论，不改采样与阈值政策。
- `daily_experience` 仍为 `not_run`，`capacity` 仍为 `target_unresolved`；短窗口数据不能证明 GC 长尾消失。
- 后续顺序：汇总受影响证据对全部改动输入的绑定 → 冻结前置与所选发布车道检查 → 独立复核 → 受保护 PR 集成；每一步需在获得相应授权后执行。

### （7）基线重采：绑定 R15.2 全部输入

- 原因：R15.1 基线记录的 `menu_service.py` 哈希为 `323bce4a…`，R15.2 的入口投影改动后当前文件为 `c6dba956…`；`delivery_engine.py` 虽不在 9 个声明身份文件内，但属于导航与路由权威的运行依赖。旧基线不能绑定当前候选。
- 命令：`ENV=dev ENV_FILE=<main checkout>/.env.dev PRODUCT_PERFORMANCE_BASELINE_SOURCES=sla,observe,contract_profile,contract_request,permission,cache_identity,role_matrix make local.dev.runtime.performance.baseline`
- 结果：`status=baseline`，`gaps=0`，`entries=7`，`samples observed/retained=142/142`；`target_code_identity.head=eda906b3eaac360aa885c46d70247a174c5e1c5f`，`dirty=true`；`controlled_regression=passed`，`daily_experience=not_run`，`capacity=target_unresolved`。
- 记录：`artifacts/backend/system_performance_baseline.json`，sha256 `4edc92ce…`；采集日志 `artifacts/main-scheduled-ci-closeout-20261016/sce-r15-2-performance-baseline.log`，sha256 `9fab4166…`。

| 指标 | R15.1（04:46Z） | R15.2 重采（05:26Z） |
| --- | ---: | ---: |
| `warm_contract_dispatch` p95 | 77.81 ms | 70.66 ms |
| `cold_contract_assembly` max | 187.20 ms | 200.11 ms |
| `first_contract_assembly` first | 1620.22 ms | 1644.24 ms |
| `startup_system_init_first` first | 1724.86 ms | 1701.10 ms |
| `startup_system_init_http` p95 | 768.54 ms | 1418.72 ms |
| `warm_startup_repeat` p95 | 414.86 ms | 444.49 ms |

- 成熟系统目标总体为 `within_tolerance`（met 3 / within tolerance 3 / failed 0 / not evaluated 1）。两次采集都是单窗口观察，差异不作为本轮回归或收益的归因；尤其是 `startup_system_init_http` 只有 1 个 p95 样本，不能用于长尾结论。
- SLA 报告已随重采刷新：`system.init` p95 `1418.72 ms`（限 `8000`）、`ui.contract` p95 `814.53 ms`（限 `5000`）、`execute_button` `25.12 ms`（限 `3000`）。`execute_button` 6 次均为 `403`，工具归类为 `permission_guard`、`error_count=0`，仅产生 1 条 warning；本轮不把它归因为代码回归，也不宣称业务成功。SLA 报告：`artifacts/backend/platform_sla_report.json`，sha256 `308c94b2…`。
- 该重采只刷新受控回归基线与 SLA 观察；`daily_experience` 与 `capacity` 状态不变。

## R15.3 审核收口：拒绝记录身份、管理面声明完整性与 403 取证（2026-10-17，不冻结）

### （1）范围与边界

- 只处理审核提出的 S1/S2 两处阻断；性能优化保持封口，不追加毫秒优化，不做完整 `entry_key` 迁移。
- 未冻结、未 Quick、未推送、未 PR、未合并、未部署；状态仍为“受控回归基线已建立”。

### （2）S1：拒绝记录必须可被生产端与消费端同时接受

- 生产端 `MenuService.filter_route_authority_by_publication()`：条目被移入 `denied_actions` 时显式写 `route_kind="DENIED"`。此前只追加 `reason_code`，会保留 `PRIMARY_NAV`/`ADMIN_ROUTE` 等可执行种类，触发消费端 bucket 一致性校验。
- 消费端 `routeAuthority.normalizeEntry()`：`DENIED` 记录接受 `action_xmlid` **或** `menu_xmlid` 作为身份；两者都为空的拒绝记录仍是 `ContractGap`。严格校验保留，未恢复静默过滤。
- 真实反例（`sc_dev_demo` 发布权威，非构造数据）：uid 21 `denied=8`、uid 55 `denied=1`，两边都含 `menu_sc_root`（`action_id=0`、`action_xmlid` 为空、`source=role_surface.declared.not_delivered`）。修复前该形态会在 `route_authority.denied_actions[*].action_id` 抛缺口，导致整条 `system.init` 消费失败。

### （3）S2：区分“未声明管理面”和“声明不完整”

- `build_web_surface_entry_target()`：`sc_web_surface` 与 `sc_web_route` **都不存在**时返回 `{}`，普通 action 继续走 compatibility；只要其中一个存在、或原文出现声明键但静态解析失败，就投影为显式 `admin_surface`，缺失字段留空。
- 前端 `actionRoutePolicy.adminSurfaceTarget()` 对空 `surface` / 非法 `route` 抛 `ContractGapError`，不再有“缺一半就降级为 compatibility”的路径。
- 运行时探针新增 `partial_declaration_violations`，当前为空。

### （4）403 单独取证

- 主体：`sc_dev_demo` 的 uid 2 `Administrator`；记录：`project.project:1`；动作：`action_view_tasks`（`type=object`，`dry_run=True`）。
- 后端响应：HTTP 403，`code=PERMISSION_DENIED`，`message=ACTION_CONTRACT_AUTHORITY_MISSING`，`reason_code=PERMISSION_DENIED`。
- 结论：SLA 探针发送的是不带声明契约身份（`action_id` / `backend_identity` / `source_widget_id`）的裸按钮请求，`execute_button` 按契约 fail-closed 拒绝。这是**预期的声明契约拒绝**，不是代码回归，也不代表一次成功的状态迁移。
- `platform_sla_guard.py` 现在记录 `denial{http_status,code,message,reason_code}` 与 `denial_classification`；仅 `fail_closed_undeclared_action_authority` 被视为已解释，其余标记为 `unexplained` 留待人工判定。状态码分类不再单独充当证据。

### （5）受影响页面验收（前端真实消费，非后端探针替代）

| 主体 | 场景 | 结果 |
|---|---|---|
| uid 21 `sc_demo_business_config` | 带 8 条拒绝记录（含菜单级拒绝）的启动 | 通过；无页面错误 |
| uid 21 | `/admin/business-config` | 通过；`.business-config-page` 挂载，URL 未漂移 |
| uid 21 | `/admin/menu-config` | 通过；页面挂载，URL 未漂移 |
| uid 55 `demo_full` | 带 1 条菜单级拒绝的启动 | 通过；无页面错误 |
| uid 55 | 普通列表 `/a/878?menu_id=559` | 通过；20 行数据 |
| uid 55 | 记录 `/r/payment.request/99` | 通过；`data-state=ok` |

- 两个角色全程 `page_errors=[]`、`http5xx=[]`，未出现契约缺口文案。

### （6）证据失效集合

- 重跑：`menu_service.py` / `navigation_entry_target.py` 直接影响的 L2 单测与前端 route authority 守卫；`local.dev.runtime.entry_target.probe`（L3）；SLA 报告（工具输出结构变化）；受影响页面（L4）。
- 复用：缓存分层文档、性能基线采样、两个配置入口与普通列表/记录页面（其输入未变）；契约台账因新增完成绑定而重跑 `unit`+`enforce`，不默认重采七源。
- 未运行：完整浏览器矩阵、`ci.local.quick`、冻结。SLA 本次 `system.init` p95 为 584 ms，属热态单次观察，不作为新收益声明。

### （7）生成物刷新与冻结前置

- `make verify.frontend.contract_basis.unit verify.frontend.contract_basis.enforce`：15 项单测 PASS；`open_defects=0`、`bindings=11`、`exemptions=5`、`logic_sites=3`。台账闭合来自修复两个真实缺陷并补全完成绑定，未删除或改分类放行。
- `make ci.local.iteration`：PASS（`change_state=dirty`、`coverage=L1_only`、`receipt=none`）。`changedPathCount=227` 被测试台账的顺序编号重排放大；按路径集合比对，语义变化是新增 2 个测试资产、删除 0 个。
- `make ci.delivery.freeze.prepare`：PASS（`candidate=unfrozen`）。受跟踪生成物仅刷新测试台账、复杂度报告和分片队列：
  - 测试台账 1548 → 1550，新增 `test_local_dev_runtime_entry_target_probe.py`、`test_local_dev_runtime_record_form_probe.py`，无删除，相对顺序不变；行号整体位移是顺序 ID 重排。
  - 复杂度报告扫描文件 4838 → 4844（新增的 6 个探针/测试工具），需拆分行 67 → 68（`test_delivery_menu_entry_target.py` 增长到 1543 行）。
  - 其余内容绑定生成物（E2E 矩阵、模块依赖图、契约结构指纹等）无漂移。
- 生成物变化不影响上述页面证据：页面证据的输入是运行时契约与前端消费代码，均未被生成报告改动。生成改动已审查，尚未提交；当前仍是 dirty 候选，不是冻结身份，也不构成 Quick 或交付证据。

### （8）结论

- S1/S2 两处阻断已最小修复，生产端—消费端反例均落地，契约台账门禁、受影响页面、`ci.local.iteration` 与冻结前置检查均通过；可以进入汇总批次产品复核。
- 上述仅代表“定向验收 + 冻结前置通过”。批次验收尚未宣布；主线集成、部署、产品交付仍分别未发生，不得合并表述。

## R15.4 汇总批次产品复核（2026-10-17，执行端，不冻结）

### （1）候选身份与范围

- 候选：HEAD `eda906b3eaac360aa885c46d70247a174c5e1c5f` + 显式 dirty 范围（49 个路径）。
- 范围：R15.3 的 S1/S2 最小修复与验证资产；性能优化继续封口，不追加毫秒优化，不做完整 `entry_key` 迁移。
- 状态：未 commit、未冻结、未 Quick、未推送、未 PR、未合并、未部署。

### （2）产品面覆盖（复用 R15.3 原始证据）

| 产品面 | 主体/入口 | 结果 | 证据 |
|---|---|---|---|
| 带拒绝条目的角色启动 | uid 21，`denied=8`（含菜单级 `menu_sc_root`） | 通过；无契约缺口、无页面错误 | `sce-r15-3-affected-pages.log` |
| 带拒绝条目的角色启动 | uid 55，`denied=1`（菜单级拒绝） | 通过；无契约缺口、无页面错误 | `sce-r15-3-affected-pages.log` |
| 配置入口一 | `/admin/business-config` | 通过；页面挂载，URL 未漂移 | `sce-r15-3-affected-pages.log` |
| 配置入口二 | `/admin/menu-config` | 通过；页面挂载，URL 未漂移 | `sce-r15-3-affected-pages.log` |
| 普通列表入口 | `/a/878?menu_id=559` | 通过；20 行数据 | `sce-r15-3-affected-pages.log` |
| 普通记录入口 | `/r/payment.request/99` | 通过；`data-state=ok` | `sce-r15-3-affected-pages.log` |
| 真实契约消费 | 前端归一化器消费 live `system.init` | 通过；每条拒绝 `route_kind=DENIED` 且有身份 | `sce-r15-3-route-authority-consumption.log` |

- 两个角色全程 `page_errors=[]`、`http5xx=[]`。

### （3）反例与边界（生产端—消费端成对）

| 反例 | 期望 | 证据 |
|---|---|---|
| 仅 `menu_xmlid`、无 action 的拒绝记录 | 前端接受，不中断初始化 | 后端 `test_unpublished_declaration_is_republished_as_a_denied_record`；探针 `test_menu_only_denial_is_a_valid_denial_record`；前端 guard 菜单级拒绝用例 |
| 未发布条目被移入 `denied_actions` | 重写为 `route_kind=DENIED`，保留原身份 | 后端 publication 单测；前端 `PRODUCT_ENTRY_NOT_RELEASED` 用例 |
| 无身份拒绝记录 | 仍抛 `ContractGap`，不静默过滤 | 探针 `test_denial_without_identity_is_a_violation`；前端 `assertGap` 用例 |
| 拒绝记录保留可执行 `route_kind` | 视为违规 | 探针 `test_denial_keeps_its_executable_route_kind_is_a_violation` |
| `sc_web_surface`/`sc_web_route` 声明不完整 | 投影为显式 `admin_surface`，消费端停机 | 后端 `test_partial_web_surface_declaration_is_an_explicit_gap_target`；探针 `test_partial_declaration_must_project_to_an_explicit_gap`；前端 `adminSurfaceTarget` 缺口用例 |
| 普通 action 完全未声明管理面 | 保持 compatibility，不误报缺口 | 后端同组单测；探针 `test_complete_declaration_passes` 等 |
| `execute_button` 403 | 预期 fail-closed，不是回归 | `sce-r15-3-sla.log`：uid2、`project.project:1`、`action_view_tasks`、`dry_run`，`PERMISSION_DENIED/ACTION_CONTRACT_AUTHORITY_MISSING` |

### （4）未覆盖与不得外推的结论

- 未运行完整浏览器矩阵、`ci.local.quick`、冻结、发布候选门禁。
- 未覆盖正式 89 个入口的其余产品面、`daily_experience`、`capacity`、首次打开/启动专项、真实部署后的“点击→可操作”长尾。
- 上述页面通过只证明本批受影响面未回归，不证明产品整体交付或性能目标全部达成。

### （5）证据失效分析

- `ci.delivery.freeze.prepare` 只刷新测试台账、复杂度报告与分片队列；页面证据的输入（运行时契约、后端路由权威、前端消费代码）未变，因此复用 R15.3 页面证据，不重采七源。
- 台账/复杂度/分片报告的路径变化来自新增测试资产和顺序 ID 重排；按路径集合比对无删除，不改变任何运行时行为。
- `run.json` 与批次记录属于证据元数据，不影响 L2/L3/L4 结果输入。

### （6）复核结论

- 执行端汇总批次产品复核通过：S1/S2 修复、反例、受影响页面、契约台账门禁、`ci.local.iteration` 与冻结前置均一致，未发现新的功能回归证据。
- 该结论不替代独立复核。批次验收、主线集成、部署、产品交付仍分别是未完成状态；下一步需所有者明确授权后才进入“提交清洁候选→完整指纹→精确 HEAD Quick→独立复核→受保护 PR”。

## R15.5 增量证据绑定与当前候选基线（2026-10-17，不冻结）

### （1）问题与影响集合

- 冻结前身份问题：旧性能基线 `artifacts/backend/system_performance_baseline.json`（sha256 `4edc92ce…`）登记的 `menu_service.py` 哈希为 `c6dba956…`，S1 修复后当前文件为 `8896c6ba…`，旧基线不能直接称为当前候选基线。
- 同时发现 `platform_sla_guard.py` 在 R15.3 增加了拒绝取证字段，属于基线全局 `probe_and_budget_digest` 的输入变化。
- 用 `scripts/ops/evidence_scope.py` 建立七源单位集合（`sla`、`observe`、`contract_profile`、`permission`、`contract_request`、`cache_identity`、`role_matrix`），单位为“采集命令 + 探针哈希 + 该探针声明的产品文件哈希”，运行时身份绑定 `sc-local-dev` / `sc_dev_demo` / 容器与镜像 ID。
- 计划结果：受影响 `sla`、`permission`；可复用 `observe`、`contract_profile`、`contract_request`、`cache_identity`、`role_matrix`；`identity_changed=false`。计划：`artifacts/main-scheduled-ci-closeout-20261016/sce-r15-5-performance-scope-plan.json`，sha256 `fed1f59b…`。

### （2）只补受影响采集

- `sla`：首次按 `ENV=.env.dev` 直接调用未加载受管环境，`DB_NAME` 缺失导致登录失败；归类为调用/环境缺陷，不是产品失败。按 `scripts/common/env.sh` 加载受管 env 后重采 PASS，未改产品代码。
- `permission`：通过受管 `local.dev.runtime.permission.probe` 重采 PASS；新日志声明的 `menu_service.py` 哈希为 `8896c6ba…`，与当前文件一致。
- 其余五源原始日志保持不变，作为继承输入参与一次归一化；没有重采七源，也没有仅修改旧哈希。
- 归一化：`--strict` PASS，`status=baseline`、`gaps=0`、`entries=7`。所有声明了产品哈希的条目 `identity_match=match`；`sla` 与 `cache_identity` 按设计不声明产品哈希，仍为 `unknown`，不冒充匹配。
- 新基线：`artifacts/backend/system_performance_baseline.json`，sha256 `7bdb15f5…`；受跟踪报告 `docs/ops/audit/system_performance_baseline.md` sha256 `13f2bbed…`。
- 新 SLA 观察：`system.init` p95 `630.90 ms`、`ui.contract` p95 `877.16 ms`、`execute_button` `23.53 ms`（6 次均 403，`PERMISSION_DENIED / ACTION_CONTRACT_AUTHORITY_MISSING`，分类 `fail_closed_undeclared_action_authority`）。该 403 只证明裸请求被拒绝，不作为动作成功或性能收益证据。

### （3）继承关系落账

- 执行结果写回证据作用域台账：`sla`、`permission` 记为 `passed`；其余五源保留 `declared`（继承自旧基线登记哈希）。
- 再次 `plan`：`affected=[]`、`stale=[]`、`blocked=[]`、`execution_required=false`、七源全部可复用；`units_digest=5e7a658d…`。计划：`artifacts/main-scheduled-ci-closeout-20261016/sce-r15-5-performance-scope-plan-after.json`，sha256 `bc4752a1…`。

### （4）复用边界

- 页面证据继续复用：S1/S2 修复后未再修改运行时契约或前端消费代码，本次只重采性能证据，不改变页面输入。
- 本基线是当前 dirty 候选内容上的测量；提交后将以同一文件集合生成完整指纹，并在干净 HEAD 上再归一化一次仅更新 `target_code_identity`（不重采原始证据）。

### （5）结论

- 旧基线身份问题已闭合，当前候选基线不再引用过期 `menu_service.py` 哈希。
- 下一步：形成清洁候选并提交，生成完整指纹，然后执行一次精确 HEAD Quick。

## R15.6 清洁候选形成与干净 HEAD 归一化（2026-10-17，不冻结）

### （1）清洁候选

- R15.5 的 S1/S2 修复与证据重绑已提交为 `b136353474554b6f235d242746f4bdbc4b4a065f`（`fix(contract): 收口路由拒绝记录、管理面缺口与性能证据身份`）。
- 提交后复核 `git status --short` 为空；tracked/untracked 均无残留，本轮不再新开产品改动。

### （2）干净 HEAD 重归一化

- 在 clean HEAD `b1363534…` 上，用同一 `--identity-file` 与同一七源输入再归一化一次；不重采任何探针，不修改任何源日志。
- 字段级差异恰好 3 项：`generated_at`、`identity.target_code_identity.value.head`（`eda906b3…` → `b1363534…`）、`identity.target_code_identity.value.dirty`（`true` → `false`）。其余字段逐字节一致。
- 结果：`status=baseline`、`gaps=0`、`entries=7`；声明产品哈希的 5 个源 `identity_match=match`，`sla` 与 `cache_identity` 按设计不声明产品哈希仍为 `unknown`，`mismatches=[]`。
- 物证：JSON sha256 `9576c8f0…`；受跟踪报告 sha256 `bc66c721…`（仅 `generated_at` 行变化）；归一化日志 `artifacts/main-scheduled-ci-closeout-20261016/sce-r15-6-performance-baseline-rebind.log`，sha256 `5e1d48e0…`。

### （3）证据作用域复算

- 重归一化后再次 `plan`：`affected=[]`、`stale=[]`、`blocked=[]`、`execution_required=false`、`identity_changed=false`、`units_digest=5e7a658d…`，七源全部可复用。
- 计划文件 `artifacts/main-scheduled-ci-closeout-20261016/sce-r15-6-performance-scope-plan-postrebind.json`，sha256 `bc4752a1…`，与 R15.5 执行后计划逐字节一致，说明重绑没有改动任何单位输入。

### （4）提交后自引用绑定

- `target_code_identity` 无法指向包含它自身的提交。因此最终绑定方式为：候选提交存在后，以 JSON-only 再归一化一次，使 `head=<候选 SHA>`、`dirty=false`；受跟踪报告不再改写，其内容与重绑后 JSON 仅 `generated_at` 不同。
- 该次提交后重绑的最终 sha256 记入未跟踪归档清单与 PR 文本；受跟踪报告与它的差异仅为生成时间，不构成内容漂移。
- 原始证据身份不受影响：重绑不改变任何源日志、探针哈希或 `probe_and_budget_digest`。

### （5）状态

- 未执行 Quick、独立复核、外部归档、推送、PR 或部署。

## R15.7 Quick 首轮失败与验证面登记收口（2026-10-17，不冻结）

### （1）失败事实

- 在清洁候选 `6760de8a…`（指纹 `19127d7b…`）上执行一次 `make ci.local.quick`，退出码 2，未签发 receipt。
- 唯一失败门禁：`audit.verification.lane_coverage.check`（由 `verify.verification.lane_coverage` 汇入 `verify.contract.architecture.suite`）。
- 拒绝内容：`targets_zero_reference` 787→791、`local_only_scripts` 18→21，且 4 个 target 与 3 个脚本不在冻结身份集内。
- 归属判断：不是本轮 S1/S2 或性能证据改动引入的产品缺陷，而是 R14/R15 性能时段新增的本地只读探针与其单测从未登记。属 P4 验证工具面负债，本轮负责收口。

### （2）最小修复（登记，不删表面）

- `scripts/audit/verification_lane_dispositions.json`：登记 4 个探针 target，`disposition=local_diagnostic`、`owner=platform-team`、`review_by=2027-03-31`，理由写明需要活栈、不能进 Quick。
  - `local.dev.runtime.entry_target.probe`、`local.dev.runtime.projection_cache_identity.probe`、`local.dev.runtime.record_form.probe`、`local.dev.runtime.startup_fact_reuse.probe`。
- `scripts/audit/verification_lane_exemptions.json`：登记 3 个 local-only 脚本，沿用既有 `local_performance_probe` / `local_quick_only_unit` 分类。
  - `local_dev_runtime_projection_cache_identity_probe.py`、`local_dev_runtime_record_form_probe.py`、`test_local_dev_runtime_record_form_probe.py`。
- `scripts/audit/verification_lane_baseline.json`：用唯一受管入口 `--write-baseline` 重写，属守卫声明的“deliberate, reviewed action”，不是手工改哈希。
- 两个登记文件的改动均为纯新增（`42 insertions`），未改动或删除既有条目。

### （3）基线扩展范围核验

- 重写后差异恰好 7 项身份 + 4 项关联计数：`max_targets_zero_reference` 787→791、`max_local_only_scripts` 18→21、`recorded_targets_defined` 2356→2360、`recorded_targets_unreached_from_anchor` 2181→2185。
- 没有任何无关身份被顺带扩入；未修改产品代码、探针断言或执行车道。

### （4）验证

- `make verify.verification.lane_coverage`：`PASS surface within the frozen baseline`，自检 72 tests OK。
- 未重跑与本次改动无关的门禁；Quick 仍需在最终冻结 HEAD 上重新执行一次。

### （5）状态

- 未独立复核、未归档、未推送、未部署。

## R15.8 Quick 二次失败：AST 测试台缺依赖注入（2026-10-17，不冻结）

### （1）失败事实

- 在候选 `6a369199…`（指纹 `65c05b48…`）上执行 `make ci.local.quick`，退出码 2，未签发 receipt。
- 失败门禁：`verify.product.menu.metadata_batch.unit`。
- 报错：`NameError: name 'build_web_surface_entry_target' is not defined`，位置 `addons/smart_core/delivery/menu_service.py:381`。
- 归因：S2 修复在 `_route_entry_from_menu` 中调用模块级导入 `build_web_surface_entry_target`；而 `scripts/verify/test_menu_metadata_batch.py` 以 AST 抽取类方法、在自建命名空间中 exec，命名空间未提供该模块级依赖。属 P4 测试工具面未同步，不是产品逻辑缺陷；产品调用本身是声明投影的既有职责。

### （2）最小修复

- `scripts/verify/test_menu_metadata_batch.py`：按路径加载纯 Python 的生产模块 `addons/smart_core/core/navigation_entry_target.py`，把真实的 `build_web_surface_entry_target` 注入测试命名空间。
- 未打桩、未在测试中复制实现，因此 S2 的“不完整声明显式停机”行为仍由真实代码参与断言。
- 改动仅该文件（`9 insertions, 1 deletion`），未触碰产品代码、门禁定义或其他测试。

### （3）定向验证

- `make verify.product.menu.metadata_batch.unit`：6 tests OK，退出码 0。
- 该失败属 fail-fast 捕获；修复后按影响集合只需重跑本单元，Quick 仍需在最终冻结 HEAD 上整体重跑一次。

### （4）状态

- 未独立复核、未归档、未推送、未部署。

## R15.9 远程 frontend_release_gate 失败：决策权威台账未随行号重导（2026-10-17，不冻结）

### （1）失败事实

- 候选 `b51a20b8…` 的 PR #669 运行中，`frontend_release_gate` 失败；失败点 `verify.frontend.decision_authority.unit` 的 `test_committed_ledger_matches_live_scan`。
- 报错：`committed decision-authority ledger is out of sync with the live scan; re-export it and review the diff`。
- 归因：本批较早提交修改了 `frontend/apps/web/src/views/ActionView.vue`，行号整体位移；台账仍是位移前扫描结果。属生成台账未随源码重导，不是决策分类变化。

### （2）最小修复

- 通过受管入口 `make verify.frontend.decision_authority.export` 重新导出 `docs/frontend_productization/decision-authority-inventory-v1.json`。
- 台账差异仅 3 处 `lines`（`1433→1436`、`1423→1426`、`3068→3070`），`classification`、`literal`、`occurrences` 与统计（findings=139、distinct=99、contract-derived=51、frontend-logic-defects=0）全部未变。

### （3）验证

- `make verify.frontend.decision_authority.unit`：15 tests OK，守卫 PASS（每个决策均为契约派生、已登记缺口或声明渲染交互）。
- 本地 Quick 未覆盖该单元，因此此前本地通过不代表远程该车道通过；本轮把该单元纳入定向验证。

### （4）状态

- 新提交后候选身份变化，需重绑性能基线目标身份、重算指纹并在新 HEAD 上再跑一次 Quick；旧候选的归档与 PR 正文以新身份更新。
