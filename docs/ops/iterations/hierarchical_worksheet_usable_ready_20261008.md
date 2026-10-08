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
