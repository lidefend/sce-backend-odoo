# Daily Dev Mainline Product Acceptance Closeout（最新主线产品验收收口，2026-10-09）

Run: `.agent/runs/DAILY-DEV-MAINLINE-PRODUCT-ACCEPTANCE-CLOSEOUT/run.json`
Branch: `audit/daily-dev-mainline-product-acceptance-closeout-20261009`
Baseline: `aea2c19bbe4edb2a13fbf908255e918e18f3a299`（`main`，PR #630 退役后）

## 1. 目标与责任层

- **Formal Product Layer**：P4（ops delivery / 运行态验收收口）。
- **Layer Target**：日常开发运行态（`sc-root:/opt/projects/repos/sce-product-odoo`，`ENV=dev`，
  `DB_NAME=sc_demo`，入口 `http://1.95.85.92:18081/`）主线身份对齐 + 用户视角验收边界收口。
- **Standard vs User-Specific**：运维交付与验收，无行业/客户语义。
- **Why Here**：验收入口必须服务最新主线，属交付验收层。
- **Why Not Elsewhere**：不改 P0-P3 产品语义，不放宽 ACL/字段权限/断言，不新增环境/凭据。
- **Blast Radius**：日常运行仓的 git 树与 served 身份；`sc_demo` 只读验收面。

## 2. 复用裁定（为什么不是重跑矩阵）

- `git diff --stat bfb38367 aea2c19b -- addons/ frontend/` **为空**：最新主线相对已验收态
  （served `bfb38367`，`bfb38367` 是 `aea2c19b` 的祖先）**产品代码零变化**。
- 该区间唯一的验收工具变化是 PR #626（`b28d4499`）对 `dailyHomeSummaryMatches` 的收紧断言
  与路由规则；其受影响断言已在 `docs/ops/iterations/hierarchical_worksheet_usable_ready_20261008.md`
  §13 重跑并通过（served `bfb38367`：`router-workspace-home` 明暗各 `summaryResponses=1`、`officialCards=3`）。
- 既有验收的唯一未决产品策略项（`项目台账` `/f/` ↔ `readonly`）已于 2026-10-09 由同记录 §14 收口。
- 前端产物只依赖前端源（未变）→ 已验收产物 `b0311c6f` 仍为当前产物。
- 结论：**不重跑验收矩阵**（`.agent/decisions/evidence-reuse-identity.yaml` OPS-DECISION-002）。

## 3. 执行与结果

### 3.1 运行态身份对齐（三受管入口，均 PASS）

| 入口 | 结果 | 关键回执 |
| --- | --- | --- |
| `daily.runtime.main.bundle_sync` | PASS | old `bfb38367` → source `aea2c19b`；`bundle_sha256=6be422eb…b073`；upstream `origin/main` |
| `daily.runtime.source_revision.align` | PASS | previous `bfb38367` → `aea2c19b`；`env_written=true`、`restarted=true`；回读 `source_revision=aea2c19b`、`database=sc_demo`、`environment=dev` |
| `daily.runtime.frontend.build` | PASS | `rebuilt=true`、`reused=false`；产物指纹仍为 `b0311c6f39e3…4957`、入口 `index-Yv56wmel.js` 一致 → 产品前端面未变 |

回执：`.runtime/final-acceptance/daily-deployed/{bundle-sync,source-revision-align,frontend-build}.json`。

**模块升级判定**：`bfb38367..aea2c19b` 的 `addons/`、`frontend/` 改动数为 0（`git diff --stat` 为空），
无模型/字段/视图/数据/安全变更 → **不执行模块升级**。

### 3.2 记录身份重解析（PASS）

`make daily.runtime.record_identity.resolve DAILY_RUNTIME_EXPECTED_SHA=aea2c19b…`
（`CONFIRM_DAILY_RUNTIME_RECORD_IDENTITY=RESOLVE_DAILY_SC_DEMO_RECORD_IDENTITY`）：

- `served_revision=aea2c19b`、`served_database=sc_demo`、`remote_head=aea2c19b`、`ssh_host=sc-root`。
- company a=`21` / b=`22`；10 项 target（project / contract / general_contract_carrier / settlement /
  payment_request / payment_request_company_b / payment_execution / journey_request / work_settlement /
  lifecycle_project）**唯一解析**。
- 写入 `artifacts/backend/acceptance_record_identity.json`（`expected_sha=aea2c19b…`，将旧 `bfb38367`
  信封替换为服务态身份）。回执：`.runtime/final-acceptance/daily-deployed/record-identity-resolve.json`。

### 3.3 只读用户级探针（PASS）

