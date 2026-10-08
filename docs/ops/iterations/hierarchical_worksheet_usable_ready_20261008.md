# 工作表「可用即就绪」+ 契约声明分页（2026-10-08）

## 1. 本轮目标（单一可验收结果）

两个工作表入口（`smart_construction_core.menu_sc_p1_expense_contract`、`smart_construction_core.menu_sc_payment_execution`）
在实测中要等整表拉完（约 40.4s）才声明 `data-state=ready`，导致矩阵探针 30s 超时。本轮让工作表在**首个可用批次**
到齐时即声明可用，并把「首屏页大小」改为**契约声明、前端消费**，整表续载作为独立的后台进度继续。

不放宽任何断言、探针等待启发式或 ACL/字段权限；不为付款/合同模型做前端特判；不新增全局测试框架。

## 2. 根因

- 探针 `scripts/verify/business_entry_matrix_browser.mjs` 以 `waitUntil='networkidle'` 导航、并等 `data-state != 'loading'`（30s）。
- 工作表旧实现用固定 `limit=5000` 循环拉全表，声明态要等整表拉完才可用：
  `construction.contract.expense` 8,513 行（首个 5000 行请求服务端约 16s）、`sc.payment.execution` 38,568 行。
- 契约缺口：工作表表面的 `config` 从未声明分页，而同族 `HierarchyBrowser` 已消费契约 `page_size`。
  也就是说，此前**前端只能自己造一个分页常量**——按最高职责界限，这个缺口本身就是契约缺陷。

## 3. 责任层与改动

| 责任层 | 载体 | 改动 |
| --- | --- | --- |
| P0 后端装配 | `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py` | `_inject_native_hierarchical_worksheet` 发布 `sheet.page_size`，取自受管通道 `hierarchical_worksheet.page_size` → `context.hierarchy_page_size` → native tree `page_size` → 平台缺省 50，声明层夹取 1..20000 |
| P0 前端渲染 | `frontend/apps/web/src/app/action_runtime/hierarchicalWorksheetDataSource.ts` | 新增 `ContractGapError` / `ContractDefectRef` / `requireDeclaredPageSize`；首个可用批次触发 `onUsable`；续载为登记传输机制常量（分块 5000、让渡 800ms） |
| P0 前端渲染 | `frontend/apps/web/src/components/action/HierarchicalWorksheet.vue` | 首个批次到齐即 `loading=false`，新增独立 `data-load-state` 反映后台续载 |
| 声明守卫 | `scripts/verify/frontend_scene_contract_consumption_guard.py` | 登记工作表声明消费；退役的前端兜底常量列为 forbidden |
| 契约缺陷机制 | `docs/architecture/frontend_contract_basis_ledger.json` + `scripts/verify/frontend_contract_basis_guard.py` | 台账绑定「声明 → 消费 → 缺失停机」；机制豁免必须登记且不得承载产品语义 |
| P0 前端消费原语 | `frontend/apps/web/src/app/contract/contractGap.ts` | 共享 `ContractGapError` / `requireDeclaredNumber`：消费缺声明即停机（工作表数据源改为复用它） |
| 交付冻结门 | `make/frontend.mk` + `make/ci.mk` | 新增 `verify.frontend.contract_basis.enforce`（存在未闭合缺陷即 FAIL）并挂入 `ci.delivery.freeze.prepare` |
| 最高职责界限 | `AGENTS.md`、`ARCHITECTURE_GUARD.md`、`docs/architecture/ai_development_guard.md`、`.agent/decisions/contract-driven-runtime-authority.yaml` | 前端只做渲染与交互；契约缺失即停机；前端无契约依据的判断即契约缺陷 |

## 4. 验证（本地，非交付证据）

- `make verify.frontend.hierarchical_worksheet.unit`：`hierarchical_worksheet_load_stage_test PASS cases=10`（含缺声明/非法声明直接停机、声明值原样消费、让渡行为）。
- `python3 addons/smart_core/tests/test_page_assembler_view_orchestration_versions.py`：`Ran 22 tests OK`（含 `sheet.page_size` 派生与优先序断言）。
- `make verify.frontend.rendering_detail_state.unit`：`PASS surfaces=173 gaps=0`。
- `make verify.frontend.scene_contract.consumption.guard`：`PASS`。
- `make verify.frontend.contract_basis.unit`：7 项单测 + 守卫 `PASS bindings=1 exemptions=2 logic_sites=26 open_defects=3`。

## 5. 前端逻辑审计结论（26 站点 / 3 契约缺陷）

按最高职责界限（前端只做渲染与交互，其余输入必须来自契约）对 `frontend/apps/web/src` 做 fail-closed 扫描，
共登记 **26** 个「前端自行加入判断」的站点：**23** 个属于 3 个契约缺陷簇，**3** 个判定为非缺陷
（渲染分发或已登记机制）。台账：`docs/architecture/frontend_contract_basis_ledger.json`；
守卫：`python3 scripts/verify/frontend_contract_basis_guard.py`（`--list-candidates` 列出全部扫描命中）。
计数校验：`4（簇 B）+ 13（簇 A）+ 6（簇 C）+ 3（非缺陷）= 26`。

### 5.1 缺陷簇 A — `CD-20261008-FRONTEND-SELECTED-LIMIT`（13 站点，产品面取数规模无契约声明）

前端自行决定「拉多少条」，而这些规模本应由契约/后端声明。

| 站点 | 前端自造的量 | 原因 |
| --- | --- | --- |
| `components/GlobalMessagePanel.vue` | 12 / 40 / 80 | 消息面板写死会话与消息拉取量 |
| `layouts/AppShell.vue` | 200 | 建议动作轨迹导出行数 |
| `views/SceneHealthView.vue` | 50 / 100 | 场景健康视图拉取量 |
| `views/ReleaseOperatorView.vue` | `action_limit 20` | 发布运维视图拉取量 |
| `views/businessConfigSurface/useBusinessConfigScopeLifecycle.ts` | 1000（三处） | 业务配置范围拉取量 |
| `views/businessConfigSurface/useBusinessConfigRemediationLifecycle.ts` | 1000 / `batch_limit 300` | 数据量与批大小均无契约依据 |
| `app/action_runtime/useActionViewScopedMetricsRuntime.ts` | 1 | 作用域指标取样量（取单条） |
| `app/runtime/unifiedPageContractLitePilot.ts` | 40 | Lite 试点拉取量 |
| `app/activityPageRetention.ts` | 由 `session.ts` 的 `MAX_ACTIVITY_PAGES=6` 决定保留量，非法输入兜底 1 | 会话页签保留量无契约声明（边界见 5.5） |
| `pages/contractForm/useNativeChatterRuntime.ts` | 20 | 协作区用户检索拉取量 |
| `pages/contractForm/useRelationRuntime.ts` | `limit ?? 80` | 关系字段选项拉取量 |
| `views/ActionView.vue` | 夹取 1..200 | 前端覆盖声明值边界（与本次移除的 `page_size` 夹取同口径） |
| `stores/session.ts` | `limit \|\| 20` | 会话检索链缺省（同文件另一处 `limit \|\| undefined` 属按声明省略，非默认值） |

收口条件：每个产品面用声明值替换前端常量与夹取；缺失或非法即 `ContractGapError` 停机，并由守卫覆盖。

