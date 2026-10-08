# 日常开发服务器刷新到当前主线并重收用户级验收（2026-10-08）

## 1. 目的与边界

把日常开发运行态从 `24e05cd5` 刷新到当前主线 `7a0fb870`，并用复用优先的受管验收重新收口用户视角。
本批不改产品代码；验收 harness 的证据定位缺陷按 P4 层修复。如验收暴露产品缺口，按所属层单独登记处理。

## 2. 基线与身份

- 基线 `origin/main` = `7a0fb87006dfbd0381c4a06705a300242ef52311`。
- 刷新前日常运行态 `source_revision` = `24e05cd54685645498843bf29b222fed3f595d9e`（数据库 `sc_demo`，环境 dev）。
- 运行车道：`daily.runtime.main.bundle_sync` / `daily.runtime.source_revision.align` / `daily.runtime.record_identity.resolve`。
- 用户级验收身份：导航 `wutao`，契约/夹具账号 `fixture_role_finance`（uid210，role `finance`，公司 `FE Company A`=21），矩阵主体验收角色 `fixture_role_config_admin`。

## 3. 执行与结果

### 3.1 运行态刷新（三入口，均 PASS，无提交）

| 入口 | 结果 | 关键回执 |
| --- | --- | --- |
| `daily.runtime.main.bundle_sync` | PASS | old `24e05cd5` → source `7a0fb870`；`bundle_sha256=8f5757d0…787b`；upstream `origin/main` |
| `daily.runtime.source_revision.align` | PASS | previous `24e05cd5` → `7a0fb870`；`restarted=true`；回读 `source_revision=7a0fb870`、`database=sc_demo`、`environment=dev` |
| `daily.runtime.record_identity.resolve` | PASS | `served_revision=7a0fb870`、`served_database=sc_demo`、company a=21/b=22；10 项 target 唯一解析；写入 `artifacts/backend/acceptance_record_identity.json` |

回执日志：`.runtime/agent-runs/DAILY-DEV-MAINLINE-ACCEPTANCE-REFRESH/{bundle_sync,source_revision_align,record_identity_resolve}.log`。

**模块升级判定**：`24e05cd5..7a0fb870` 的 `addons/` 改动共 14 个文件，全部为 handlers / services / `models/support/` / tests，`views/`、`data/`、`security/` 变更数为 0，无字段定义变更。故**不执行模块升级**，运行态重启（已由 `source_revision.align` 完成）足以承载。

### 3.2 只读用户级探针（PASS）

`make verify.daily_dev.acceptance.readonly.probe`（`ACCEPTANCE_TARGET_SHA=7a0fb870`，`DB_NAME=sc_demo`，base `http://1.95.85.92:18081`）：

- `runtime_identity`：served `7a0fb870`、database `sc_demo` → PASS。
- `login`：`nav_action_count=89`、`nav_leaf_count=89`、违禁标签命中 0、必需路径缺失 0、必需动作错配 0 → PASS。
- `contract`：11/11 检查 PASS（identity_deployed_sha / actor_uid / role_code / company / resolution_unique_target / request_target_binding / integrity / schema_digest / formal_schema / custody），`errors=[]`。
- `[dev_acceptance_release_probe_schema_guard] PASS`。
- 回执：`.runtime/agent-runs/…/readonly_probe.log`、`artifacts/backend/daily_dev_acceptance_probe.json`（含 `.contract.json` 托管响应）。

口令 fail-closed 按设计生效：日常 profile 拒绝已知弱口令，必须提供 ≤10 分钟的 `SC_ACCEPTANCE_DAILY_CREDENTIAL_CONFIRMATION` 信封且各字段与 CLI/env 完全一致；本批以固定开发口令 + 信封通过，未放宽该守卫。

### 3.3 负例闭包复核（无漂移）

`make verify.frontend.business_entry.negative_closures`：10 个 denied-role 候选、2 个 ineligible。
与刷新前快照逐候选比对：`closure_size` / `role_xmlids` / `nav_targets` / `company` / `error` **全部一致**，仅记账字段 `adopted_from` 由「采纳的临时观测」变为实采空值。即本次能力/菜单投影改动未改动已声明的否定闭包。

### 3.4 业务入口矩阵（复用优先 + 定向复验）

- 增量规划：`declared=89 units / reusable=89 / affected=0` → 无新增受影响键，按复用优先不重跑。声明输入 `business_entry_matrix_model.mjs`、`released_navigation_target.mjs`、`business_entry_matrix_browser.mjs`、矩阵 CSV、overlay 在 `24e05cd5..7a0fb870` **均无变化**。
- 复核发现 4 个单元的证据指针失效（见 3.5）：`menu_sc_p1_daily_contract`、`menu_sc_product_project_lifecycle_v1`、`menu_sc_project_initiation`、`menu_sc_project_project`。
- 定向复验上述 4 键（附 `SC_ENTRY_SCOPE_REVERIFY_REASON`）：`ok=true`、`entries=4`、`problems=0`、`console_errors=0`。
- 覆盖状态（`make verify.frontend.business_entry.matrix.evidence_scope.status`）：`units=89`、`checked=9` + `passed=80`；stale / uncovered / failed / blocked / never_recorded 均为 0。（该次记账所用映射有缺陷，**已在 3.7 修正并重折为 87 `checked` + 2 `exception`**。）

