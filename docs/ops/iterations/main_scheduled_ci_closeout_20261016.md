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