### 5.2 缺陷簇 B — `CD-20261008-API-ENVELOPE-DEFAULT-LIMIT`（4 站点，请求信封缺省）

与簇 A 同源，单列以区分「信封缺省」这一独立声明责任：P0 `smart_core` 应在声明层提供信封缺省，前端只透传。

| 站点 | 前端缺省 | 原因 |
| --- | --- | --- |
| `api/data.ts` | `?? 40` / `?? 2000` | 列表信封缺省由前端常量决定 |
| `api/globalMessages.ts` | `?? 30` / `?? 40` | 全局消息信封缺省 |
| `api/chatter.ts` | `?? 20` | 协作区用户检索信封缺省 |
| `services/trace.ts` | `\|\| 50` / `\|\| 5`、最小 1 | 追踪查询取数量与下限 |

### 5.3 缺陷簇 C — `CD-20261008-CONTRACT-PARAM-FALLBACK`（6 站点，契约参数缺失时前端补默认/夹取）

声明**已存在**，但前端在缺失或越界时代前端补值，属「前端覆盖声明」，与已修复的 `sheet.page_size` 同口径。

| 站点 | 前端补的默认/边界 | 原因 |
| --- | --- | --- |
| `components/action/HierarchyBrowser.vue` | `page_size` 补 50、夹取 10..200 | 声明值须原样消费，缺失即停机 |
| `components/action/HierarchyPlanner.vue` | `page_size` 补 5000 | 同上 |
| `components/action/HierarchicalWorksheet.vue` | `variance_tolerance` 补 0 | 同口径需收紧（分页参数已改为缺声明即停机） |
| `pages/ListPage.vue` | `grouping.default_sample_limit` 补 0、按前端常量取分组样本 | 取样量应由声明决定 |
| `app/runtime/actionViewLoadResultRuntime.ts` | 沿 `groupSampleLimit` 兜底 3 | 声明缺失应停机 |
| `app/runtime/actionViewBatchArtifactsRuntime.ts` | 失败分页补 12（两处） | 同口径问题 |

### 5.4 判定为非缺陷（3 站点，保留在清单中并附理由）

| 站点 | 判定 | 原因 |
| --- | --- | --- |
| `app/runtime/actionViewGroupDrilldownRuntime.ts` | `registered_mechanism` | 仅把未声明 limit 解析为 0（表示未指定），不决定数据量 |
| `app/runtime/actionViewRouteRuntime.ts` | `registered_mechanism` | 仅做 URL 查询参数解析，不产生数据量默认值 |
| `app/presentation/collectionPaginationPresentation.ts` | `renderer_dispatch` | 按已声明总条数与页大小计算分页呈现，属渲染计算 |

### 5.5 待裁决的一处边界（不失守）

`app/activityPageRetention.ts` + `stores/session.ts:MAX_ACTIVITY_PAGES` 的「会话页签保留量」也可论证为
**交互/会话状态**（类似滚动位置与标签页保活）而非产品取数规模，本可归为交互域机制。本轮按**从严不放宽**原则
保留在缺陷簇 A，不做静默降级；若使用者裁决为交互域机制，再改为登记豁免（`carriesProductSemantics: false`）。

### 5.6 已闭合缺陷

- `CD-20261008-WORKSHEET-PAGE-SIZE`：`config.sheet.page_size` 已在装配层声明、前端原样消费、缺失即停机（见第 3、4 节）。


## 6. 机制：前端判断即停机 → 回契约要结果（三层 fail-closed）

把「前端只做渲染与交互」从约定升级为**强制机制**：一旦出现没有契约依据的前端判断，
立即停机并回到声明层要结果，不得由前端默认值/夹取/特判兜底。

| 层 | 入口 | 行为 |
| --- | --- | --- |
| 运行时（消费） | `frontend/apps/web/src/app/contract/contractGap.ts` | `requireDeclaredNumber` 在声明缺失/非法时抛 `ContractGapError`，调用方进入显式停机态；工作表数据源已改为复用该原语（`requireDeclaredPageSize`） |
| 静态（门禁） | `python3 scripts/verify/frontend_contract_basis_guard.py` | 扫描 `frontend/apps/web/src`；出现**未登记**的前端判断站点即 FAIL（立即停）；`--list-candidates` 列出全部命中 |
| 交付（冻结） | `make verify.frontend.contract_basis.enforce` → 挂入 `ci.delivery.freeze.prepare` | 存在**未闭合**契约缺陷（`openContractDefects` 或 `verdict=contract_defect_open`）即 FAIL，禁止冻结/放行 |

- 机制声明与接线由单测锁定：`scripts/verify/test_frontend_contract_basis_guard.py::test_mechanism_is_declared_and_wired`
  （断言台账 `mechanism` 三层齐全、`verify.frontend.contract_basis.enforce` 已登记为 make 目标、且已挂在 `ci.delivery.freeze.prepare`）。
- 台账 `mechanism` 段：`docs/architecture/frontend_contract_basis_ledger.json`；决策：`.agent/decisions/contract-driven-runtime-authority.yaml`（ARCH-DECISION-002，新增 5 条机制规则）。
- 治理文本：`AGENTS.md`、`ARCHITECTURE_GUARD.md`、`docs/architecture/ai_development_guard.md`。

### 6.1 本机制的即时效果（必须明说）

`ci.delivery.freeze.prepare` 现在会因 3 个未闭合缺陷（23 个前端站点）而 **STOP**。
即：本分支在缺陷闭合前**不得冻结、不得走交付车道**。这不是放宽或临时豁免，而是机制的预期行为：
要么在声明层补齐声明并由前端原样消费，要么由使用者显式裁决（见 6.5 边界）。本轮不做静默降级。

### 6.2 附带修复的既有 mainline 漂移（`verify.guard.registry`）

`make verify.guard.registry`（`ci.professional.backend` 必需门）在基线 `a2213be3` 上已是 **FAIL**：
`test_business_entry_matrix_incremental.py`（PR #620 引入）与
`test_login_envelope_consumption_guard.py`（PR #614 引入）以
`python3 -m unittest scripts.verify.<module>` 形式被 make 调用，但守卫审计把「模块形式调用」
只记为 file reference、不记为 make target，因而被判为 unwired 且无 disposition。

- 处理：在 `scripts/verify/registry.yaml` 为这 3 个脚本（含本轮的 `test_frontend_contract_basis_guard.py`）
  登记 `wire_or_retire: file-consumed`（事实性 disposition），并刷新生成快照
  `docs/audit/guard_registry/guard_registry.json`；`make verify.guard.registry` 复验 **PASS**
  （1312 active / 88 orphan / 186 unwired，0 undispositioned）。
- 未改审计工具本身的 wiring 模型：把「模块形式调用」计入 wired 会让既有 186 条 file-consumed
  disposition 变成 stale，属高风险改动，另行评估。

## 7. 边界状态

批次验收：进行中（本地 L1/L2 定向通过；运行态重走改到「主线合并 → 重建服务端产物」之后，见 8.6）。
主线集成 / 版本发布 / 产品交付：未声明完成。

## 8. 部署后发现运行态回归与根因（2026-10-08 续）

### 8.1 现象

PR #621 合并（main `514e1b51`）并按受管入口重建日常服务器前端后，普通列表入口在运行态
渲染即失败，业务入口矩阵探针报：