### 3.5 证据定位缺陷（P4 根因修复，属可达成性缺陷）

- **根因**：增量入口 `scripts/verify/business_entry_matrix_incremental.py` 的默认产物目录是固定路径 `artifacts/frontend-business-entry-matrix/incremental`，而台账（`evidence_scope` ledger）把每个单元的 `source` 记录为它折叠所用的 `summary.json`。后续任何更窄的增量运行都会覆盖同一 `summary.json`，使先前单元的 `source` 不再包含自身条目 —— 证据不可溯源，且**定向复验会反过来损坏另一个单元的证据**。
- **实证**：该 `summary.json` 于 `2026-10-07T22:12` 被只含 `menu_sc_user_payment_apply` 的运行覆盖，导致 4 个单元（3.4 所列）的 `source` 失效。
- **修复（最小、通用，无模型/角色特判）**：默认目录改为**按运行唯一**（`<UTC 时间戳>-<执行键集摘要>`）；显式 `SC_ACCEPTANCE_OUTPUT_DIR` 行为不变（仍原样使用）；`resolve_output_dir` 改为在已知执行键集之后再解析，使目录名由产生它的输入派生。
- **锁定**：`scripts/verify/test_business_entry_matrix_incremental.py` 增加「默认值不等同共享目录 / 不同运行与不同键集解析到不同目录 / 早先运行的 `summary.json` 不被覆盖」断言；`make verify.frontend.business_entry.evidence_scope.unit` → **Ran 34 tests OK**（该套件在 3.7 扩至 46 项）。
- **复核**：台账中 9 个引用文件的单元 **0 溯源问题**，4 个复验单元 `source` 现指向 `artifacts/frontend-business-entry-matrix/incremental/20261008T100715Z-f0c688786dcb/summary.json`。

### 3.6 前端产物代际对齐（P4 受管入口，无提交）

- **发现的盲点**：日常运行态通过 nginx bind mount 提供**预构建**静态前端（`FRONTEND_DIST_DIR`），而受管代码同步 `daily.runtime.main.bundle_sync` 只快进 git 树，不重建产物。因此主线合并若改了前端源码，`/api/runtime-version` 会报新 commit，但**实际服务的 bundle 仍落后一代**，用户级验收会静默跑在旧渲染面上；只读探针的契约/导航断言看不到这一点。
- **实证**：刷新前服务入口为 `index-DPFnm5JE.js`，与部署 HEAD 不一致；`/api/runtime-version` 未声明 `FRONTEND_BUILD_SHA256`。
- **修复（复用既有受管件，不新增环境）**：新增受管入口 `make daily.runtime.frontend.build`（确认串 `CONFIRM_DAILY_RUNTIME_FRONTEND_BUILD=BUILD_AND_DECLARE_DAILY_RUNTIME_FRONTEND_AT_DEPLOYED_HEAD`，脚本 `scripts/ops/daily_runtime_frontend_build_align.py`）。流程：要求远端树处于精确 commit 且干净 → 复用已声明代际 → 否则调用既有 `make verify.frontend.build` 构建 → 用既有 `scripts/verify/frontend_build_fingerprint.sh` 计算产物指纹并声明为 `FRONTEND_BUILD_SHA256` → `make restart` → 回读 `/api/runtime-version` 与 `/index.html`，证明服务入口即刚构建的产物；回读不成立则恢复原 env 与运行态。仅触碰前端产物目录、单条声明 env 行与受管运行态；不改写代码树、数据库、卷、凭据或 nginx 配置。
- **结果**：产物 `index-DPFnm5JE.js` → `index-QSyK4l8b.js`；指纹 `f21ffd64b849962b9e47fbb1f76d258c097e464d2310892540e3f60a62a806a2` 已由 `/api/runtime-version` 声明并回读一致。单测 `make verify.daily.runtime.frontend.build` → **Ran 15 tests OK**。回执 `.runtime/agent-runs/…/frontend_build.log`。
- 代际对齐后重跑只读探针（`readonly_probe_frontend_refresh.log`）与负例闭包（`negative_closures_frontend_refresh.log`）均 PASS：探针 `nav_action_count=89`、contract 11/11、`errors=[]`。

### 3.7 台账记录映射缺陷（P4 根因修复）