`make verify.daily_dev.acceptance.readonly.probe`（`ACCEPTANCE_TARGET_SHA=aea2c19b…`，
`DB_NAME=sc_demo`，base `http://1.95.85.92:18081`）：

- `runtime_identity`：served `aea2c19b`、database `sc_demo`、frontend `b0311c6f…4957` → PASS。
- `frontend`：根 200、`assets/index-Yv56wmel.js` 200、intent OPTIONS 204 → PASS。
- `login`（`wutao`，uid16）：`nav_action_count=89`、`nav_leaf_count=89`、违禁标签命中 0、
  必需路径缺失 0、必需动作错配 0、`auth_name=吴涛`、`role_code=business_config_admin`、`system_init_ok=true` → PASS。
- `contract`：11/11 检查 PASS（`identity_deployed_sha` / `identity_actor_uid` / `identity_role_code` /
  `identity_company` / `resolution_unique_target` / `request_target_binding` /
  `contract_integrity_self_consistent` / `contract_schema_digest_bound` / `contract_formal_schema_valid` /
  `contract_custody_captured` / `contract_custody_bytes_persisted`），`errors=[]`；
  声明账号 `fixture_role_finance`（uid210，role `finance`，`FE Company A`=21），
  `approved_semantic_sha256 = 40db30a8…223b`。
- `[dev_acceptance_release_probe_schema_guard] PASS`。
- 回执：`artifacts/agent-runs/DAILY-DEV-MAINLINE-PRODUCT-ACCEPTANCE-CLOSEOUT/readonly_probe.log`、
  同目录 `readonly_probe.receipt.json`、`artifacts/backend/daily_dev_acceptance_probe.json`（含 `.contract.json` 托管响应）。

口令 fail-closed 按设计生效：日常 profile 拒绝已知弱口令，必须提供 ≤10 分钟的
`SC_ACCEPTANCE_DAILY_CREDENTIAL_CONFIRMATION` 信封且各字段与 CLI/env 完全一致；本批以固定开发口令 + 信封通过，
未放宽该守卫。

### 3.4 运行态口令事实（记录，非断言放宽）

- 日常运行时 `fixture_role_finance` 的实际口令为 **`123456`**（HTTP 直证实测 uid=210），
  已**不是**仓库默认 `SC_ACCEPTANCE_FIXTURE_PASSWORD=scdevpass`；契约段首次直跑因
 默认口令得到 `contract_probe_auth_failed`。
- 处置：以受管机制显式提供运行时事实口令 `SC_ACCEPTANCE_FIXTURE_PASSWORD=123456`（契约账号凭据），
  11 项检查照常全跑，**未跳过/未放宽任何检查**。
- 与 2026-10-08 同型批次（`daily_dev_mainline_acceptance_refresh_20261008.md` §3.2「固定开发口令 + 信封」）一致。
- 归属：`scdevpass` 仅服务于隔离本地 `sc_frontend_acceptance` fixture；日常 `sc_demo` 采用所有者
  固定简单口令 `123456`。两者口径不同属体系内差异，不作为缺陷处置，在此显式记录以免反复。

### 3.5 状态边界（分开报告）

- **批次验收**：通过（本运行态对齐 + 只读用户级探针）。
- **主线集成**：本轮为运行态对齐与验收，无产品代码候选，不主张集成状态。
- **版本发布**：未主张（日常 dev 运行态，非正式版本发布）。
- **产品交付**：技术证据已就绪，**待所有者登录核对**后判定（`http://1.95.85.92:18081/`，`wutao/123456`，库 `sc_demo`）。

## 4. 未处置/保留

- 不重跑 89/108 键验收矩阵（输入未变，属禁止的冗余复验；依据 OPS-DECISION-002）。
- 未放宽 ACL/字段权限/断言/负例/必需检查；未新增环境、数据库、端口、卷或凭据授权。
- 未改动任何产品代码、契约或运行时业务语义。

## 5. 缺陷闭环：登录回跳授权门禁（P0 前端渲染机制）

### 5.1 现象与根因

- 所有者报障：登录后落到「当前角色无权访问此业务入口。请返回已授权的工作区。」
  （`frontend/apps/web/src/views/AccessDeniedView.vue`）。
- 根因：会话过期恢复（`sessionExpiredRecovery.ts`）与 401 重定向会回放用户会话结束前打开的路径，
  但 `normalizeSafeLoginReturnPath` **只校验路径形状**（编码、非登录入口、已绑定的 action 路由），
  **不校验授权**。已退役入口 `/a/1176?menu_id=969&action_id=1176` 形状合法被原样回放，
  router 守卫按当前发布的 `route_authority` 判定为未授权 → `NAVIGATION_AUTHORITY_DENIED` → 落到 access-denied。