- `smart_construction_core.menu_sc_p1_expense_contract: the runtime declared no recognised presentation surface (declared by nothing)`
- `smart_construction_core.menu_sc_payment_execution: 同上`
- `console.error: [ActionView] render failed ContractGapError: 契约缺少合法声明 search.defaults.page_size_options`

### 8.2 根因（首次产生位置）

声明层**没有问题**。直连 `/api/v1/intent`（`ui.contract.v2` / `op=action_open`）实测两份契约都带
`searchContract.defaults.page_size_options=[10,20,50]`、`page_size_range={min:1,max:200}`；
用前端 `decodeContractV2Snapshot` 直接解码该应答也 `[OK]`。缺口在**前端消费形状**：

- `frontend/apps/web/src/app/runtime/actionViewListPageSizeRuntime.ts` 直接从入参顶层读
  `searchContract.defaults`；
- 调用方 `ActionView.vue:2990/2991`（以及 `:2386` 的指标扫描上界）传入的是 `ContractV2NormalizedStore`，
  契约快照只挂在 `store.snapshot` 之下，顶层没有 `searchContract`；
- 因此查询恒得 `{}` → `requireDeclaredNumberList(undefined)` → `ContractGapError` → 列表页渲染中止 →
  探针判定「未声明任何可识别呈现面」。

该解析器签名原为 `contract: unknown`，正是它让错误形状通过了类型检查。这不是「未识别 widget 导致错误默认值」，
也不是字段权限拒绝：声明存在且合法，纯粹是消费层拿错了载体。

### 8.3 修复责任层

P0 前端渲染机制（契约消费层），**未改声明层、未加前端兜底、未做付款模型特判**：

- 解析器改为类型化接收 `ContractV2NormalizedStore | null`，并通过既有规范访问器
  `resolveContractV2SearchContract(store)` 读取，前端不再自拼键路径；
- 载体形状漂移改由**编译期类型签名**拦截（`verify.frontend.typecheck.strict` 覆盖）；
- 声明缺失仍然停机（`ContractGapError` 语义不变）。

### 8.4 行为锁与证伪

新增 `frontend/apps/web/scripts/action_view_list_page_size_runtime_test.ts`，用**生产 store 工厂**驱动
**生产解析器**，锁定：声明原样消费、第二份声明给出第二份结果（证明不是前端常量）、缺失即停机、
「顶层 `searchContract` 不是载体」这一回归形状必须停机。挂入
`verify.frontend.action_view_page_size_runtime.unit`（quick / pr / release 三条前端车道）。

证伪：临时把解析器换回部署版实现，同一测试以**完全相同的线上报错**失败
（`ContractGapError search.defaults.page_size_options`），换回修复版 `PASS cases=11`。

### 8.5 复现出的体系缺口：复用身份里没有服务端修订

更值得注意的是这条回归是怎么「没被发现」的：`108/108` 的列表通过证据是在服务端 `f4279416` 上采集的，
换包到 `514e1b51` 后仍被判为**可复用**，所以只重走了 2 个键。

- `scripts/verify/business_entry_matrix_model.mjs::environmentIdentity` 原只绑定
  `base_url / database / login / denied_role_candidates`，并显式注释「故意排除服务端包修订」，
  约定由执行者「带着记录在案的 impact analysis」跨部署携带证据 —— 但没有任何机制**强制**这份分析存在。
- 处理（本次一并收口）：把**服务端修订**纳入复用身份。该值不是执行者声明，而是探针每次实测的
  `source_revision/git_sha`，并且探针在跑任何条目之前就拒绝不匹配的值；同修订的原样重部署不产生失效
  （复用效率保持），换修订则**强制**把上一代包上采集的证据判为 stale。
  `environmentIdentity` 现在对空修订直接拒绝，后续调用方无法悄悄省略。
- 锁定：`scripts/verify/business_entry_matrix_reuse_identity.test.mjs`（基线可绑定 / 同身份指纹稳定 /
  换修订指纹改变 / 空修订拒绝），挂入 `verify.frontend.business_entry.evidence_scope.unit`。

即：这条机制把「静默复用」改成了「要么同修订复用，要么重新取证」，正对应迭代效率要求
（能复用先复用）与证据有效性要求（输入变了必须失效）的交叉点。

### 8.6 当前边界与下一步

- 因为 8.5 的复用身份现在绑定服务端修订，运行态复核必须落在**最终服务端修订**上：
  顺序固定为 主线合并 → `make daily.runtime.*` 受管重建 → 在最终 served revision 上做**一次列表范围复核**。
- 受影响的浏览器证据按新规则全部判为 stale（这是预期结果，不是缺陷）：日常前端从 `f4279416` 换代到
  当前修订，上一代包上采集的条目不得继续复用。
- 环境 DENY 结论继续单独保留（两个挂载者同属一个项目不足以证明独占），未泛化为「环境全部通过」。

### 8.7 候选发布分支的受管续接（2026-10-08）

准备推送时发现 GitHub 上同名分支 `codex/hierarchical-worksheet-usable-ready-20261008` 仍指向
`88e5db43`，而它正是 **PR #621 已合并的 head**（合并提交 `514e1b51` 为单亲提交，
树与该 head 逐字节一致，即 squash 合并）。因此本次候选与远端同名 ref 必然分叉：

- `make pr.push` 正确拒绝非快进（`! [rejected] ... (non-fast-forward)`）；
- 强推被 allowlist 硬禁（仅在受管退役/切换入口内允许 `--force-with-lease`）；
- 受管退役入口 `make branch.retire.historical` 会把「仍被运行时载体（`.agent`）引用的分支」
  直接跳过，不做放宽。

处理：按 allowlist C 段允许的 `git checkout -b <new-allowed-branch>`，在同一提交
`0c43a012` 上以新分支 `codex/page-size-consumption-and-matrix-reuse-20261008` 续接本候选，
并把 run 绑定一并更新到新分支；旧的已合并远端 ref 保持原状（不删除、不强推），
待本次运行关闭、不再有载体引用它之后，再用受管入口清理残留引用。

副作用（如实记录）：分支名变化使上一轮 8 条本地 receipt 按 `branch` 条件失效，
需在新分支名下重新落 receipt，并对新 HEAD 重新跑**一次**`make ci.local.quick`。

## 9. ActionView surface 契约未就绪先渲染（PR #622 部署回归）— 2026-10-08

### 9.1 事实：部署后 80/89 业务入口整页失败

PR #622（`d2d51935`）部署到日常开发服务器后，89 个业务入口里 **80 个整页失败**：

- 证据 `artifacts/frontend-business-entry-matrix/incremental/20261008T144718Z-ec2ec3d9f94c/summary.json`：
  `ok=false`、`entries=89`、`problems=80`、`console_errors=162`，80 个键全为 `unknown-presentation`
  （"the runtime declared no recognised presentation surface"）。
- 162 条 console error 全部同一条：`[ActionView] render failed ContractGapError: 契约缺少合法声明
  search.defaults.page_size_options：前端不停机兜底，等待声明层补齐`。
- 通过的 9 键为 kanban 1 / form 5 / aggregate 2 / admin 1，**无一 table**。
- 历史对照：`7a0fb870`（#619 之前）89 键几乎全通过；`514e1b51`（#621）仅 2 键失败。