- **现象**：一次覆盖 89 个声明单元的矩阵观测已正确采集，但台账把 87 条正确证据连带判废，并迫使对未回归的单元重走表面。
- **根因**：`scripts/verify/business_entry_matrix_scope.mjs` 的 `--emit-results` 在 `summary.ok !== true` 时，把**面级**结论折叠进**每个**已执行单元（追加 `<status>=failed` 后缀）。探针的 `summary.ok` 是覆盖整个进程退出码的聚合**面级**结论，绝不能重写同级单元各自的结论；只有未被 per-entry 记录覆盖的选中键才应记 `failed`。
- **修复（最小、通用）**：逐单元状态只取自 `summary.entries[]`；未被 entries 覆盖的选中键记 `failed`；新增 `surface_ok` / `surface_fatal` 面级字段，面级结论与单元结论分离。
- **恢复映射而不重采（复用优先）**：新增受管重折能力 `--record-existing / --record-existing-reason / --plan`（引擎 `record --source`）。它在 `select` 之前执行，绑定**原始**运行的 plan 与 `summary.json`，**不执行任何探针**；fail-closed 校验 schema / `target_sha` / `served_revision` / `database` / selection keys / plan 存在，缺 reason 或 plan 一律拒绝；重折结果仍含非成功项时非零退出，绝不能被误认为一次新的通过走查。
- **实测重折**（`ledger_refold_mapping_fix.log`）：原 89 条 → **87 `checked` + 2 `exception`**；来源标注 `#record_only`。台账 `runs` 增至 8；重折前快照 `ledger_before_refold.json`。
- **锁定**：`make verify.frontend.business_entry.evidence_scope.unit` → **Ran 46 tests OK**（在 3.5 的 34 项之上新增 mapping / record-only / `--source` 断言）。

## 4. 状态边界（分开报告）

- **批次验收**：本批（运行态刷新 + 前端产物代际对齐 + 用户级验收复收 + harness 证据定位修复 + 台账记录映射修复）通过；89 项矩阵剩余 2 项 `exception` 已定性为**真实产品缺陷**（见 5），不属本 P4 批次。
- **主线集成**：本批 harness 改动仍需按受管流程进入 PR 与远端 CI 后判定，本记录不主张已集成。
- **版本发布 / 产品交付**：均未主张。

## 5. 剩余与未覆盖

- 未重跑全量 89 单元浏览器矩阵：规划判定 0 受影响且声明输入文件未变，按复用优先不重复取证；能力/菜单投影改动的影响由只读探针（导航 89 条、0 违禁、0 必需缺失）与负例闭包（与原快照语义一致）覆盖，并以 `OPS-DECISION-002`（served revision 仅作溯源）为身份口径。
- 本机 `sc_dev_demo` 上 `verify.workflow_contract.backend` 既有 9 红为 demo 数据漂移，不在必需 CI 车道，亦非本批引入，本批不处理。

- **保留的真实产品缺陷（P1，非本批引入，独立于本 P4 批次登记）**：矩阵剩余 2 个 `exception` 是**真实产品缺陷**，既非抖动也非探针口径问题：
  - 键：`smart_construction_core.menu_sc_p1_expense_contract`（`/a/579?menu_id=905`）、`smart_construction_core.menu_sc_payment_execution`（`/a/806?menu_id=347`）。
  - 定向复验稳定复现 30s `networkidle` 超时（`matrix_reverify_2keys.log`）。
  - 根因链（已实证）：两页均由 `HierarchicalWorksheet`（工作表 / `presentation=hierarchical`）渲染；前端 `frontend/apps/web/src/app/action_runtime/hierarchicalWorksheetDataSource.ts` 的 `loadAll` 硬编码 `limit=5000`，把整表分页全部拉进浏览器。数据规模：`construction.contract.expense` = 8,513 行，`sc.payment.execution` = 38,568 行；后者需 8 批 × ~1.5MB ≈ 12MB、约 19s 才全量，叠加 expense 页约 41s，均超 30s。声明态实测由 `loading` 到 `ready` 约 41s，即**产品面本身慢**；`/api/v1/intent` 持续分批请求使 `networkidle` 永不达成 → `page.goto` 超时。
  - 契约缺口：契约仅声明 `dataMeta.limit=20`，**未声明工作表 `page_size`**；前端 5000 为硬编码 fallback。
  - 非本次候选窗口引入：`24e05cd5..7a0fb870` 前端 delta 仅能力/菜单投影（`c5a19c15`），未触工作表数据源；属数据规模驱动的既有产品问题。
  - 最小契约驱动修法（**待授权，独立于本 P4 批次**）：契约声明工作表分页/窗口（如 `dataMeta.context.hierarchical_worksheet.page_size`），前端 `loadAll` 消费声明而非硬编码 5000；不特判付款模型，也不放宽验收断言。
