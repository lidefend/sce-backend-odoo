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

批次验收：进行中（本地 L1/L2 定向通过，待运行时重走）。
主线集成 / 版本发布 / 产品交付：未声明完成。