### 9.2 根因：契约投影未就绪就先渲染 surface

`ActionView.vue` 模板在 `actionContract.value === null`（规范化契约投影未就绪）时就已经进入
ListPage 分支：`viewMode` 可由路由/模型元数据先推导为 `tree` → `resolveContentKind('tree')` →
`vm.content.kind === 'list'`，于是列表分支上的 `:page-size-options="listPageSizeOptions"` 提前求值
`resolveActionViewPageSizeOptions(null)` → 抛 `ContractGapError` → 整页停机、声明不出任何展示面。

只有 ListPage 分支绑定了该 prop，所以失败面精确等于 table/hierarchical 入口。

已排除项（均有证据，勿重复排查）：后端声明正常（直连 intent 返回
`searchContract.defaults.page_size_options=[10,20,50]`）；浏览器收到的响应正常；解码器 / store /
解析器离线链路正确；线上包确实含新代码。完整调用栈落在模板 `h(...)` → compute
`listPageSizeOptions` → 解析器 → 抛错处，且当刻 `actionContract` 为 `null`。

### 9.3 责任层与修复

**P0 前端渲染机制**（通用渲染行为，无行业/客户语义；不是 P1）。新增
`frontend/apps/web/src/app/runtime/actionViewSurfaceGateRuntime.ts`，唯一判据
`resolveActionViewSurfaceDisplayState({renderError, hasContract, loadError})`，判定顺序固定：

1. `render-error`（渲染期契约缺口等错误）；
2. `surface`（契约已就绪，含 surface 自己的错误态）；
3. `load-error`（契约未就绪且加载已失败）；
4. `contract-pending`（契约未就绪 → 停机等契约，只渲染加载骨架）。

`ActionView.vue` 模板按此四分；契约未就绪**不渲染 surface、不猜形态、不兜底默认值**，
`ContractGapError` 硬停机语义不变。未放宽 `requireDeclaredNumberList` 断言，未改声明层，
未加前端默认 `[10,20,50]`，未加付款模型特判。

### 9.4 行为锁

新增 `frontend/apps/web/scripts/action_view_surface_gate_runtime_test.ts`（`PASS cases=10`），用生产
`createContractV2Store` 驱动生产判据 + 生产 `resolveActionViewPageSizeOptions`，锁定：契约就绪 →
`surface` 且同刻声明可消费；未就绪 → `contract-pending` 且绝不为 `surface`（负例先证基线正常再注入）；
未就绪却渲染 surface 时那条消费链必抛 `ContractGapError(missing='search.defaults.page_size_options')`；
未就绪+加载失败 → `load-error`；就绪+加载失败 → 仍 `surface`；render-error 优先；四态穷尽可达。
挂入 `verify.frontend.action_view_surface_gate_runtime.unit`（quick / pr / release 三条前端车道）。

契约台账新增 declarationBindings 第 3 条（ActionView surface 展示形态，`onMissing: stop`，
`stopSymbol: contract-pending`）。

### 9.5 迭代效率：把「未映射」缺口按类补齐（机制修正，非本次业务修复）

`make ci.local.iteration` 的增量规划器把本次改动里的契约台账、规划器自身、make 目标定义都判成
「未映射」，等于把最小复用退回人工挑目标。按「发现效率问题立即处理」补齐：

- 台账 `docs/architecture/frontend_contract_basis_ledger.json` 与契约守卫 →
  `verify.frontend.contract_basis.unit` / `.enforce`（此前改台账无人推荐重跑守卫）；
- 规划器自身与 `make/frontend.mk` → `verify.frontend.dev.incremental.unit`；
- 新增锁：**RULES 里推荐的每个目标都必须在 makefile 中有定义**（防目标名漂移把最小复用变成
  make 直接报错）；
- `.agent/` 运行记账不再计入 `unmappedPaths`：续跑时只动 run 记账不该要求「人工挑一个 L2」。

`verify.frontend.dev.incremental.unit` 由 20 例增至 **24 例 OK**；规划器对当前工作区输出
`unmappedPaths=[]`、`manualNonZeroL2Required=false`。

### 9.6 边界与报告

- 4 项既有守卫失败（`frontend_list_contract_rendering_guard`、`frontend_platform_runtime_config_guard`、
  `frontend_contract_query_context_guard`、`navigation_contract_boundary_guard`）**不属本轮**：前两个未接
  任何 make/workflow 入口，另两个只在 minimum_surface / dev_test 车道；断言指向本轮未改的文件
  （`ListPage.vue` 在 HEAD 上本就没有 `.footer-row-label`）。四项均不在
  `public_guard` / `merge_policy_gate` / `professional_quality_gate` / `frontend_release_gate` 路径上。
- 环境 DENY 结论继续单独保留（仅作重建/快照车道阻断），未泛化为「环境全部通过」。
- 四边界（截至 PR #623 合并后）：主线集成完成（PR #623 → `fd783922`，四项必需检查 pass）；列表范围复核完成（89/89、`problems=0`）；批次验收进行中（其后发现 `options_limit` 投影缺口，见第 10 节）；版本发布 / 产品交付未声明。

## 10. relation_entry 选项取数规模的通用投影缺口（PR #623 之后，2026-10-09）

### 10.1 怎么发现的

PR #623 修复 surface 门禁后，在最终 served revision `fd783922` 上复核列表范围：
**89/89、`problems=0`**（此前 80/89 整页失败）。但顶层残留 1 条 pageerror：

```
pageerror: 契约缺少合法声明 relation_entry.options_limit：前端不停机兜底，等待声明层补齐
```

历史三份证据（`514e1b51` / `7a0fb870` / `d2d51935`）均无此错误 —— 它一直存在，只是被先前的整页崩溃掩盖。

### 10.2 根因：不是后端没声明，是前端通用投影丢了声明键

运行态探针（`.runtime/diag/relation_entry_probe.mjs`，取 `project.project` 表单 v2 契约）核实：
后端 **44/44** 处 `relation_entry` 都下发 `options_limit=80` / `options_search_limit=40` / `search_dialog`。

缺口在 P0 前端通用投影：`frontend/apps/web/src/pages/contractForm/relationDescriptor.ts` 的
`relationEntry()` 是白名单投影，把这三个声明键丢掉了；消费点
`relationOptionsLimit(entry)` / `relationOptionsSearchLimit(entry)` 从投影对象上读
`entry.options_limit`，取到 `undefined` → `requireDeclaredNumber` 抛 `ContractGapError`。

即：**声明层完备、消费原语正确，责任落在「投影没有原样透出声明」这一层**。

同时暴露一条更重的记账缺陷：台账 `closedContractDefects` 里 `CD-20261008-FRONTEND-SELECTED-LIMIT`
曾以「关联选项条数来自 relation_entry.options_limit/options_search_limit」声称闭合，但其
`closureEvidence` 根本没包含消费文件，也没有行为锁 —— 这是一次**无证据的闭合声明**。该缺陷已在
`reVerified` 中如实记录并补证。

### 10.3 修复（保持责任层）

- `relationEntry()` 原样透出 `options_limit` / `options_search_limit`（键名沿用声明形状 snake_case），
  不夹取、不补默认值；缺失/非法仍由 `requireDeclaredNumber` 停机。