- 守卫拒绝本身**正确**：`1176`/`969` 不在 `wutao` 的 `route_authority`（不在任何 bucket，也不在导航叶子中），
  属已退役入口（产品台账已统一为「项目台账」）。缺陷在**应用自己提议了一个契约未授权的回跳目标**。
- 真实证据（远端 nginx 访问日志，非合成）：
  - `00:29:57` 用户（Windows/Edge，`171.214.216.251`）打开 `/a/1176?...&menu_id=969&action_id=1176`，
    其上 `POST /api/v1/intent` 返回 **401**（会话过期）。
  - → `/login?reason=session_expired&db=sc_demo` → 重新认证 → `00:30:08` 落到
    `/access-denied?from=/a/1176...&reason=NAVIGATION_AUTHORITY_DENIED`。
- 干净会话对照：`/a/1176`（带/不带 `menu_id=969`）对 `wutao` 均判 denied；直接登录（无 redirect）
  正常落地 `/s/projects.list`（无 denied）。

### 5.2 责任层与修复边界

- 归属：**P0 平台内核产品**，layer target = `frontend/apps/web` 登录后重定向门禁
  （通用 `route_authority` 消费），**不是 P1 行业语义，也不是 P4 运行态**。
- 修复（`frontend/apps/web/src/app/routeAuthority.ts`、`frontend/apps/web/src/views/LoginView.vue`）：
  新增 `authorityBoundTargetResolvable(contract, target, scope)`——`/a/`、`/f/` 且带 action/menu 绑定的
  回跳目标必须能在**当前发布的** `route_authority` 中解析，否则不作为回跳；`/s/`、`/`、无绑定 `/f/`、
  `/r/` 恒为可解析（`/r/` 保留守卫的关系读意图路径）。未解析时回落
  `isPlatformAdminEntryRuntime() ? '/?platform_admin=1' : session.resolveLandingPath('/')`。
- 未越界：不放宽 router 守卫（纵深防御保留），不改后端契约/模型/字段/权限语义，
  不加付款或任何模型特判，不新增环境/数据库/端口/卷/凭据授权。
- 单元证据：`make verify.nav.pro01r.route_authority.unit` → PASS，`[login_return_authority] PASS cases=13`
  （基线正例 + 未知 action / 退役入口 / 菜单绑定不匹配 / 缺 context 负例）；`vue-tsc` typecheck PASS。

### 5.3 提交与部署

- 提交：`3d90df05` `fix(frontend): drop authority-bound login-return targets the current contract denies`
  （独立提交边界；台账随本记录另提）。
- 部署（受管候选车队，`timeout` 内一次完成，无手工 compose/卷/端口）：
  1. `make daily.runtime.candidate.bundle_sync`（`CONFIRM_...=SYNC_EXACT_DAILY_CANDIDATE_SHA_WITH_BUNDLE`）
     → PASS，remote 检出 `3d90df05`（detached），`origin_main_mutated=false`。
  2. `make daily.runtime.source_revision.align`（`...=ALIGN_DAILY_RUNTIME_SOURCE_REVISION_WITH_DEPLOYED_HEAD`）
     → PASS，`served.source_revision=3d90df05`。
  3. `make daily.runtime.frontend.build`（`...=BUILD_AND_DECLARE_DAILY_RUNTIME_FRONTEND_AT_DEPLOYED_HEAD`）
     → PASS，重建并声明服务产物：`frontend_build_sha256=8bd99a72…f266`，`entry_asset=index-BCF7hFFL.js`。
- 部署后身份（`GET /api/runtime-version`）：`source_revision=3d90df05…a793`、
  `git_sha=3d90df05…a793`、`frontend_build_sha256=8bd99a72…f266`、`database=sc_demo`、`environment=dev`。

### 5.4 修复后浏览器复核（真实 401 驱动，非 handler 诊断）

受控注入 `POST /api/v1/intent → 401`（等价于服务端会话过期），驱动**应用自身**的
`redirectForExpiredSession` 写入回跳路径，再真实重登录：

| 用例 | 记录的回跳路径 | 重登录后落点 | 结论 |
| --- | --- | --- | --- |
| 负例（退役入口） | `/a/1176?product_domain=…&menu_id=969&action_id=1176` | `/s/projects.list` | 不再落 access-denied ✅ |
| 正例（授权入口） | `/s/projects.list?menu_id=379&action_id=506&scene_key=projects.list` | `/s/projects.list` | 合法回跳保留 ✅ |