- 台账新增 declarationBindings 第 4 条：`declaredBy=page_assembler._build_relation_entry_for_field`、
  `consumedBy=relationDescriptor.ts`、`onMissing=stop`、`stopSymbol=requireDeclaredNumber`，
  并修正 `CD-20261008-FRONTEND-SELECTED-LIMIT` 的证据链。bindings 3→4。
- 未放宽断言、未加模型特判、未改后端。

### 10.4 行为锁（基线先绿，再证注入被检出）

新增 `frontend/apps/web/scripts/relation_entry_option_limits_test.ts`，挂入
`verify.frontend.professional_relation_field.unit`：

1. **基线**：声明存在时投影必须带键且 `relationOptionsLimit` 返回声明值本身
   （用非默认值 33/17，防前端常量冒充声明）；同时锁「投影必须携带消费所需键」集合。
2. **负例**：声明缺失 → `ContractGapError`（`defect.missing` 精确、指向 page_assembler）；非法值
   （0 / 负数）→ 同样停机而非夹取；整段 `relation_entry` 缺失 → 停机。
3. **锁自证**：临时移除投影键后基线用例 FAIL（负面控制），证明该锁确实拦得住原始缺陷。

`cases=6`。不扩全局测试框架、不以字符串/常量出现本身当作正确性证明。

### 10.5 本轮验证与边界

- 定向：`verify.frontend.professional_relation_field.unit`（含新锁 6 例）、
  `verify.frontend.contract_basis.unit`（11 例 + guard bindings=4）、
  `verify.frontend.dev.incremental.unit`（24 例）、`typecheck.strict`、
  contractForm 页面规则命中的 `canonical_form_presenter` / `primitive_adapter` /
  `product_page_pattern` / `page_pattern_reference_parity` / `style_system.guard`、
  `verify.frontend.contract_basis.enforce` —— 全 PASS。
- `make ci.local.iteration` PASS：`unmappedPaths=[]`、`unmappedManualL2=false`。
- 环境 DENY 结论继续单独保留，未泛化。
- 四边界：本轮批次修复进行中；主线集成需待本分支 PR 通过四项必需检查后声明，且其后在最终
  served revision 上只做「受影响关系字段」的定向运行态复核（不重跑 89 键矩阵）。

## 11. 迭代效率缺口：复用身份绑定错对象（P4 验收工具）

### 11.1 现象与量化

受管入口 `verify.frontend.business_entry.matrix.incremental` 上做**定向 6 键**请求，范围引擎却判定
`requested=6 / affected=89 / execute=89`，实际重走全量（约 30 分钟）。账本历史进一步显示：同一治理运行态上
连续三次全量重走（15:12 / 16:34 / 17:43，每次 89 键、`planned_affected` 全 89），而这些重走没有一次是
因为声明输入真的变了。用户多轮反馈的「本地/定向复用没生效、反复无用工作」即此。

### 11.2 根因（实证，非推测）

- **不是范围引擎的比较逻辑写错。** 以当前账本重放 `plan`：`affected=0 / reusable=89`。
- 真正的缺陷是**复用身份绑定了错的对象**：`environmentIdentity()` 把 `served_revision`（**部署 commit sha**）
  写进每个 unit 的指纹与账本身份。于是任何一次 mainline 部署都让 89 键全部失效——包括只改后端、文档或
  与本验收面无关的合并。
- **该缺陷与已记录裁决相冲突**：`.agent/decisions/evidence-reuse-identity.yaml`（OPS-DECISION-002）早已写明
  `served_bundle_revision_role: provenance`、`validity_key_excludes: [served_bundle_revision]`，但代码从未执行
  该裁决。这是「记录在案的裁决未被机制执行」——比写错代码更值得记档。
- 次要自失效：`acceptance_status` 是**结果字段**（批次收口时写回 CSV），却属于指纹输入
  `CONSUMED_ROW_FIELDS`，于是「收口」这一动作会让刚收口的行重新失效。

### 11.3 修复（保持责任层，P4）

- 复用身份改为运行态自报的**受管前端产物指纹** `frontend_build_sha256`：由
  `/api/runtime-version` 发布、由受管入口 `daily.runtime.frontend.build` 用
  `scripts/verify/frontend_build_fingerprint.sh` 按 dist 内容计算。部署 commit 只作 provenance。
  产物指纹恰好在「服务端渲染面真的变了」时变化，正是断言依赖的输入。
- **fail-closed 降级**：运行态没有发布产物指纹时回退到部署 revision（等于旧保守行为，绝不跨产物复用），
  并在 units 文档 `provenance.reuse_identity_key=served_revision` 与入口输出中显式可见。
- 探针在声明 `SC_ACCEPTANCE_FRONTEND_BUILD_SHA` 时校验服务端 `frontend_build_sha256` 一致，并把产物身份
  写进 `summary.json`；探针仍独立校验部署 revision 与 database，观测只能发生在声明的部署上。
- `acceptance_status` 移出指纹输入，改记为 provenance（结果不再污染输入）。
- `frontend_dev_incremental.py` 规则补 `test_business_entry_matrix_incremental.py` 与
  `business_entry_matrix_scope_seed.py`：此前入口自身的测试文件落到 typecheck 兜底，`unmappedPaths=1`。

### 11.4 证据（负例先证基线）

离线（受管 adapter + 引擎，不跑浏览器）：

| 输入 | 结果 |
| --- | --- |
| 同产物 + 同部署 revision | `affected=0 / reusable=89` |
| 同产物 + **不同部署 commit**（`0000…`） | `affected=0 / reusable=89`（本次修复目标） |
| 不同产物指纹 | `affected=89`（原防护保留） |
| 旧方案 units 文档（identity 含 `served_revision`） | `affected=89`（fail-closed，不跨身份方案静默复用） |

账本迁移（零执行）：`--record-existing` 把 `20261008T171004Z` 的 89 键观测重折到新指纹。绑定条件已核：
部署 `4ee151ef`、产物 `b0311c6f…`（`frontend-build.json`: `entry_asset=index-Yv56wmel.js`，
服务端 `/index.html` 当前即该产物）、`sc_demo`、CSV 未变；探针改动为 assertion-neutral（只加产物绑定与
summary provenance，未触碰任何 entry 断言）。

活体定向（同一治理运行态）：

```
[business-entry-incremental] reuse identity binds frontend_build_sha256=b0311c6f39e3…4957
[business-entry-incremental] reusable=89 affected=0
[business-entry-incremental] executing 6 entries
[business-entry-matrix] ok=true entries=6 problems=0 console_errors=0
```

- `selection.json`：`execute == requested`（6），`reused=89`，`re_evidenced=6`。
- 无理由请求同一 6 键 → `DENY … already covered with unchanged inputs`，退出码 2，**零执行**（复用优先闸门未放宽）。
- 定向单测：`verify.frontend.business_entry.evidence_scope.unit`（`Ran 27 tests OK` + JS `cases=23`）、
  `verify.frontend.dev.incremental.unit`（`Ran 24 tests OK`）、`verify.guard.registry` PASS、
  `make ci.local.iteration` PASS（`unmappedPaths=[]`、`manualNonZeroL2Required=false`）。

### 11.5 效率结论

- 同产物换部署：89 键 → **0 键**（此前每次部署必然全量）。
- 定向复核：约 30 分钟 → 约 3.5 分钟（6 键）。
- 未变通过的层按规则直接复用，未重跑无关门禁。

### 11.6 边界与残留

- **责任层**：P4（ops 交付工具与验收夹具）；无 P0/P1 产品语义、无后端契约、无前端渲染改动。
- 残留依赖：产物指纹的区分力依赖前端构建可复现性。若构建引入时间戳等非确定内容，表现为「保守地全量重走」
  （安全方向），不构成误复用。
- 环境 DENY 结论继续**单独保留**，仅作重建/快照车道阻断，未泛化为「环境全部通过」。
- 四边界：批次验收（本节）通过；主线集成待本分支 PR 通过四项必需检查后声明；版本发布与产品交付另判。

## 12. 详情车道与关系往返在 served `main bfb38367` 上的收口（2026-10-09）

### 12.1 触发与受管重建

run 第 7 步「回到产品交付主线」的首个执行单：**只收详情，不碰已通过的列表**。先把权威
`main` 精确 SHA 提升到日常运行态（`sc-root:/opt/projects/repos/sce-product-odoo`，`sc_demo`）。

| 受管入口 | 结果 |
| --- | --- |
| `daily.runtime.main.bundle_sync` | PASS `old_sha=4ee151ef…` → `source_sha=bfb38367…`，`normalized_from_candidate=false` |
| `daily.runtime.source_revision.align` | PASS 声明并重启，`/api/runtime-version` 回读 `source_revision=bfb38367…` |
| `daily.runtime.frontend.build` | PASS `rebuilt=true reused=false`；产物指纹 `b0311c6f39e3…4957`、entry `index-Yv56wmel.js`，与 `4ee151ef` **相同**（本轮无前端源码变化） |
| `daily.runtime.record_identity.resolve` | PASS 受管解析出 10 类记录身份（project 2014 / contract 1719 / settlement 3624 / payment_request 36178 / payment_execution 170345 / lifecycle 2022 / companies a=21 b=22 等） |

读回：`source_revision=bfb38367882467e081c9eab2feff6e880a71687e`、
`frontend_build_sha256=b0311c6f39e3de5e5706933217e3fc99d572411c81133d6c8e010b2efd5a4957`、`database=sc_demo`。

### 12.2 详情实际效果（1440 / 390 × 明暗）

入口 `make verify.daily_dev.list_surface.readonly.browser`，`LIST_SURFACE_DAILY_OBSERVATION_SCOPE=detail-only`，
受管 daily 只读档（弱口令确认信封 key 集固定、TTL < 10 分钟，未手拼凭据）。

| 运行 | 产物 | 结果 |
| --- | --- | --- |
| light | `.runtime/final-acceptance/detail-lane-bfb38367/detail-only-light.json` | `passed=true`，`record_checks` 8/8（1440 + 390 各 `declared_entry_route`/`exact_record_contract`/`declared_renderer`/`return_to_source`），`runtime_errors=0`、`denied_requests=0`、`console_errors=0` |
| dark | `.runtime/final-acceptance/detail-lane-bfb38367/detail-only-dark.json` | 同上；声明主题 `resolved=dark` |

`servedIdentity`（探针自证）：`servedSha=bfb38367…`、`servedDatabase=sc_demo`、
`frontendBuildSha256=b0311c6f…4957`。

### 12.3 关系“点击打开 → 返回原记录 → 标签和动作恢复”（一次真实往返）

声明驱动探针 `scripts/verify/record_relation_roundtrip_acceptance.js`：捕获页面自身消费的
`ui.contract.v2`，只对契约声明 `can_read` 的关系控件做**真实点击**，再按前端自身发出的 `return_*`
契约校验回退（不是 handler 诊断）。源记录 `construction.contract.income/2331`（action 578 / menu 904，
契约声明 14 个关系条目）。

- 4 个声明可打开条目全部 `opened`：`project_id` → `/f/project.project/1245`（声明 `696/376`）、
  `partner_id`（`786/598`）、`handler_id`（`723/438`）、`tax_id`（无 action/menu 声明）。
- 往返：`project_id` 回退后 `path/title/statusbar/tabs/actions` 全部恢复，`error_free=true`。
- `denied_requests=0`、`console_errors=0`。
- 原台账记录的「关联跳转返回 403」**不再复现**：`project_id` 现在声明的打开入口 `696/376` 在
  `navigation.route_authority` 内，不再落到 `access-denied`。

### 12.4 边界

- 责任层：P4（运行态验收）；本批次产品代码 0 变更。
- 本执行单只收详情；**创建/编辑与工作台**的最小证据差额是下一执行单，89 键列表矩阵不重跑。
- 产物指纹与 `4ee151ef` 相同，说明本轮（PR #625）无前端源码变化；详情与关系证据按当前 served 身份重新绑定。
- 环境 DENY 结论继续单独保留（见第 11.6 节），本批次未依赖它。
- 观察（本轮未改代码）：纯叙述性 `docs/ops/iterations/*.md` 在 `ci.local.iteration` 中被计为 `unmappedPath`
  （`NON_SOURCE_PATH_PREFIXES` 当前只豁免 `.agent/`），使记录性文档改动也带出 `manualNonZeroL2Required=true`。
  按「只修确认失败」本轮不动规划器，登记为迭代效率候选（与第 9.5 节同类）。

## 13. 创建/编辑与工作台的最小证据差额收口（served `main bfb38367`，2026-10-09）

### 13.1 触发与入口

同一受管入口 `make verify.daily_dev.list_surface.readonly.browser`，`LIST_SURFACE_DAILY_OBSERVATION_SCOPE`
分别取 `form-profiles` / `workbench-only`，明暗各一次，1440/390；复用 12.1 的受管后端与构建产物
（`source_revision=bfb38367…`、`frontend_build_sha256=b0311c6f…4957`、`database=sc_demo`、fixture 未变）。
本轮未重跑 89 键列表矩阵，未重建后端/前端。

### 13.2 创建/编辑面（`form-profiles`）：PASS，但按声明口径记录

`records` 12/12、`runtime_errors=0`、`denied/console/page=0`。实际生效的断言是 `declared_edit_entry`
（编辑页 `/f/project.project/581?menu_id=379&action_id=506`，明暗各观察一次）。

`declared_create_entry / declared_create_contract / declared_create_renderer` 全部为
**`not_applicable`（声明文案："create authority is not declared for this list"）**。也就是说本车道证明的是
「契约声明了什么就观察什么」，**不是**创建/编辑写入能力的证明。该口径与
`daily_dev_user_acceptance_completion_20261006.md` §3.5 一致，沿用不重新解释。

### 13.3 工作台面：首轮 FAIL 的定性与根因（**不是契约缺陷**）

首轮 `workbench-only` 明暗均 `passed=false`，失败信息 `current daily home summary response missing`
（`scripts/verify/frontend_list_surface_structure_browser.mjs:1047`）。失败运行
`console/page/failed/denied = 0`；`my.work.summary` 请求**确实发出且 HTTP 200**（请求参数为
`product_workspace=true, page=1, sort_by=priority, sort_dir=desc, section/source/reason_code=all, search=''`），
只是不满足探针 `dailyHomeSummaryMatches` 里硬编码的 `limit===12 && limit_each===4 && page_size===12`。

责任判定（实证，非推测）：