两侧 `pageerror` 均为空；负例在修复前正是落 `/access-denied?...reason=NAVIGATION_AUTHORITY_DENIED`
（同 §5.1 真实日志与首次 cookie 清空对照观察）。

### 5.5 用户视角矩阵复取

前端产物指纹由 `b0311c6f…4957` 变为 `8bd99a72…f266`，属**合法**证据失效：
`make verify.frontend.business_entry.matrix.evidence_scope.status`（带
`SC_ACCEPTANCE_FRONTEND_BUILD_SHA=8bd99a72…f266`）报 `units=89 state_counts.stale=89`
（复用键 `frontend_build_sha256`）。据此以 `make verify.frontend.business_entry.matrix.incremental`
在部署身份上以 `make verify.frontend.business_entry.matrix.incremental` 增量重取：

- **89/89 checked**（`ok=45 empty=38 ready=5 form=true=1`），`problems=0`、`console_errors=0`；
- 负例：89/89 均有可判定的拒绝候选，`leaked_entries` 全空，`uncovered_entries=0`；
- **独立复核**：用 `business_entry_matrix_scope.mjs --emit-results` 对同一 `summary.json` 独立重折叠，
  得 89 checked、`partial=false`，且条目键集合与 CSV/账本完全一致；
- 复用键 `frontend_build_sha256=8bd99a72…f266`；证据
  `artifacts/frontend-business-entry-matrix/incremental/20261009-closeout-resume/summary.json`。

### 5.6 取证体系机制修复（P4，与产品能力无关）

上一轮重取暴露的是**取证体系自身**的缺陷，不是产品缺陷：

- 事实：探针只在 `main()` 结尾一次性写 `summary.json`。一次 `POST /api/v1/intent` 401 触发
  应用回跳 `/login` 后，后续每条 `page.goto(..., waitUntil:'networkidle')` 全部 30s 超时，
  进程结束时得到 `6 通过 + 83 无结论`（83 条 `list_status=None records_rendered=None`）。
- 二次伤害：`scope` 适配器把"选择集中没有逐条观察"的键一律记为 `failed`，
  于是"输入未变不得重跑失败单元"的门禁反过来**阻断续跑**——空跑被固化成失败。

三项修复（均在本轮提交边界内，产品断言、ACL、字段权限、负例一律未放宽）：

1. **逐条持久化 + 断点续跑**：每条结论落 `entries.jsonl`（append）并原子重写
   `summary.json`（`completeness: partial`）；`SIGINT/SIGTERM` 先落盘再退出；
   同一身份（target + served bundle + base_url + database + login + 选择键）重启时复用已完成条目。
2. **会话自愈（有界）**：探针在响应流上识别 `intent` 401，重新登录一次并**只重试该条**，
   重试前丢弃被中止尝试的部分结论；恢复失败则整轮中止为 partial，而不是空烧剩余选择集。
   业务断言失败照常返回，**从不重试**。
3. **partial 语义（unreached ≠ failed）**：未到达的单元**不记录**（既不通过也不失败），
   recorder 把 `planned_affected` 收窄为真正执行的单元，未到达者保持 never-recorded，
   下一轮自动续取，从而支持"迭代推进到全通过"。

证据：

- 机制 smoke（`SC_ENTRY_MATRIX_KEYS=…menu_sc_p1_cost_ledger`）：`entries.jsonl` 逐条落盘；
  `completeness=partial`（进行中）→ `complete`，`ok=true problems=0 console_errors=0`；
  同目录二次运行输出 `resumed 1 completed entry`，未重跑该条。
- `make verify.frontend.business_entry.evidence_scope.unit` PASS：
  `evidence_scope` + `incremental` 32 tests、`reuse_identity` 23 cases；
  新增 `PartialFoldPlanTests`、`EmitResultsStatusTests` 两个 partial 用例。
- 决策记录：`.agent/decisions/evidence-capture-resilience.yaml`（OPS-DECISION-003）。

## 6. 状态边界（更新）

- **批次验收**：通过（P0 门禁修复 + 受管部署 + 浏览器正/负例复核 + 用户视角矩阵 89/89 增量复取 + 独立重折叠复核 + 取证体系机制修复门禁）。
- **主线集成**：修复提交在候选分支；未并入 `main`（未主张集成状态）。
- **版本发布**：未主张（日常 dev 运行态对齐，非正式版本发布）。
- **产品交付**：技术证据就绪，**待所有者登录核对**（`http://1.95.85.92:18081/`，`wutao/123456`，库 `sc_demo`）。