- **后端**：`my.work.summary` 在 `product_workspace` 为真时**先返回**（`addons/smart_construction_core/handlers/my_work_summary.py:723-752`），
  根本没有读取 `limit/limit_each/page_size`；工作台载荷由 `CurrentWorkItemService`（→ `PaymentRequestWorkItemService`）
  自带规模构建。这三个参数在该路径上是**惰性参数**。
- **实测**：同一账号同一 fixture，带 `12/4/12` 与不带（走默认）两个请求的 `product_workspace` 结果完全一致
  （`todo`=2、`initiated`=0），**无产品行为变化**。
- **前端**：PR #621 移除前端持有的 `12/4/12`，属于已归档决议 `CD-20261008-API-ENVELOPE-DEFAULT-LIMIT`
  （信封缺省由后端声明层承担，`my_work_summary` 在列）的落地，方向正确。
- **探针**：`dailyHomeSummaryMatches` 仍冻结了 PR #621 之前的前端常量，属于 **P4 验收工具的过时断言**。

因此先前「这是契约缺声明」的假设**被证伪**：工作台面既无契约缺失，也无产品行为变化；失败全部归属探针断言。

### 13.4 修复（保持责任层，P4）：把魔法数字换成「声明消费 + 实际行为」

`dailyHomeSummaryMatches` 改为锁定三件事，不再断言任何前端已不再持有的数字：

1. **声明消费**：请求为 `my.work.summary` 且 `product_workspace===true`，并且**不携带**前端自造的产品取数规模
   （`limit`/`limit_each`/`page_size` 任一出现即判否）；排序/分页仍是前端合法持有的 `page=1, sort_by=priority, sort_dir=desc`。
2. **契约结果**：信封 `ok===true`。
3. **实际行为**：`data.product_workspace.sections` 必须是被真正构建出来的非空数组（投影缺失或为空判否）。

负例先行（先证未注入的基线正常，再证注入被检出）：契约锁
`scripts/verify/test_frontend_list_surface_search_contract.py::test_daily_read_boundary_executes_real_predicate`
按真实基线构造 `summary` 先断言 `dailyHomeSummaryMatches(summary)===true`，再逐一注入
`product_workspace=false / limit=12 / limit_each=12 / page_size=12 / page=2 / sort_by=id / ok=false /
sections=[] / 无 product_workspace` 并断言全部被检出为 `false`；重跑 `verify.frontend.list_surface_search_contract.unit` 22 例 OK（未放空断言）。

### 13.5 结果（受影响车道重跑一次）

`workbench-only` 明暗各重跑一次（探针是本轮唯一变化的执行输入），1440/390 全部通过：

- `passed=true`，`console_errors/page_errors/failed_responses/denied_requests = 0`。
- 观察：`declared-theme`（light/dark 各自 `resolved` 正确）、`declared-default-landing`（`/s/projects.list`，
  `projects.list`）、`router-workspace-home` 明暗各 `summaryResponses=1`、`officialCards=3`。
- 产物：`.runtime/final-acceptance/forms-workbench-bfb38367/workbench-only-{light,dark}.json`；
  `form-profiles` 明暗产物为本目录同批 `form-profiles-{light,dark}.json`。

**复用裁定**：`form-profiles` 车道不执行工作台分支（`DAILY && (scope==='all' || WORKBENCH_ONLY)` 之外的 scope 跳过），
其断言不依赖本次改动，按「测试工具改动只失效依赖它的结果」沿用通过证据，未重跑。

### 13.6 迭代效率：把本轮暴露的两处浪费做成机制（P4）

本轮暴露两处系统性浪费，按「发现效率问题立即处理」当场收口在规划器 `scripts/verify/frontend_dev_incremental.py`：

- **探针改动无人路由**：改 `frontend_list_surface_structure_browser.mjs` 落进 `unmappedPaths`，其契约锁
  `verify.frontend.list_surface_search_contract.unit` 只能靠人工 grep 才会被想起来。现补规则把
  探针与其锁测试路由到该非零单测；否则过时断言会一路漂到日常车道才暴露（正是本轮）。
- **纯叙述性文档要求人工 L2**：`docs/**`（本轮为 `docs/ops/iterations/*.md`）无任何映射即要求
  `manualNonZeroL2Required=true`，而按已归档复用决议 `OPS-DECISION-002`，`documentation_only_change`
  **不失效**任何单元。现把 `docs/` 并入 `NON_SOURCE_PATH_PREFIXES`（仅当无映射时豁免；被规则映射的
  `docs/architecture/frontend_contract_basis_ledger.json` 仍照旧路由到契约门）。

证据：改动后 `make ci.local.iteration` 的 `unmappedPathCount` 2 → **0**、`manualNonZeroL2Required` true → **false**，
且 `verify.frontend.list_surface_search_contract.unit` 自动进入推荐目标。行为锁 `verify.frontend.dev.incremental.unit`
新增 3 例（探针路由、叙述文档不触发人工 L2、受管台账仍走契约门）后 27 例 OK。

### 13.7 边界与残留

- 责任层：本轮产品代码 0 变更；改动集中在 P4 验收探针、其契约锁与规划器（均为既有受管工具的扩展）。
- 证伪记录（供后续不再反复）：工作台 `my.work.summary` 的取数规模**不是**未声明缺口，不要在契约层「补」它；
  它在 `product_workspace` 路径上惰性，真实规模由 `CurrentWorkItemService` 决定。
- 环境 DENY 结论继续单独保留（第 11.6 节），本轮未依赖它，也不泛化为「环境全部通过」。
- 未宣称：89 入口全部可用、创建/编辑写入能力已验收（`form-profiles` 为声明口径）、版本发布/产品交付完成。

## 14. 项目台账 `/f/` ↔ `readonly` 观察项收口（served `main bfb38367`，2026-10-09）

### 14.1 这是当前唯一的未决产品策略项

出处 `docs/ops/iterations/daily_dev_user_acceptance_completion_20261006.md` §4.1：列表声明
`model_write_authority=true` 并据此打开 `/f/project.project/<id>`，但记录契约给出 `effectiveRenderProfile=readonly`；
提问「是否为产品策略」。

### 14.2 事实（served bfb38367 / sc_demo / wutao，前端真实 op）

- **列表契约**（`op:action_open`，action 506 / menu 379）：`modelRights={read,write,create,unlink,duplicate:true}`，
  同时 `globalStatus.effectiveRenderProfile="readonly"`、`pageAuth="read"`；`actionRuleList` 只有 2 条规则，
  其中 `page.row` 的 `target` **全部为 null** —— 该列表**不声明**正式 `record_entry`。
- **记录契约**（`op:model`，model=`project.project`，record_id=581，action 506 / menu 379）：
  `effectiveRenderProfile="edit"`、`pageAuth="edit"`、`effectiveRecordCapabilities.write=true`、
  workflow `editability="editable"`、`workflowPhase=draft`（记录 `PRJ260581`）。
- **台账当前可见 20 行**逐行记录契约：`edit=20`、`readonly=0`。
- **served 车道产物**（`.runtime/final-acceptance/detail-lane-bfb38367/detail-only-{light,dark}.json`）：
  `/f/project.project/581` 记为 `edit-form-observation-without-save`，记录检查 8/8 通过，
  `denied_requests=0`、`console_errors=0`。

### 14.3 定性：不是契约自相矛盾，是「模型级写权限」与「记录/状态级有效可编辑性」两个不同权威

- **入口路由**（`/f/` vs `/r/`）的唯一来源是后端声明的 `statusContract.globalStatus.modelRights.write`
  （`recordEntryFromModelRights`）。该列表未声明正式 `record_entry`，因此走这条**已声明的通用机制**；
  非布尔值一律 fail-closed 到 `/r/`（`frontend/apps/web/src/app/runtime/recordEntryContract.ts` 头注释）。
- **记录面 profile** 由 P0 `addons/smart_core/utils/contract_governance_form_render.py::resolve_render_profile`
  （由 ORM 生效权限计算）产生，并由 P1 工作流**收窄**：`addons/smart_construction_core/core_extension.py`
  （`editability in {readonly,locked}` → `pageAuth=read` + `effectiveRenderProfile=readonly`）经
  `models/support/workflow_contract_service.py::_editability`。
- 两个权威职责不同：`modelRights` = 模型级能力（决定入口路由）；`effectiveRenderProfile` = 该记录**当前**有效可编辑性。
  当记录被状态/审批锁住时，`/f/`（可写入口）+ `readonly`（该记录当前不可写）是设计内的 fail-closed 收窄，**不是矛盾**；
  且 `506/379` 在 `route_authority` 内，不产生 403。
- **既有锁已把该配对判为合法**：`scripts/verify/test_frontend_list_surface_search_contract.py` 断言
  `/f/<model>/<id>` 可声明 `edit` **或** `readonly`，只对 `/r/` + 非 readonly 抛错；P1 收窄由
  `addons/smart_construction_core/tests/test_workflow_contract_backend.py`、`test_core_extension_v2_finalize.py` 锁定。

因此：**不放宽任何断言、不改产品代码、不加任何模型特判**；探针把 readonly 记录记 `not_applicable` 的口径本身正确
（绝不当作编辑通过）。也不以 `critical` 覆盖 ACL / 字段权限 / 合法隐藏规则。

### 14.4 观察项在 served 身份上已不可复现，其来源期已被「项目台账入口统一」取代

- 原始 readonly 观测出现在旧基线 `5ba6398e`（产物 `detail-closeout-5ba6398e/light.json`：581 surface=`readonly-detail`）。
- 其后合入的 **PR #594**（`90484d88`，`PROJECT-LEDGER-ENTRY-UNIFICATION`，即所有者批准的
  「项目台账 × 项目信息编辑 统一为唯一入口」）退役了遗留表单视图 `view_sc_product_project_information_edit_form_v1`，
  把台账统一到 `view_project_overview_form`，并新增运行契约锁 `addons/smart_construction_core/tests/test_project_ledger_runtime_contract.py`。
- served `bfb38367` 上同一记录同一入口解析为 `edit`，台账 20 行全 `edit`。
- 说明：历史基线在可变 `sc_demo` 上的**精确**触发条件（记录当时的状态/审批锁，或遗留入口面的权限投影）不再重新取证；
  两种成因都是合法收窄，均非契约自相矛盾。收口以当前 served 身份的事实为准。

### 14.5 证据与边界

- 机制锁（本轮引用重跑）：`make verify.frontend.collection_view_semantics.unit` → `record_entry_contract_test: ok`、
  18 + 36 tests OK、guard PASS（含 `modelRights:{write:'true'}` 字符串 fail-closed → `/r/`）。
- diag 证据：`.runtime/final-acceptance/ledger-readonly-closure-bfb38367/{list_and_record_contract.json,list_status_profile.json,ledger_rows_profiles.json}`。
- 边界：本轮产品代码 0 变更；未触碰 ACL / 字段权限 / 合法隐藏规则；环境 DENY 结论继续单独保留（§11.6）。

## 15. 批次合并：PR #626 进入 `main`（2026-10-09）

- 候选分支 `fix/user-acceptance-detail-closure-20261009`，评审头 `84376430a5a88149c4e4057049b6c60d4e256530`
  （`chore(generated)` 复杂度证据刷新，工作区干净）。
- 精确头 `84376430` 上四项必需检查全部 `success`：`merge_policy_gate`、`professional_quality_gate`、
  `public_guard`、`frontend_release_gate`；其余 `release_candidate_gate`、`python310_runtime_compatibility`、
  `professional_authorization`、`public_guard_classify`、`classify` 亦 success；`fast`、`wait_for_candidate_checks`、
  一项 `classify` 为可信风险分类的显式 skip（可接受）。
- `make pr.merge PR=626 EXPECTED_HEAD=84376430…` 走平台受保护 PR 合并；`pr.merge.local_quick_gate`
  **REUSE** 精确头 `ci.local.quick` receipt（未重跑套件）。合并方式 `--squash`：
  合并提交 `b28d449948f77b2f7f0d72bc7ef913b323d51e0d`（`Merge PR #626`，单亲 `bfb383678824…`），
  与 `#614–#625` 的既有惯例一致。
- 回读：PR #626 `state=MERGED`、`mergedAt=2026-10-08T21:45:42Z`、`mergeCommit=b28d4499…`；
  `origin/main=b28d4499…`；`84376430^{tree} == b28d4499^{tree}`（`a9d32af1…`，squash 承载完整内容）。
- **边界**：合并不触发产品部署。日常运行态仍服务 `main bfb38367` / 产物 `b0311c6f…` / `sc_demo`；
  本批次**不主张**版本发布完成或产品交付完成。环境 DENY 结论继续单独保留（§11.6），本批次不依赖它、也不泛化。

## 16. 终局退役（2026-10-09）

- 本批次的目录、detail/relation 往返、创建-编辑与工作台最小证据差额均已随 **PR #626** 并入 main
  （合并提交 `b28d4499…`，§15），主线批次边界已闭合。所有者确认后把本 run 翻终态。
- 改动：`FE-HIERARCHICAL-WORKSHEET-USABLE-READY` goal `in_progress → completed`；对应 run
  `active → completed` 并重写 `next_exact_step`；`.agent/active-runs.json` 移除
  `fix/user-acceptance-detail-closure-20261009` 绑定（`branches` 变为空集），main 上不再有索引项指向
  已合并的该分支。批次记录新增本节。
- 台账守卫同步：`RECORDED_NON_CANONICAL` 棘轮由 3 降到 2（移除本 goal 的 `in_progress` 记录态），
  单测合成夹具改为镜像新现实；守卫要求「棘轮集合与磁盘逐字相等」，故退役与棘轮必须同一次改动完成。
- 边界：`ENV-ACCEPTANCE-REBUILD-LANE-PREREQUISITE` 独立专题已解除环境 DENY，本退役**不依赖**它、也不泛化
  为「环境全部通过」。合并不触发产品部署。批次验收=完成；主线集成=完成（该批次 `b28d4499`）；
  版本发布=未主张；产品交付=未主张。89 键矩阵不重跑。
- 车道：`.agent`/`docs` 记账候选默认被 `pr.merge.local_quick_gate` 判为 bookkeeping-only；本专题为**真实
  终局退役**且无相邻产品候选，故按该门显式指引用 `PR_MERGE_BOOKKEEPING_TERMINAL_RETIRE=<reason>`
  走一次终局退役，全批只跑一次精确头 Quick。
