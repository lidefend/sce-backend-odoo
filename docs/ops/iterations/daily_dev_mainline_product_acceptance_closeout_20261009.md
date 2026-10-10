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

## 7. 角色锁定驱动的验收数量机制（P4）

### 7.1 根因

验收侧 `ACCEPTANCE_NAV_MIN_ACTIONS/MAX_ACTIONS` 原来是一个**与角色无关的全局常量 89**。
但菜单数量只有在**具体角色锁定后**才确定：不同角色看到的是不同的契约交付面
（`business_config_admin` 发现已安装能力面=89，而 `finance`=45、`pm`=24、`owner`=5、
`project_member`=10）。用管理员面去度量其他身份，等价于**验收未契约驱动**——这是本轮
用户判定"前面一直按 89 验收是不对的"的直接原因。

### 7.2 机制（锁定机制，不锁定数字）

`config/frontend/acceptance_environments_v1.json` 的 daily `navigation_policy.action_count_authority`
改为 `scope: locked_role_surface`，显式声明：

- `principal_role`：本次验收锁定的主体角色；
- `role_surfaces`：每个受验角色 → 其权威版本化来源
  - `business_config_admin` → `installed_capability_surface`（产品契约 `policy_strategy.effective_menu_count_per_product`）；
  - `finance`/`pm`/`owner`/`project_member` → `locked_role_navigation_manifest`
    （`config/frontend/authoritative_navigation.json` 的已锁清单长度，且 `expected_count` 必须等于清单去重身份数）。

解析由单一来源 `scripts/verify/acceptance_action_count.py` 完成：数量**派生**而非钉死；
未列入 `role_surfaces` 的 principal 角色、或清单声明数与锁定身份数不一致，一律 fail-closed。

运行态闭环：`scripts/ops/dev_acceptance_release_probe.py` 新增 `role_code_expected`，
当 `system.init` 返回的 `role_code` 偏离声明的 `principal_role` 时报 `role_code_unexpected`，
避免"角色漂移 + 数量断言"错配后被静默放过。

### 7.3 归属与边界

- 全部改动在 **P4 验收工具层**（`config/frontend` 验收策略 + `scripts/verify` + `scripts/ops` 探针 + `make` 接线）。
  P0/P1 业务语义、ACL、字段权限、负例断言一律未放宽，也不含模型特判。
- 89 仍作为 `business_config_admin` 的**派生结果**出现，不再是任何地方的输入常量。

### 7.4 检查（离线，均通过）

| 目标 | 结果 |
| --- | --- |
| `verify.acceptance_action_count.unit` | 14 tests PASS（finance=45/pm=24/owner=5/project_member=10/business_config_admin=89；未列角色与钉死数字 fail-closed） |
| `verify.product.menu.release_manifest_v2.guard` | PASS centers=10 contract_pages=89 accounting_pages=6 total=89；各角色来源均可解析 |
| `verify.frontend.release_navigation_policy.guard` | PASS roles=4 released_leaf_identities=84 |
| `verify.scene.role.policy.consistency.guard` / `verify.scene.role.surface.consistency.guard` | PASS（角色集由契约声明驱动） |
| `verify.contract.structure_lock` / `verify.frontend.auth_surface.guard` / `verify.frontend.auth_credential.guard` | PASS |
| `verify.environment.topology.guard` / `verify.dev.acceptance.release_probe.schema.guard` | PASS |
| `make ci.local.iteration` | PASS（L1, dirty） |

### 7.5 运行态读回（已取得，闭环）

经受管入口刷新日常运行态后读回（base `http://1.95.85.92:18081`，库 `sc_demo`）：

- `daily.runtime.candidate.bundle_sync`：PASS；old `3d90df05…`，`source_sha=d106d2dd…`，
  `origin_main_mutated=false`，evidence_ref `refs/daily-candidates/audit/daily-dev-mainline-product-acceptance-closeout-20261009`。
- `daily.runtime.source_revision.align`（`DAILY_RUNTIME_SOURCE_REVISION_SHA=d106d2dd…`）：PASS；
  `served.source_revision=d106d2dd…`、`restarted=true`。

`verify.daily_dev.acceptance.readonly.probe` 正/负例：

| 断言 | 正例 | 负例（声明 `finance`/45，实登管理员） |
| --- | --- | --- |
| `served_sha` | `d106d2dd…` PASS | `d106d2dd…` PASS |
| `frontend_build_sha256` | `8bd99a72…f266` | 同 |
| `role_code` vs `role_code_expected` | `business_config_admin` == 声明 | `business_config_admin` ≠ `finance` |
| `nav_action_count` | `89`（= 锁定角色面派生值） | `89`（> 45 上限） |
| 身份 | `吴涛` uid 16，`system_init_ok=true` | 同 |
| 结论 | **PASS** | **FAIL**：`role_code_unexpected`、`nav_action_count_above_max` |

负例按预期失败，说明数量断言**真实**：角色漂移叠加管理员面会被拒绝，而不是被静默放过。
产物：`.runtime/daily-readback-candidate.json`、`.runtime/daily-readback-negative.json`。
本机制在服务实例上的效果自此**已证明**。

## 8. 账本复用完整性（P4，迭代效率根因）

### 8.1 现象与根因

用户反复指出"跑通了的结论不能复用、总是重跑全量"。核查后确认这是**账本机制**的缺陷，不是产品缺陷：

- run 账本里有 **21 条声明级 `status: PASS`/`detail`**，但 `make agent.run.resume` 报告
  **23/23 全部 `not_run`/`stale`**。原因：`scripts/ops/agent_run_context.py` 只从
  `.runtime/agent-runs/<run>/<check>.json` 回执读取裁决，写进 `run.json` 的裁决**完全无效**，
  于是"声称 PASS"与"无任何证据"可以共存。
- 声明**未要求绑定真实入口**：两条检查引用 `verify.acceptance_action_count.unit` 与
  `verify.dev.acceptance.release_probe.schema.guard`，而任何 Makefile 分片都**没有定义**这两个目标
  （真实入口分别是新增的 `verify.acceptance_action_count.unit` 与
  `verify.dev.acceptance.release.schema.guard`）。无法执行的检查永远无法被记录，也就永远无法复用。
- `kind` 可选，7 条检查缺省；复用引擎把缺省 `kind` 视为 runtime，**通过也无法转为可复用**。
- 已执行的检查从未走 `make agent.run.begin/record`，输入哈希索引始终为空。

### 8.2 机制修复

- `resolve_run` 现在对以下情况 **fail-closed**：检查缺 `kind`、携带声明级 `status`/`detail`、
  或引用任何 Makefile 分片都未定义的目标。声明里不能再出现裁决，叙事留在本记录。
- 新增 `make/guards.mk` 目标 `verify.acceptance_action_count.unit`，让角色锁定数量解析器绑定到
  **带测试计数的入口**，不再搭在宽泛的 daily env guard 上（绑定越窄，失效面越窄）。
- `summary()` 新增 `check_reuse_summary`，可复用/失效/未跑一眼可见，不再靠推断。
- 12 条离线检查经 `begin/record` 重跑并写入**输入绑定回执**。
- `ci_local_iteration` 的复用键补上配方实际执行却漏声明的
  `make/ci.mk`、`scripts/verify/frontend_dev_incremental.py`、`scripts/ci/trusted_scan_scope.py`。

### 8.3 度量与残余

| | 检查数 | reusable | not_run | stale |
| --- | --- | --- | --- | --- |
| 修复前 | 23 | **0** | 19 | 4 |
| 修复后 | 25 | **12** | 11 | 2 |

`not_run` 的 11 条 = 4 条 runtime（按设计需重新读回）+ 6 条纯守卫目标 + `frontend_typecheck`，
后 7 条**不产出非零测试计数**，按现行契约无法记为可复用证据，只能每轮重跑（各约 2–3s）。
**残余**：给这些目标补带测试计数的入口，是其加入可复用集的有界后续项；
这不能通过放宽"非零测试计数"规则来绕过。

### 8.4 声明纠偏：stale 2 → 0（未重跑任何测试）

`make agent.run.resume` 此前报 `stale=2`（`daily_runtime_source_revision_align`、
`daily_runtime_frontend_build`），交接时被解读为"运行时车道环境未对齐"。逐项比对**回执原文**后确认
与产品、环境均无关，是三处**声明缺陷**：

1. **kind 误声明。** 这两个目标是纯离线单测入口（`py_compile` + 单测运行器），
   `make/codex.mk:735/767`；其回执本身记录的也是 `kind=offline`。但 `run.json` 把它们声明为
   `kind=runtime`，而本 run 的 `environment.kind=offline`。复用引擎对 `kind!=offline` 的检查
   恒抛 `runtime evidence requires authoritative environment readback`
   （`scripts/ops/agent_run_context.py` `evaluate()`），即**结构上永远不可能转为可复用**——
   这类检查只要声明成 runtime，就必然每轮重跑。
2. **漏依赖。** 两条检查声明的 `inputs` 只有 2 项，回执记录的是 3 项（含 `make/codex.mk`）。
   同一缺陷更明显的一例：`daily_runtime_candidate_bundle_sync` 声明的输入是 **main 车道**
   脚本 `daily_runtime_bundle_sync.py`，而 `make/codex.mk:711` 该目标实际执行的是
   `daily_candidate_bundle_sync.py` / `test_daily_candidate_bundle_sync.py`。
3. **未被索引的证据。** main 车道回执（`9 tests`、`status=passed`、`log_sha256` 校验通过）
   文件名是 `daily_runtime_bundle_sync.json`，与任何已声明检查 id 都不匹配，因此从未被读取，
   一直计入 `not_run`。

**修正内容（不含任何断言放宽、不含任何测试重跑）：**

- 两条检查 `kind` `runtime → offline`（与回执及目标实际执行内容一致）。
- 两条检查 `inputs` 补回 `make/codex.mk`（回执记录的完整依赖集）。
- `daily_runtime_candidate_bundle_sync` 的 `inputs` 改为其目标真实执行的依赖。
- 新增检查 id `daily_runtime_main_bundle_sync` 绑定 `verify.daily.runtime.main.bundle_sync`，
  并将既有回执重命名使其可被索引（**保留证据，未删除**）。

| | 检查数 | reusable | not_run | stale |
| --- | --- | --- | --- | --- |
| 8.3 移交态 | 26 | 13 | 11 | 2 |
| 本轮声明纠偏后 | 27 | **16** | 11 | **0** |

**边界（必须与"运行时已对齐"区分）：** 上述 reusable 只证明**离线单测**通过，**不等于**日常
运行态已完成身份对齐。真实运行时写入是受确认串约束的受管入口
`make daily.runtime.source_revision.align` / `daily.runtime.frontend.build`，它们不是 `verify.*`
目标，无法进入 run 的检查索引；其效果由 runtime 类读回检查承载
（`browser_login_return_authority`、`business_entry_matrix_recollect`、`daily_acceptance_readback`），
三者目前仍为 `not_run`。

**待所有者裁定：** 候选车道与 main 车道两个 bundle-sync 检查现并存；本 run 声明的运行路径是
main 车道，候选车道检查保留但尚无回执。

## 9. 前端 `.js` 边界裁定（P0 渲染机制，所有者决定 A）

### 9.1 事实

- `frontend/apps/web/src` 下共 **7 个 `.js`**，**全部为既有文件**，本批次未新增：
  `app/actionViewRouteLeaseCore.js`、`app/capabilityCore.js`、`app/capabilityPolicyCore.js`、
  `app/navigationSelectionCore.js`、`app/view_state.js`、`app/resolvers/menuResolverCore.js`、
  `app/resolvers/sceneRegistryCore.js`。引入来源：`401bcb3b`（干净产品基线）5 个、
  `5baaa048`（RC14）1 个、`c5a19c15` 1 个。本批次 dirty 中只有
  `navigationSelectionCore.js` 被修改。
- 源码规模：`497` 个 `.ts`、`226` 个 `.vue`、`0` 个 `.mjs`/`.jsx`（前端源码内）。

### 9.2 为什么是 `.js`（既定策略，不是疏漏）

- 这些文件是自 `.vue` 抽出的**纯函数 core**，唯一目的是让验证脚本用**裸 node 直接 import**，
  无需 TS 装载或构建：`scripts/verify/fe_view_state_smoke.js` 用
  `require(.../view_state.js)`，`scripts/verify/frontend_navigation_initialization_race.test.mjs:5`
  直接 `import ... navigationSelectionCore.js`。
- 主 tsconfig 保持 `allowJs=true / checkJs=false / strict=false`，strict 边界只覆盖
  `src/contracts/**/*.ts`、`src/api/scene.ts`、`src/views/SceneHealthView.vue`，
  见 `docs/ops/stage_defs/phase_10_5_frontend_type_recovery.md`（遗留类型债隔离期）。

### 9.3 边界结论

- 内容扫描：7 个文件无模型名、字段名、行业语义。唯一 `res_model` 命中是
  `menuResolverCore.js:86` 的**透传读取**（`meta.model = node?.native_model || actionMeta.res_model`），
  不是硬编码业务判断。
- 职责是"契约产物 → 渲染/交互"所需的归一与选择（capability 状态映射、菜单解析、导航选择、
  空/错状态派生、路由租约竞态判定），属 **P0 前端渲染机制**，**不构成前端越界做业务逻辑**，
  也**不需要等契约补缺**。

### 9.4 已确认缺口与处置

- 缺口：这 7 个文件**同时逃过** `vue-tsc`（`checkJs=false`）与 ESLint（`--ext .ts,.vue`），
  即前端逻辑密度最高的部分零静态检查，仅由 node 冒烟/单测保底。
- **所有者裁定（A）**：本轮不扩改动，保持现状；把「收敛为 `.ts`」与「纳入 ESLint + 受限
  `checkJs` 白名单（不改扩展名）」登记为**后续 P4 迭代项**，不并入本批次。
- 附带观测：全量 `vue-tsc`（`497` `.ts` + `226` `.vue`，无 incremental/tsBuildInfo）实测 ≥10 分钟。
  本批次前端改动只有 `navigationSelectionCore.js`，其对口验证是 2 秒的
  `verify.frontend.navigation_initialization_race.unit`（已跑、35 tests、可复用）。
  全量 typecheck 的**定向化/缓存化**同为后续 P4 项，须先立项再改，不直接大改门禁。

## 10. 契约行与守卫规则对齐：声明式场景入口（route A 判别联合的最后一环）

### 10.1 现象

`make verify.contract.view_structure` 在**本批之前与之后都 FAIL**，但失败形态不同：

| | 该守卫的裁决 |
| --- | --- |
| 基线（HEAD policy） | 6 条陈旧绑定错误 |
| 本批（新增 `角色首页` 契约行） | **提前 `raise` 一条冲突**，把上述 6 条全部掩盖 |

即本批新增的契约行与其守卫规则**不兼容**：守卫没跑到陈旧绑定检查就中止了。

### 10.2 根因

`scripts/contract/product_view_structure_common.py::policy_menu_rows` 对每条
`enabled && release_state == "released"` 的能力**硬性要求** `menu_xmlid && res_model`，
缺一即 `conflicts.append(...)`，循环结束后 `raise ValueError("; ".join(sorted(conflicts)))`
（该 raise 是 fail-closed，本身没问题）。

但 route A（所有者已批准）的**声明式场景入口**按设计**没有模型承载面**：
`disposition_policy/entry_target_policy == "scene_entry"`，`action_xmlid=""`、`res_model=""`，
授权基准是原生菜单锚点 + 服务端角色化契约投影，执行目标是 `target_scene_key`
（见 `docs/architecture/menu_scene_anchor_policy_v1.md`「Identity (Single Source)」）。因此它
**必然**触发该冲突。

关键：`policy_menu_rows` 同时被**导出器**（`scripts/contract/export_product_view_structure.py:273`）
与**守卫**（`scripts/verify/product_view_structure_contract_guard.py:68`）消费。若不一并修正，
发布车道的运行时导出同样会 `raise`，形成"契约声明了却永远导不出来"的死结。

### 10.3 判定

这不是"断言太严"，而是**守卫与导出器未建模 route A 的判别联合**——与 §9 同类的体系缺口。

### 10.4 修正（fail-closed，未放宽任何既有断言）

`policy_menu_rows` 先判断是否为声明式场景入口：

- 是：要求 `menu_xmlid` **且** `target_scene_key`，并**禁止**声明 `res_model`；满足后从
  view structure 行集中**排除**（场景入口无视图结构面，不应进入该清单）。
  缺 `target_scene_key` 或误带 `res_model` → 仍然 `raise`。
- 否：原规则**逐字不变**（`menu_xmlid && res_model`）。

### 10.5 证据

- 新增 3 条单测（场景入口被排除 / 缺 `target_scene_key` 失败 / 误带 `res_model` 失败）；
  `scripts/verify/test_product_view_structure_contract.py` 22 → **25**。
- 新增受管入口 `make verify.product_view_structure.contract.unit`（`make/guards.mk`），
  沿用 §8.2 的**窄绑定**模式：守卫单元测试绑定到带测试计数的入口，而不是搭在
  `verify.contract.view_structure` 或发布导出车道上。
- 回执：`25 tests`、`status=passed`、可复用（`source_head=f631cf04`）。

### 10.6 结果与边界

- `make verify.contract.view_structure` 回到**与 HEAD 完全一致的 6 条错误**：
  `formal menu coverage differs from policy`、4 条 candidate fingerprint provenance
  （`baseline_sha` / `scope_manifest_sha256` / `digest` / `branch`）、
  `formal menu policy hash mismatch`。即**本批不再引入新的失败模式**。
- 这 6 条属**发布/导出车道的受管产物重生成项**：`contracts/generated/product_view_structure_contract.json`
  记录 `formal_menu_policy_sha256=80b5c7d5bb...`（与 HEAD policy `bc4274a3...`、本批 policy
  `bcefc90c...` 均不同）并绑定旧分支 `feature/native-view-action-semantics-closure-v1` /
  `git_head=01a29b14`。该目标**不属于任何聚合门禁**，重生成必须走受管运行时导出车道
  （`make contract.view_structure.export` → `gate.contract.view_structure`），**不得 offline 手改**。

### 10.7 账本现状

| | 检查数 | reusable | not_run | stale | failed |
| --- | --- | --- | --- | --- | --- |
| 本轮声明纠偏后（§8.4） | 27 | 16 | 11 | 0 | 0 |
| 叠加本节窄绑定入口 | **28** | **17** | 11 | 0 | 0 |

## 11. 运行态读回车道（本轮执行：两个结论 + 一个部署闸门 + 一个前置未就绪）

环境身份先核实：`sc-root:/opt/projects/repos/sce-product-odoo` 树处于 `d106d2dd` 且**干净**，
`COMPOSE_PROJECT_NAME=sc-backend-odoo-dev`、`DB_NAME=sc_demo`、`NGINX_PORT=18081`、
`SC_SOURCE_REVISION=d106d2dd…`、`FRONTEND_BUILD_SHA256=8bd99a72…f266`；
`/api/runtime-version` 回读与之一致。**注意**：本机 `sc-local-dev` 组合也占用 18081，所有日常车道调用
必须显式传 `ACCEPTANCE_BASE_URL`/`FRONTEND_URL=http://1.95.85.92:18081`，不得落到缺省 `127.0.0.1`。

### 11.1 离线守卫批量执行（7 条全部 PASS，其中 1 条转为可复用）

| 检查 | 目标 | 结果 |
| --- | --- | --- |
| `daily_runtime_candidate_bundle_sync` | `verify.daily.runtime.candidate.bundle_sync` | PASS，**6 tests**，回执可复用 |
| `contract_structure_lock` | `verify.contract.structure_lock` | PASS（`domains=14`） |
| `scene_role_policy_consistency` | `verify.scene.role.policy.consistency.guard` | PASS（payload 25 / role_variants 22） |
| `scene_role_surface_consistency` | `verify.scene.role.surface.consistency.guard` | PASS（roles 10 / r3 scenes 22 / warnings 17） |
| `frontend_auth_credential` | `verify.frontend.auth_credential.guard` | PASS（sensitive_screenshot=0 / trace 0） |
| `frontend_auth_surface` | `verify.frontend.auth_surface.guard` | PASS（contract_pages=3） |
| `dev_acceptance_release_probe_schema_guard` | `verify.dev.acceptance.release.schema.guard` | PASS |

6 条纯守卫 + `frontend_typecheck` 仍**不产出非零测试计数**，按 §8.3 的既有契约无法进入可复用集
（"给这些目标补带测试计数的入口"是其**有界后续项**，不放宽"非零测试计数"规则）。
`scene_role_surface_consistency` 会重写 `docs/audit/scene_role_surface_consistency_report.md`，
本轮差异仅时间戳，已还原，不并入本批 diff。

### 11.2 列表矩阵复用（`business_entry_matrix_recollect`）：未执行任何浏览器走查

`make verify.frontend.business_entry.matrix.incremental`（`ACCEPTANCE_TARGET_SHA=d106d2dd…`、
`DB_NAME=sc_demo`、base `http://1.95.85.92:18081`）：

- 复用身份由运行态发布：`FRONTEND_BUILD_SHA256=8bd99a72…f266`，与台账记录一致。
- `declared=89 units / reusable=89 / affected=0` → `REUSE-FIRST nothing to execute`，退出码 0，**未打开浏览器**。
- 日志 `.runtime/eff/rec/business_entry_matrix_recollect.log`。
- 结论：列表面在本批下**零回归**（这正是"能复用必须先复用"应有的形态：4 秒、零走查）。

### 11.3 日常只读探针（`daily_acceptance_readback`）：唯一失败 = 部署闸门

首次运行暴露 3 个错误。逐项定位后，**只有一个是契约事实**，另两个是验收前置的绑定/产物错误：

| 错误 | 归属层 | 事实与处置 |
| --- | --- | --- |
| `contract_probe_auth_failed` | 调用绑定（非产品） | 契约探针以 `fixture_role_finance` 取会话；日常库该 fixture 口令为固定开发口令，而 `ACCEPTANCE_CONTRACT_PASSWORD` 缺省继承了隔离 profile 的 `scdevpass`。实测：`scdevpass` → `AccessDenied`，固定开发口令 → `uid=210`。按真实凭据传入后消失。 |
| `record_resolution_served_sha_mismatch` | P4 受管产物（非产品） | `artifacts/backend/acceptance_record_identity.json` 绑旧 SHA（本地 `aea2c19b` / 远端 `6c8e07f7`），served 为 `d106d2dd`。走受管入口 `make daily.dev.acceptance_contract.resolve`（远端、`sc-backend-odoo-dev`、`sc_demo`，入口自身先 HTTP 校验 `served_sha==ACCEPTANCE_TARGET_SHA`，不符即 DENY）重生成后消失。 |
| `nav_action_count_below_min` | **契约/部署闸门** | 本批新增 `角色首页` 契约行 → 工作区解析 `acceptance_action_count=90`（`role=business_config_admin`）；served 运行态仍是 `d106d2dd`（89）。 |

前置修正后在同一 served SHA 重跑，结果收敛为**唯一失败**：

- `runtime_identity`：PASS（served `d106d2dd`、`database=sc_demo`、`frontend_build_sha256=8bd99a72…f266`）。
- `frontend`：PASS。
- `contract`：**11/11 全 PASS**、`errors=[]`；custody 1 048 331 bytes / sha256 `7c249c12…`。
- `login`：FAIL，`errors=["nav_action_count_below_min"]`；`nav_action_count=89`、违禁标签命中 0、
  必需路径缺失 0、`role_code=business_config_admin` 一致。

**裁定（不放宽断言）**：`DAILY_ACCEPTANCE_NAV_MIN_ACTIONS/MAX_ACTIONS` 由版本化契约解析——
本批使契约 89 → 90，而运行态尚未承载本批改动，该断言**按设计必然失败**，且**不得**改成 89 来"通过"；
它是"工作区契约与部署面不一致"的**正确告警**。回执记为 `status=failed`、`test_count=11`
（= 契约面 `required_checks` 数），语义为"已诊断、未变前置不得重试"。

### 11.4 `browser_login_return_authority`：前置未就绪，未执行

`verify.nav.pro01r.route_authority.browser` 的登录主体是
`nav_pro_{config_admin,system_admin,pm,project_member}`。实测日常库 `sc_demo` 上这 4 个登录**不存在**
（`AUTH_REQUIRED`）；它们由受管入口 `make nav.pro01.runtime.prepare`（需在远端
`sc-backend-odoo-dev` 组合内执行）建立。故本检查本轮**前置未就绪、未执行**；
不得以 handler 诊断替代一次真实"点击打开 → 返回 → 标签/动作恢复"走查（该走查是详情收口的硬要求）。

### 11.5 声明纠偏（本轮新增，未放宽任何断言）

`daily_acceptance_readback` 的 `inputs` 补入 `artifacts/backend/acceptance_record_identity.json`：
探针确实消费该受管解析产物（`ACCEPTANCE_RECORD_RESOLUTION`），原声明漏依赖，会允许
"产物换了而结果被当作未变"。这是"输入列表必须包含测试工具与依赖"的最小修正。

### 11.6 边界：本批回归口径 ≠ 运行态已对齐

`daily_acceptance_readback` 的失败**不代表本批产品缺陷**，而是**本批尚未部署**。本批的产品面
（`角色首页` 场景入口、场景/角色契约统一、`menu_service` 投影、前端 `navigationSelectionCore.js`）
只有经 **commit → 合并 → 部署 + 模块升级**（新锚点是菜单记录）才会出现在 `sc_demo` 运行态；
在此之前用户视角验收**不可能**通过，也无法用只读探针替代。

### 11.7 账本现状

| | 检查数 | reusable | not_run | stale | failed |
| --- | --- | --- | --- | --- | --- |
| §10.7 | 28 | 17 | 11 | 0 | 0 |
| 本轮 | 28 | **18** | 9 | 0 | **1** |

`not_run` 9 = 3 条 runtime 读回（`browser_login_return_authority` 前置未就绪；
`business_entry_matrix_recollect` 已按复用优先执行、零走查；`daily_acceptance_readback` 另有回执）
+ `frontend_typecheck` + 5 条纯守卫目标（非零计数契约外，见 §8.3）。

### 11.8 `frontend_typecheck`（本轮实测）+ 其声明输入修正

- **实测**：`make verify.frontend.typecheck.strict`（`vue-tsc --noEmit` 主项目 + `-p tsconfig.strict.json`
  严格子项目）于 HEAD `f631cf04` **EXIT=0**，无任何诊断输出；日志
  `.runtime/eff/rec/frontend_typecheck.log`。即本批（唯一前端改动是 `navigationSelectionCore.js`）
  之后，前端**全量严格类型检查通过**。
- 仍**不建回执**：该目标不产出测试计数，按 §8.3 的既有契约无法进入可复用集（其"定向化/缓存化"
  已由 §9.4 登记为后续 P4 项）。本轮结果以本记录 + 原始日志承载。
- **声明输入修正（防假复用）**：该检查原 `inputs` 只列了 5 个文件（`tsconfig.json`、`package.json`
  与 3 个被点名文件），**不含被检查的源码树**，若将来被记为可复用，`src` 中任一处改动都不会使其失效——
  这是**不成立的复用边界**。现改为真实依赖集合：`frontend/apps/web/src`（**目录**，逐文件哈希）、
  `tsconfig.json`、`tsconfig.strict.json`、`package.json`、`vite.config.ts`。未放宽任何断言。

## 12. 快照同步问题闭环（2026-10-09 第 12 轮）

### 12.1 事实结论：快照本体一直在同步，缺口在"服务/消费面"

`sc.edition.release.snapshot` 的回执每次都带当前候选 SHA（`snapshot_version=daily-navigation-<sha12>`、
`refreshes.*.changed=true`、`snapshot_released_page_count=90`），即**快照本身没有滞后**。真正没有跟上的是
两条别的东西，且都发生在"同步之外"：

| 层 | 现象 | 根因 | 修复 |
| --- | --- | --- | --- |
| 发布面 vs 代码面 | 契约已变、闸门仍读上一代契约 | 两个面分属两条独立发布车道 | `daily.runtime.candidate.release` 固定为 `bundle_sync → source_revision.align → published_face.converge` |
| served 身份 | `/api/runtime-version` 报旧 SHA | `SC_SOURCE_REVISION` 未随树更新 | 同一入口内声明并回读 exact deployed HEAD |
| 冻结时机 | 新投影代码未生效就冻结 | `guard.codex.fast.upgrade` 拒绝未声明的升级（`MODULE_UPGRADE_FAILED`） | 按受管模式声明 `CODEX_NEED_UPGRADE=1` + `CODEX_MODULES`，并把升级尾部日志带进失败信息 |
| 消费面（用户可见） | 闸门 PASS 但 `system.init` HTTP 500 | 规范投影只认 `action_id>0` / `menu_containers`，把契约声明的 scene 入口（`menu_id=1004, action_id=0`）判为"无目标节点"并抛错 | 服务端投影与前端镜像共同消费同一"声明授权"载体；发布闸门守卫补齐投影尾部，不再"只跑闸门" |

### 12.2 部署回执（候选 `4b7f9a46`，仅日常运行时，未进 main）

- `daily.runtime.candidate.bundle_sync` PASS；`old 0d9e4500…` → `source_sha 4b7f9a46…`，`origin_main_mutated=false`。
- `daily.runtime.source_revision.align` PASS；`served.source_revision=git_sha=4b7f9a46…`。
- `daily.runtime.published_face.converge` PASS（`upgrade_modules=[smart_core]`）；`snapshot_id=39/40`、
  `daily-navigation-{standard,preview}-4b7f9a46`、`gate_page_count=kept_leaf_count=90`、`guard PASS`。
- `daily.runtime.frontend.build` PASS；`frontend_build_sha256=a3f477a4…`、`entry_asset=index-Buu4bI2N.js`。
- 回执：`.runtime/final-acceptance/daily-deployed/{candidate-bundle-sync,source-revision-align,published-face-converge,frontend-build,record-identity-resolve}.json`。

### 12.3 用户视角读回（`wutao/123456`，`sc_demo`）

- `system.init` **HTTP 200**（变更前同账号同库为 **HTTP 500**）；112 个节点全部带 `canonical_navigation` 投影，
  `enabled=94 / container=18 / disabled=0`。
- `角色首页`：`menu_id=1004`、`action_id=null`、`state=enabled`、`authority.state=allowed`、
  `authority.source=nav.declared_entry`、`route=/s/workspace.home`。
- `navigation.meta.platform_release_gate`：`snapshot_id=39`、`allowed_page_count=kept_leaf_count=90`、
  `removed_leaf_count=0`。

### 12.4 只读探针 正/负例（断言未放宽）

| 断言 | 正例（`wutao`，`business_config_admin`） | 负例（声明 `finance`/46，实登管理员） |
| --- | --- | --- |
| `served_sha` / `frontend_build_sha256` | `4b7f9a46…` PASS / `a3f477a4…` | 同 |
| contract 段 | 11/11 PASS | PASS |
| `role_code` vs 声明 | 相等 | **不等** → `role_code_unexpected` |
| 计数 | `nav_admitted_entry_count=90 == nav_gate_kept_leaf_count=90 == 契约 90` | `90 > 46` → `nav_entry_count_above_max` |
| 结论 | **PASS** | **FAIL**（按预期） |

计数口径修正（非断言放宽）：契约授权字段名为 `effective_menu_count_per_product`（**菜单条目**数），而探针原先
只统计 `action_id` 非空的节点；声明式 scene 入口天然没有业务动作，于是"90 条契约 vs 89 个动作节点"永远无法
同时成立。现按契约人口（受闸门放行的叶子条目）计数，并**新增**与发布闸门 `kept_leaf_count` 的等式校验。
`nav_action_count=89` 继续作为事实记录。产物：`.runtime/daily-readback-{candidate,negative}.json`、
`artifacts/backend/daily_dev_acceptance_probe.json`、`artifacts/backend/acceptance_record_identity.json`。

### 12.5 账本复用边界（设计约定，非缺陷）

`make agent.run.record` 已为 `daily_acceptance_readback` 写入绑定身份的回执（39 项断言、日志哈希）。
但 `scripts/ops/agent_run_context.py` **只自动复用声明的 offline 检查**：`kind=runtime` 的回执一律保持
`stale`，理由固定为 `runtime evidence requires authoritative environment readback`
（由 `scripts/verify/test_agent_run_context.py::test_runtime_receipt_never_auto_reused` 锁定）。
因此 runtime 车道的权威读回在本批由 `.runtime/final-acceptance/daily-deployed/*.json` + 上述回执承载。
"运行态证据可复用"需要先引入**声明式权威环境读回**机制，登记为下一项 P4 项（见 §13），本轮不擅自改变该约定。

### 12.6 未完成项

1. 浏览器关系交互车道：`nav_pro_*` fixture 受管制备 + `verify.nav.pro01r.route_authority.browser`
   一次真实"点击打开 → 返回原记录 → 标签/动作恢复"。
2. 主线集成：等待用户明确授权（本轮指令为"先不执行进入主线"）。
## 13. 迭代效率闭环（2026-10-09 第 13 轮）：扫描作用域不再用"进程数"换 O(n)

### 13.1 现象与度量

用户反馈"日常迭代这么慢"。先量后改，实测 `make ci.local.iteration`：

| 步骤 | 累计耗时 | 说明 |
| --- | --- | --- |
| `agent_run_context` | 0.20s | 台账解析 |
| `frontend_dev_incremental --plan-worktree` | 0.18s | 受影响面推荐 |
| `trusted_scan_scope` | **30.1s** | 占整个入口 37s 的 **82%** |
| 入口合计 | **36.8s** | |

### 13.2 根因：Git 子进程数随仓库规模线性膨胀

`scripts/ci/trusted_scan_scope.py` 只做"作用域选择"，却付出 11,074 次 Git 子进程：

1. `valid_coverage` 对快照里**每一个 ref** 单独跑一次 `git cat-file -t` 校验对象类型。
   本仓库 272 个 ref × 9 个候选快照 × 3 个扫描器 ≈ 7,300 次调用；
2. `authority_digest` 对**每一个授权文件**在**每一个 revision** 上单独跑一次 `git show`，约 1,863 次。

两者都与"被扫描内容多少"无关，只与"仓库有多少 ref / 有多少 revision 要复核"有关，
因此每次迭代都重复付全额成本。

### 13.3 修正：两个进程做完同样的判定（语义严格等价）

- `ref_object_types`：一次 `git cat-file --batch-check` 解析全部 ref tip 的对象类型。
  **仍然逐条断言**每个声明的 `(oid, type)` 对（共享 oid 不能用一个类型同时满足两条声明）；
  tip 缺失仍是硬失败。
- `revision_blob_sha256`：一次 `git ls-tree -r -z` + 一次 `git cat-file --batch` 取回全部授权 blob。
  某 revision 上缺失的授权路径仍然是硬失败（等价于原先 `git show` 抛错）。
- 摘要口径未变：仍是 `sha256(json([(path, sha256(content))]))`，仅取数方式改变。

### 13.4 证据

- **等价性**：用旧的逐文件 `git show` 实现重算，与新区间在 **24 个历史 revision + 工作区** × 3 个扫描器上
  逐条比对，**0 处偏差**。
- **耗时**：`make ci.local.iteration` **36.8s → 6.9s**；`trusted_scan_scope` **30.1s → 3.3s**；
  作用域选择内的 Git 调用 **9,211 → 81**。
- **测试**：`scripts/ci/test_trusted_scan_scope.py` 30/30 PASS；`make security.online_capture.unit` PASS。
  新登记检查 `trusted_scan_scope_unit`（`verify.trusted_scan.unit`）已写入绑定身份的回执，随后即可复用。
- 提交：`8a1ef8ab`（`perf(ci): resolve trusted-scan scope identity in two git processes`）。

### 13.5 边界（未放宽任何东西）

作用域判定口径、失败闭合路径、扫描器授权摘要、`scan_authority_changed → full` 的保守逻辑**全部保持不变**；
本次只改"用什么方式取到同一结论"。因为 `trusted_scan_scope.py` 本身属于 `COMMON_AUTHORITY`，
这次改动会让既有的 Quick 覆盖率回执按设计失效一次（下次 Quick 走 full）——这是权威变更的正确表现，不是回退。

### 13.6 剩余效率缺口（已登记；第 1 项见 §13.8，第 2 项仍开放）

1. **部署闭环的模块升级无同码复用**：前端构建有"同 commit 复用回执"（`reused` 字段），
   但 `daily.runtime.published_face.converge` 每次都要重跑 `mod.upgrade`（例如 `smart_core`），
   即使模块代码相对上次部署**一字未改**。需要一份绑定"模块集 + 代码哈希 + 已部署 SHA"的有界回执，
   并以权威读回（模块状态/写入时间）证明可跳过；这是**写操作复用**，必须可回滚，不能想当然跳过。
   **→ 已在 §13.8（`3ee08386`）落地，采用 git tree oid 绑定 + 远端复解析的 fail-closed 形式。**
2. **运行态回执仍不可复用**（见 §12.5）：需要"声明式权威环境读回"（fail-closed）才能让 runtime 车道复用。
   仍写在 run 的 `blockers` / `next_exact_step` 里，未在本轮擅自扩大改动面。
### 13.7 前端类型检查：把"重复"降到编译器内部（`39a86b2f`）

`verify.frontend.typecheck.strict` 每次都对整棵源码树从零解析（主工程 +
`tsconfig.strict.json` 严格子工程各一次）。按 §11.8 的结论，该目标**不产出测试计数**，
按既有契约无法进入"回执可复用"集合，因此它只能靠**自身**把重复降到最低。

`typecheck` / `typecheck:strict` 现在带 `--incremental`，程序图缓存在已被 `.gitignore`
覆盖的 `node_modules/.cache/vue-tsc/`（按文件内容与编译选项做键）。

- **实测**（`make verify.frontend.typecheck.strict`）：冷态 23.4s → 热态 **10.3s**。
- **失败闭合验证**（不是"跑过就算"）：热态缓存存在时注入
  `const probe: number = "..."`，该目标**仍然失败**（exit 2，报 `TS2322`）；
  删除该文件后恢复 exit 0。即陈旧程序图**不会**掩盖新诊断。
- 诊断集合、`include` 列表、严格开关**一律未改**；变的只是"从什么状态开始算"。


### 13.8 部署闭环：模块代码未变则不再重跑升级（`3ee08386`）

**现象与度量**：`daily.runtime.published_face.converge` 是每日部署三入口之一，
每次无条件执行 `mod.upgrade smart_core`（约 3 分钟），即使相对上次已验证的收敛
**模块代码一字未改**。

**根因**：该入口把"发布面必须从最新的投影代码冻结"写成了"每次都必须重跑升级"。
前端构建早已有"同 commit 复用回执"（`reused` 字段），部署面却沿用"无条件写"。

**修正（fail-closed 的同码判定，不靠时间戳、不靠文件名）**：

- 本地在**精确候选 revision**（`--expected-sha`）解析每个声明模块的 **git tree oid**
  （`<sha>:addons/<module>` / `<sha>:odoo/addons/<module>`）。tree oid 是目录内容的递归身份，
  两个 revision 报同一 oid 即模块代码逐字节一致；**任一模块解析不出 → 返回 `None` → 不复用**。
- 该 tree id 作为**声明**经 argv 传入远端。远端**不看本地结论**，而是对自己的已部署 tree
  **重新解析**（`git rev-parse --verify HEAD:<base>/<module>`），只有"声明集 == 模块集"
  且"已部署 oid == 声明 oid"**逐条相等**时才跳过升级，否则照常升级。
- 回执新增 `upgrade_mode`（`run` / `reused` / `skipped`）、`module_tree_ids`（全 SHA 的已部署树id）、
  `upgrade_reuse_reason`。
- 本地证据校验新增：声明了模块时 `upgrade_mode` 必须 ∈ {run, reused}；`module_tree_ids` 必须是
  与声明**同集合**的全 SHA；**若远端声称 `reused` 但其 `module_tree_ids` 不等于本地声明的
  `reuse_tree_ids`，则报 `unpublished reuse claim is unproven` 并失败**。
- 复用提示只从**上一份**回执取，且要求该回执 `status/guard_status` 皆 PASS、`remote_root`、
  `database`、`upgrade_modules`、`module_tree_ids` **全等**；任何不满足即给空提示（照常升级）。
- 新增 `--force-upgrade`（`make DAILY_RUNTIME_PUBLISHED_FACE_FORCE_UPGRADE=1`）：代码没变但数据库需
  重建/对齐时的**漂移修复通道**，显式忽略命中回执。

**未放宽任何东西**：升级（可能被复用）**之后**仍然冻结发布面并跑 release gate 守卫；
`mod.upgrade` 的声明（`CODEX_NEED_UPGRADE` / `CODEX_MODULES`）与守卫耦合保持不变；
跳过只发生在"已部署树 == 声明树"这一可被远端独立复算的条件上，**默认永远是重跑**。

**测试**：`make verify.daily.runtime.published_face.converge` **22/22 PASS**
（新增：argv 携带 tree id、无提示时占位、缺 `upgrade_mode` 拒绝、`reused` 无据拒绝 / 诚实 `reused` 通过、
`reuse_hint` 全条件、真仓库 `module_tree_ids` 解析与拒绝、`--force-upgrade` 忽略命中回执）。
新登记检查 `daily_runtime_published_face_converge`（`verify.daily.runtime.published_face.converge`）已写回执。
**L3/L4 实测**（真实部署走一次并确认 `upgrade_mode=reused`）待用户确认后执行——本轮不擅自发起远端写。

### 13.9 运行态回执可复用：声明式权威环境读回（fail-closed）

**现象与度量**：`agent_run_context` 过去对**任何** `kind=runtime` 的检查一律判定
`stale`（原因：`runtime evidence requires authoritative environment readback`），
所以 `daily_acceptance_readback`（只读探针，~25s）以及后续浏览器车道的回执**每轮都要重新取证**。
这是"体系化复用"最大的缺口。

**根因**：账本要求在复用前证明"受管环境身份未变"，但当时**没有任何声明式读回载体**，
只能保守地一律重跑。缺的是"载体"，不是"是否该复用"的判断。

**修正（与 §13.8 同构：便宜的读回跑、昂贵的车道复用）**：

- 检查可以声明一个**权威环境读回**：`"readback": {"artifact": "<path>"}`，路径必须落在被忽略的
  运行时证据区（`.runtime/` 或 `artifacts/`），**不得**是源码/工具路径（否则它会伪装成代码）。
- `dependency_state` 把该 artifact 的 `sha256`（含权限位）并入检查的依赖状态；因此
  **环境变化 → 受管入口重写读回 → 摘要变化 → 回执失效（stale）**，与任何其它输入变化同等对待。
- `evaluate` 只对"声明了 readback 的 runtime 检查"放行复用；**未声明 readback 的 runtime 检查
  仍然永不自动复用**；`run.environment.kind == runtime` 依旧不可复用（保持既有硬约束）。
- **fail-closed**：readback 缺失 → `begin` 直接拒绝（`declared dependency is missing`）；
  读回被重写 / 环境身份变化 → `stale`；声明形状非法（非 `{artifact}`、绝对路径、`..`、越界、
  非运行时证据区、符号链接）→ `resolve_run` 直接拒绝。

**未放宽任何断言**：只新增了"复核用的声明式载体"，没有修改任何产品断言、门禁或回退路径；
未声明的 runtime 车道行为与之前完全一致（一律 stale）。

**实测**：`daily_acceptance_readback` 声明
`artifacts/backend/daily_dev_acceptance_probe.json`（受管只读探针输出）后重跑探针并写回执，
状态由 `stale` → **`reusable`**；`make verify.agent.resume.unit` **40/40 PASS**
（新增 6 个：未声明 readback 不可复用、读回不变可复用、读回变化失效、读回缺失阻断、
越界/源码路径拒绝、声明形状校验）。

**证据卫生纠偏**：复跑探针时暴露了两点——(1) `daily` 剖面对弱口令 `123456` 要求
`SC_ACCEPTANCE_DAILY_CREDENTIAL_CONFIRMATION`（绑定 runId/expiresAt 的 JSON）；
(2) 合同探针账号 `fixture_role_finance` 的口令由 `ACCEPTANCE_CONTRACT_PASSWORD` 提供。
两者都通过既有受管入口满足，**未放宽任何凭据守卫**。

### 13.10 部署闭环复用实跑（日常运行时候选 `a81fad7e`）

按 §13.8 的实施做了一次真实部署（受管入口 `make daily.runtime.candidate.release`，
三项显式确认；未手工拼装任何 Compose/SHA）：

- `daily.runtime.candidate.bundle_sync` PASS：`4b7f9a46` → `a81fad7e`，
  `origin_main_mutated=false`，`deployment_mode=candidate`。
- `daily.runtime.source_revision.align` PASS：`.env.dev` 的 `SC_SOURCE_REVISION` 写入 `a81fad7e`，
  `restarted=true`、`rolled_back=false`，服务端读回 `served.source_revision=a81fad7e`。
- `daily.runtime.published_face.converge` PASS：**首次必然 `upgrade_mode=run`**（上一份回执没有
  `module_tree_ids`，属正确的保守引导），并写回绑定身份
  `module_tree_ids={"smart_core":"1544cbc20706b9fd85c8f98259c71395d1ce663f"}`。

**同码复用的实跑验证**：`daily.runtime.candidate.bundle_sync` 明确拒绝把**同一 SHA** 再同步一次
（`candidate SHA must differ from the daily runtime SHA`），这是防呆而不是缺陷；因此第二段
复用证明需要一个**新的候选 revision**（文档/台账提交即可，不改 `addons/smart_core`）。

**部署带来的正确连带**：服务端 SHA 变化后，`daily_acceptance_readback` 的旧回执（绑定 `4b7f9a46` 的
读回）按机制失效——实测正是如此。按受管顺序恢复：
1. `make daily.runtime.record_identity.resolve`（`CONFIRM_DAILY_RUNTIME_RECORD_IDENTITY=…`，
   `DAILY_RUNTIME_EXPECTED_SHA=a81fad7e…`）刷新 `artifacts/backend/acceptance_record_identity.json`；
2. 重跑 `make verify.daily_dev.acceptance.readonly.probe`：PASS（`served_sha=a81fad7e`，
   `runtime_identity`/`contract` 全 PASS，`errors=[]`）；
3. 写回执后 `daily_acceptance_readback` 回到 `reusable`，台账恢复 `28 reusable / 2 not_run / 0 stale`。


### 13.11 部署闭环复用的第二次实跑：`upgrade_mode=reused` 端到端成立（`51e7cdc0`）

§13.10 只证明了"同码复用"的**拒绝路径**（同 SHA 不可重复同步）。要证明复用**真正生效**，
必须换一个新的候选 revision（`51e7cdc0`，仅文档/台账提交，未改 `addons/smart_core`），
再用同一个受管入口 `make daily.runtime.candidate.release` 部署一次。三项显式确认与
`DAILY_CANDIDATE_EXPECTED_OLD_SHA=a81fad7e…` 未变：

- `daily.runtime.candidate.bundle_sync` PASS：`a81fad7e` → `51e7cdc0`，
  `deployment_mode=candidate`、`origin_main_mutated=false`（`.runtime/final-acceptance/daily-deployed/candidate-bundle-sync.json`）。
- `daily.runtime.source_revision.align` PASS：`.env.dev` 的 `SC_SOURCE_REVISION` 写入 `51e7cdc0`，
  `restarted=true`、`rolled_back=false`，服务端读回 `served.git_sha=51e7cdc0…`
  （`source-revision-align.json`）。
- `daily.runtime.published_face.converge` PASS：**`upgrade_mode="reused"`**，
  `upgrade_reuse_reason="deployed module tree is byte-identical to the last verified upgrade"`，
  `module_upgrade_returncode=0` 且 `guard_status=PASS`；写回 `module_tree_ids={"smart_core":"1544cbc20706b9fd85c8f98259c71395d1ce663f"}`
  与 §13.10 首次 `run` 时**逐字节一致**（`published-face-converge.json`）。
- 发布面仍按契约重冻结：`construction.standard`/`construction.preview` 各 90 条已发布页面，
  `snapshot_version=daily-navigation-standard-51e7cdc0853b`。

**度量**：本轮部署墙钟约 42s，对比 §13.10 首次（`upgrade_mode=run`，含一次 `mod.upgrade smart_core`）
约 185s，省约 143s；省下的正是被复用的 `mod.upgrade`。该墙钟为执行器终端观测（attested），
机器可复算的部分是 `upgrade_mode=reused` 与 `module_tree_ids` 一致。

**复用不放松任何东西**：复用判定要求"声明的模块 git tree oid == 远端已部署 tree oid"；
本地对"声称 reused 但 tree 与声明不符"直接拒绝并回退到运行升级（`verify.daily.runtime.published_face.converge` 22/22）。
发布面在（可能被复用的）升级之后**仍然重新冻结**，并由 release-gate guard 复证。

**部署带来的正确连带（第二次）**：服务端 SHA 再次变化，`daily_acceptance_readback` 旧回执
（绑定 `a81fad7e` 的读回）按机制失效。受管顺序恢复：
1. `make daily.runtime.record_identity.resolve`（`DAILY_RUNTIME_EXPECTED_SHA=51e7cdc0…`）→
   `served_revision=remote_head=51e7cdc0`，刷新 `artifacts/backend/acceptance_record_identity.json`；
2. 重跑 `make verify.daily_dev.acceptance.readonly.probe`：PASS（`served_sha=51e7cdc0`，
   `runtime_identity`/`contract` 全 PASS，`errors=[]`，`nav_required_action_mismatches=[]`）；
3. 写回执后 `daily_acceptance_readback` 回到 `reusable`，台账恢复 `28 reusable / 2 not_run`。

**边界**：本轮为效率批次的部署闭环验证，不改变四态结论——批次验收=效率批次进行中、
主线集成=未做（用户"先不执行进入主线"）、版本发布=日常运行时候选、产品交付=未完成。
`a81fad7e`→`51e7cdc0` 是候选 revision 推进，**不含** `addons/smart_core` 代码变化，
不触发模块升级。

### 13.12 nav_pro 路线权威车道：根因在代码层闭合（2026-10-09 第 13 轮续）

**结论先行**：`navigation.route_authority` **不是自由面，也不是快照面**。它在
`addons/smart_core/delivery/menu_service.py::build_route_authority` 中把**角色契约面**
（`addons/smart_construction_core/core_extension_policy_maps.py::ROLE_SURFACE_OVERRIDES`）**划分**为
"已交付条目"与"显式拒绝条目"（`reason_code=PRODUCT_ENTRY_NOT_RELEASED`）。因此：

- 数量只在**角色被锁定且读取"已发布/可达划分"之后**才确定——与用户既定口径一致
  （"发布锁定机制，不锁定数字"）；
- `config/frontend/authoritative_navigation.json` 是 **2026-07 浏览器审计快照**，**不是**交付面；
- HTTP 探针里 `{finance:10, project_member:7, pm:10, owner:4}`、`contextual_menu_total==100`、
  `denied_total==7` 是**第四套**互不相关的历史标定。

**实测划分（served `51e7cdc0`，`sc_demo`，只读 HTTP）**：

| 角色 | 契约声明 primary | 实际交付 primary | 显式拒绝 `PRODUCT_ENTRY_NOT_RELEASED` | 未记账（静默丢弃） | 交付但不在契约面 |
| --- | --- | --- | --- | --- | --- |
| finance | 45 | 17 | 29 | 1 | 2 |
| pm | 24 | 8 | 15 | 2 | 1 |
| owner | 5 | 4 | 2 | 0 | 1 |
| project_member | 10 | 5 | 2 | 3 | 0 |

**两个残留缺陷（均已定位到属主层，均为 P0 交付引擎语义）**：

1. **静默丢弃（6 条）**：声明了却既不交付、也不记入拒绝的条目。
   `build_route_authority` 在 `visible_by_xmlid` 缺少该菜单时**直接跳过**（`menu_service.py:894-922`），
   不写任何记录。finance 1 / pm 2 / project_member 3。
2. **契约面外交付（4 条）**：原生导航树在 `menu_service.py:985-1010` 会为**任意角色**补入
   不在契约里的 `PRIMARY_NAV` 对——与该处注释"never revive the native menu tree as a
   second product-selection authority"自相矛盾。finance 2（`menu_sc_construction_diary`、
   `menu_sc_project_project`）/ pm 1 / owner 1。

**验收口径修正（非放宽）**：`scripts/verify/nav_pro_01r_route_authority_http.py` 必须从
**版本化角色契约**解析期望，断言**划分不变量**（声明 == 交付 + 显式拒绝；交付 ⊆ 声明），
并保留全部行为断言（admin 泄漏、contextual 可达、403 拒绝、跨公司/跨项目域拒绝、HTTP_500==0）；
**不得**再出现任何 pin 数字。方法：只读诊断 `/tmp/nav_diag{3,4,5,6}.py`。

**边界**：本轮只取证与记账，**未**改动判据、**未**动产品代码；P0 交付引擎修复与探针重写待执行。

### 13.13 关联跳转 403 与列表选择框定位超时：两项验收缺陷闭环（2026-10-10 第 13 轮续）

**结论先行**：用户报告的两项实际验收未通过项，都在**属主层**修复，没有放宽任何断言。

**一、关联跳转返回 403 —— P1 声明层漂移（已修）**

事实链（远程只读证据）：

1. pm 角色契约（`ROLE_SURFACE_OVERRIDES["pm"]`）把关联跳转动作为 751
   `action_construction_contract_income_execution`；
2. 锁定产品契约 `scripts/verify/baselines/formal_business_product_menu_policy_v1.json`
   （生产镜像 `/opt/sce-product/contracts/`，由 `locked_menu_policy_contract.py` 服务）**不包含 751**；
3. 发布面同模型的已发布入口是 `menu_sc_p1_income_contract`(904) / action 578，
   `res_model=construction.contract.income`，tree+form；
4. 运行时 `filter_route_authority_by_publication`（`addons/smart_core/delivery/menu_service.py`）
   因此把 751 记为 `PRODUCT_ENTRY_NOT_RELEASED`，关联跳转没有任何可达目标，前端呈现 403；
5. 同时发现同一动作存在两个上下文载体（action 578/751 与 menu 904/485 混用），违反唯一性。

修复（`c3424962`，P1 声明层对齐，**不是**放宽发布闸门）：pm 块移除 `menu_sc_project_income_contract`，
把 `contextual_action_authorities` 的目标由 751 改为发布面已发布的 578，保留全部
`context_requirements`（company_id/project_id/contract_id）。

**这就是"产品册有、发布没有对齐"的准确表述**：声明面向用户承诺了一个发布闸门从未发布的入口。
产品册（旧用户确认基线 `scripts/verify/baselines/user_confirmed_formal_menu_policy_62.json`，
60 项 released，含 751 + menu 485）与发布基线（90 项）之间存在漂移；按既定口径必须
**修声明对齐发布，而不是放宽发布闸门**。

**二、列表选择框验收定位超时 —— 取证侧未按契约消费（已修）**

车道 `scripts/verify/nav_pro_01r_route_authority_*` 有三处自造推断：

1. 以 `/a/<action_id>` 自造入口，忽略契约条目自带的可消费 `route`（`/a/723?menu_id=438`）。
   前端对无 `menu_id` 的裸 action 路由有既有且**被守卫测试锁定**的 fail-closed 规则
   （`routeAuthority.ts::findRouteAuthority` 只接受 `menu_id===0` 或 `CONTEXTUAL_ROUTE`），
   于是把"未按契约打开"误报成"入口不可达"；
2. 硬编码页面文案（"用户账号与权限"），而契约声明入口名为"人员档案"；
3. 要求治理权限字段在**没有激活其所属章节**前就可见——该表单是章节化懒渲染。

修复（`03393078`）：探针从服务端契约读取入口 `route`/`name`/`model`/`formStructureContract`，
并从治理声明 `addons/smart_core/utils/contract_governance_enterprise_forms.py::permission_fields`
解析权限字段；浏览器车道按契约 route 打开、断言行选择框可用、按契约章节 label 激活后再要求字段。

**按契约能力分层（非放宽）**：`allowed_operation != read` 的可写面**必须**渲染治理声明的权限字段；
`allowed_operation == read` 的只读面只断言记录路由绑定契约 model 且确实渲染了字段——渲染哪些字段
属前端职责，契约不保证字段集合，不作推断。`config_admin` 面为 `write`、`system_admin` 面为 `read`，
两者断言因此不同，均来自契约条目事实。

**三、验证（绑定服务端精确版本）**

- 部署：`make daily.runtime.candidate.release`，`DAILY_CANDIDATE_EXPECTED_SHA=c3424962…`、
  `OLD_SHA=99ac1479…`、`UPGRADE_MODULES=smart_core,smart_construction_core`；
  bundle-sync / source-revision-align / published-face-converge 三项 PASS，服务端
  `source_revision=c3424962e05c31b184718c779b8c6b0e5553cc92`。
- HTTP 探针：`ROLE_CONTRACT_PARTITION=PASS`、`CONTRACT_EXECUTION_CONTEXT_ROUTE=PASS`、`HTTP_500=0`。
- 浏览器旅程：`USER_MANAGEMENT_REACHABLE`、`OLD_ACTION_EXECUTION_AUTHORIZED_DIRECT_REACHABLE`、
  `ORDINARY_USER_ADMIN_DENIAL=PASS`、`CROSS_COMPANY_CONTEXT_DENIAL=PASS`、
  `UNAUTHORIZED_ROUTE_DATA_REQUESTS=0`、`DIRECT_ROUTE_500=0` 全 PASS。
- 收据：`.runtime/agent-runs/DAILY-DEV-MAINLINE-PRODUCT-ACCEPTANCE-CLOSEOUT/browser_login_return_authority.json`
  （passed，16 断言，head=`03393078`，log `.runtime/nav-pro-01/lane-execution.log`
  sha256=`6f8b309c…`）。

**四、边界与遗留**

- 四态：批次验收=进行中 / 主线集成=未做（用户"先不执行进入主线"）/ 版本发布=日常运行时候选 / 产品交付=未完成。
- 仍报告**不修**（属主层另计，P0 交付引擎语义）：`build_route_authority` 的静默丢弃与契约面外交付。
- 待用户裁决：`scripts/verify/product_menu_runtime_closeout_guard.py` 在本分支与 `origin/main` 均失败
  （`missing active=False overlays: menu_sc_project_ledger_group_v2`），与本次改动无关。

### 13.14 菜单收口守卫漂移修复：声明对齐已发布契约（`abdaf3b1`，2026-10-10 第 13 轮续）

**结论先行**：`scripts/verify/product_menu_runtime_closeout_guard.py` 报
`missing active=False overlays: menu_sc_project_ledger_group_v2`（在本分支与 `origin/main` 同时失败）
是**声明陈旧**，不是发布面缺陷。按"修声明对齐发布"的口径修复，未放宽任何断言。

**一、事实链（已独立复核）**

1. `config/product_menu_contract_v1.json` 中 `centers[1] 项目中心 / level_two[1] 项目台账`
   与 `children[0] 项目台账` 均为 `delivery=RELEASED_FOUNDATION`（该契约按 label 声明，不含 xmlid）；
2. 发布基线 `scripts/verify/baselines/formal_business_product_menu_policy_v1.json`
   两个 product 的 `menu_groups[1].menus[2]` 都含已发布条目
   `smart_construction_core.menu_sc_project_project`（label `项目台账`）；
3. 发布导航 `addons/smart_construction_core/views/menu_product_navigation_v2.xml:121`
   把该记录入口挂在容器组 `menu_sc_project_ledger_group_v2` 之下；容器组 inactive 时，
   已发布的子项在原生树里不可达；
4. `Merge PR #594`（`90484d88`）据此把 `views/menu_product_project_wave1.xml:13` 该组改为
   `<field name="active">True</field>`——这是契约裁决，不是回归。

**二、漂移根因**

裁决后，守卫 `HIDDEN_XMLIDS` 与运行时收敛常量
`addons/smart_construction_core/models/support/product_policy_sync.py::LOCKED_TARGET_UNPUBLISHED_MENU_XMLIDS`
仍保留该 xmlid，于是守卫要求一个已不存在的 `active=False` 覆盖，必然失败。

**三、修复（`abdaf3b1`，P1 声明层 + P4 守卫一致性）**

两处同源集合各自移除 `menu_sc_project_ledger_group_v2`，并加注契约理由。
**未放宽**：守卫仍要求其余每一条 `HIDDEN_XMLIDS` 都存在 `active=False` 覆盖、且都出现在锁定集合中
（`missing_overlay` / `missing_policy` 两个方向继续 fail-closed）。

**四、验证（干净 HEAD `abdaf3b1`，收据可复用）**

- `verify.product.menu.runtime_closeout.guard`：PASS（`42 unpublished menu facts are closed`）。
- `verify.product.menu.release_manifest_v2.guard`：PASS（`centers=10 contract_pages=90 accounting_pages=6 total=90`，
  sha256 `bcefc90c…`）。
- `verify.product.menu.contract_v1.guard`：PASS（锁定契约内部一致且与运行态对齐）。
- `verify.frontend.release_navigation_policy.guard`：PASS（`roles=4 released_leaf_identities=88`）。
- `verify.scene.role.surface.consistency.guard`：PASS（`role_count=10 r3_scene_count=22`）。
- `verify.contract.project_ledger_entry_carrier.orm`：PASS（`0 failed, 0 error(s) of 28 tests`）。
- 定向模块测试 `TestProjectLedgerRuntimeContract`：`0 failed, 0 error(s) of 3 tests`。

**五、行为中性说明（为何暂不重跑日常升级）**

`LOCKED_TARGET_UNPUBLISHED_MENU_XMLIDS` 仅在 `product_policy_sync.py:559` 的**锁定基线菜单循环**中消费；
`menu_sc_project_ledger_group_v2` 不是 `formal_business_product_menu_policy_v1.json` 的菜单条目，
因此本次移除对已发布运行面**行为中性**。日常运行时不为此单独重跑升级，留到合并收口的一次刷新。

**六、遗留（登记，不掩盖）**

- `browser_login_return_authority` 收据声明为 `runtime` 但未声明权威环境读回 artifact，
  框架因此判定 `stale`（既有声明机制项，非本轮改动引入）；将在合并收口的日常运行时刷新时
  重跑该车道并补 `readback`。
- `build_route_authority` 静默丢弃 / 契约面外交付（P0 交付引擎语义）仍未修，按顺序进入下一步。

### 13.15 契约声明面闭合与配置中心重挂（`c31db98f`，2026-10-10 第 14 轮）

**结论先行**：原 run 顺序中的第 2 项（P0 交付引擎残留）不是单点问题，而是**两个属主层缺陷**，均已修复且未放宽任何断言：

1. **P0 `smart_core` 交付引擎：声明的 ACTION 面从未闭合。**
   交付引擎此前已闭合声明的 **MENU** 面（`PRODUCT_ENTRY_NOT_VISIBLE`），但
   `contextual_action_authorities` / `admin_action_authorities` 声明的 action 面在既未交付、也未显式拒绝时被**静默丢弃**。
   只读探针（`.runtime/diag/action_authority_closure.json`）证实 `nav_pro_pm` 的
   `action_project_boq_import_wizard` 落在 `silent_actions`，其余 5 个角色为空。
   修法：把 ACTION 面按 MENU 面同一方式闭合——交付或显式拒绝（构建已定义但主体 ACL 不许可 → `PRODUCT_ENTRY_NOT_AUTHORIZED`；
   构建未定义 → `PRODUCT_ENTRY_NOT_DEFINED`）。**未覆盖** ACL、字段权限或合法隐藏规则，**未加**付款/BOQ 等模型特判。
   fixture 与代码一致：`group_sc_role_project_manager` 只隐含 `cost_read`，而 BOQ 导入向导 ACL 仅授予
   `cost_user/cost_manager`，因此拒绝本身**正确**，本次修的是"拒绝必须可观测"。

2. **P1 wave one：配置中心"菜单配置"叶子遗漏重挂。**
   `views/menu_product_configuration_wave1.xml` 把 `表单配置`、`字段管理` 重挂到 `产品配置` 中心，却漏掉了
   `menu_ui_menu_config_policy_business_config`；它仍挂在同一轮被关闭（`active=False`）的
   `menu_sc_lowcode_system_config_group` 之下。
   只读复核：`native_config_app_children` 只返回 `['表单配置']`；`_build_config_node` 要求**每一层**节点自身在
   `visible_ids` 中，因此整棵子树（含"菜单配置"）在原生配置投影里被截断，而角色声明面（`admin_menu_xmlids`）
   与受管配置中心基线仍然声明它 → 声明与交付分叉。
   修法：按同一 wave one 模式重挂到 `menu_sc_business_config_center`。

**一、测试断言对齐（不放宽）**

- `test_role_surface_project_member.test_route_authority_contract_separates_admin_and_contextual_action_only_entries`：
  原断言要求 `action_sc_historical_payment_fact` 必须出现在 `primary_actions`。该菜单是**声明但未发布**的锁定候选条目
  （`product_policy_sync.LOCKED_TARGET_UNPUBLISHED_MENU_XMLIDS` 刻意保持 inactive），因此可采纳结果是**记录在案的拒绝**。
  断言改为与同文件 executive / project-member 两处**完全相同**的契约不变量："交付或显式拒绝，恰好一次"，
  且拒绝分支必须带 `PRODUCT_ENTRY_NOT_VISIBLE`。**未放宽**：静默消失仍会失败。
- `scripts/verify/nav_pro_01r_route_authority_http.py`：新增 action 声明面分区断言（含 `silent_actions` fail-closed）。

**二、验证（候选 `c31db98f`，工作区干净）**

- 定向 ORM：`MODULE=smart_construction_core TEST_TAGS=user_data_boundary test.safe` → **0 failed, 0 error(s) of 25 tests**
  （分支起点为 1 failed + 1 error；基线 `aea2c19b` 为 3 failed + 1 error）。
- 守卫（全部 PASS）：`verify.nav.pro01r.route_authority.unit`、`verify.product.menu.runtime_closeout.guard`、
  `verify.product.menu.contract_v1.guard`、`verify.frontend.release_navigation_policy.guard`、
  `verify.scene.role.surface.consistency.guard`、`verify.product.menu.release_manifest_v2.guard`、
  `verify.frontend.business_entry.evidence_scope.unit`、`verify.product.workbench.wave1.guard`、
  `product_finance_center_wave1_guard.py`、`verify.frontend.typecheck.strict`、
  `verify.contract.project_ledger_entry_carrier.orm`（28 tests）。
- 日志：`.runtime/eff/rec/closeout-20261010/`；收据：`.runtime/agent-runs/DAILY-DEV-MAINLINE-PRODUCT-ACCEPTANCE-CLOSEOUT/`。
- 本地前端产物：`make local.dev.frontend` 重建并在 `127.0.0.1:18081` 服务（入口 `assets/index-B1QjP7q-.js`）。

**三、边界与遗留**

- 四态：批次验收=进行中 / 主线集成=未做（用户"先不执行进入主线"）/ 版本发布=日常运行时候选 / 产品交付=未完成。
- 日常运行态仍为 `c3424962`；`c31db98f` 的后端、菜单与前端改动**尚未部署**，因此浏览器层证据留到一次受管刷新后统一取证。
- 待裁决（登记，不掩盖）：discover 型 `system_admin` 面的原生配置投影交付了 `menu_sc_business_config_workbench`，
  而其 `admin_menu_xmlids` 未声明该条目。需产品裁决：补全声明，或收窄投影。


## 13.16 顺序解决两项未过验收：创建/编辑能力绑定 + 工作台最小证据差额（日常环境一次刷新 + 一次列表复核）

**一、本轮顺序（用户指令"顺序 解决"）**

1. 先补创建/编辑与工作台的最小证据差额；
2. 再统一验证（复用未变证据 + 一次环境刷新 + 一次列表范围复核）。

**二、一次受管环境刷新（唯一一次）**

日常开发服务器 `http://1.95.85.92:18081`（DB `sc_demo`）按受管入口顺序刷新，`c3424962 → 5220db8b`：

- `make daily.runtime.candidate.bundle_sync`：候选分支 bundle 同步（`bundle_base_sha=c3424962`，`origin_main_mutated=false`）。
- `make daily.runtime.source_revision.align`：运行身份声明为 `5220db8b`（改写 `.env.dev` 且自带备份/回滚）。
- `make daily.runtime.published_face.converge`（`DAILY_RUNTIME_PUBLISHED_FACE_UPGRADE_MODULES=smart_core,smart_construction_core`）：
  **升级两个模块**——本次候选同时改了 P0 投影代码（`smart_core/delivery/menu_service.py`）与 P1 视图
  （`menu_product_configuration_wave1.xml`），只重建前端不会验证后端修复。发布面按锁定契约重冻：
  `construction.standard` / `construction.preview` 各 90 个发布菜单，守卫 PASS。
- `make daily.runtime.frontend.build`：按部署 HEAD 重建前端并声明产物指纹。

回读（`.runtime/final-acceptance/daily-deployed/runtime-version-readback.json`）：

```
source_revision      = 5220db8b35a7596a26b930bae9e034c78dce9b8a
frontend_build_sha256= 1f46b03308983f7fe0c5b1d7a48f619af67e59391b40f07a0f19c41b07901b35
entry_asset          = index-vn0WKFxi.js
database             = sc_demo
```

**三、一次列表范围复核（`verify.frontend.business_entry.matrix.incremental`）**

- 先刷新负例闭包快照（`verify.frontend.business_entry.negative_closures`，10 候选 / 1 不适用），
  使拒绝角色计划绑定当前闭包，而不是旧快照。
- 复用判定：`reuse_identity = frontend_build_sha256`，本产物指纹变化 → 89 单元全部 affected；
  完整重走 **89/89**。
- 结果：`ok=true, completeness=complete, problems=0, console_errors=0`；拒绝角色覆盖 **89/89，0 未覆盖**。
- **新增 `collection_capability` 绑定**：76 个 table/kanban 入口把"该入口自己列表契约发布的声明"
  （`effectiveRecordCapabilities.create` / `globalStatus.modelRights.write`）与"渲染面声明"
  （`data-can-create` / `data-can-edit`）逐条绑定，**0 处不一致**；契约未发布的字段一律不断言。
- 唯一异常为 `menu_sc_p1_expense_contract`（支出合同，`hierarchical`）一次 `page.goto(networkidle)` 30s 导航超时；
  按声明理由隔离复跑后 PASS（`hierarchical`，`ready`，50 条，`record_id=3827`，工作流 `[activate, complete, cancel]`），
  定性为**重表面瞬时加载超时，非产品缺陷**。台账最终 89/89 全部 `checked`。

**四、授权探针（同一刷新后的服务身份）**

- `verify.nav.pro01r.route_authority.http`：`ROUTE_AUTHORITY_CONTRACT_VERSION=2.0.0`，
  `ROLE_CONTRACT_PARTITION / USER_MANAGEMENT / ROLE_MANAGEMENT / CONTRACT_EXECUTION_CONTEXT_ROUTE /
  ORDINARY_USER_ADMIN_DENIAL / CROSS_COMPANY_CONTEXT_DENIAL` 全 PASS，`HTTP_500=0`
  （含本轮新增的 action 声明面分区与 `silent_actions` fail-closed 断言）。
- `verify.nav.pro01r.route_authority.browser`：`USER_MANAGEMENT_REACHABLE=true`、`ROLE_MANAGEMENT_REACHABLE=true`、
  `OLD_ACTION_EXECUTION_AUTHORIZED_DIRECT_REACHABLE=true`、`ORDINARY_USER_ADMIN_DENIAL=PASS`、
  `CROSS_COMPANY_CONTEXT_DENIAL=PASS`、`UNAUTHORIZED_ROUTE_DATA_REQUESTS=0`、`DIRECT_ROUTE_500=0`。

**五、证据复用与门禁修正**

- 日常部署链路的单元收据与 `c31db98f` 时记录的十一个守卫/类型检查收据**全部复用**；
  只有 `browser_login_return_authority` 的声明输入（`scripts/verify/nav_pro_01r_route_authority_http.py`）发生漂移，故重跑。
- 两个运行时类检查（`browser_login_return_authority`、`business_entry_matrix_recollect`）补齐
  `readback.artifact`（`.runtime/final-acceptance/daily-deployed/runtime-version-readback.json`），
  否则按运行纪律只能被判 `stale`。
- 新增受管检查 `agent_ledger_consistency_unit`（`verify.agent.ledger.unit`，15 tests），
  并把它**真实读取**的 `.agent` 台账（`context.yaml`、`active-runs.json`、`runs/`、`goals/`）纳入声明输入：
  原先这些路径未声明，导致 run 台账被改写后旧绿灯仍可复用——这是本轮修正的取证依赖缺口。

**六、四态（不夸大）**

批次验收=进行中（本轮两项未过验收已顺序解决）/ 主线集成=未做（未授权进 main）/ 版本发布=日常运行时候选 /
产品交付=未完成。PR 推送、远端门禁与合入仍**必须等待用户显式授权**；独立复核（外部角色）仍待执行。

**七、登记未决（不掩盖）**

- 产品裁决：discover 型 `system_admin` 面的原生配置投影交付了 `menu_sc_business_config_workbench`，
  而其 `admin_menu_xmlids` 未声明该条目。**已于 §13.17 按证据裁决为"设计内已声明交付、非缺陷、无代码改动"**，
  仅余所有者确认（替代裁决的正确责任层为动作/菜单组声明，而非角色锚点清单）。
- 环境 DENY：重建/快照车道仍受两个挂载者阻断，仅作为该车道的结论，绑定实际入口依赖与独立复核依据，
  不泛化为"环境全部通过"；`rendering_detail_state` 的排除沿用既有裁决，不重复证明。
## 13.17 顺序解决：`system_admin` 原生配置面声明缺口裁决（证据绑定，无代码改动）

**一、事实（已复核，非推测）**

- `docs/contract/snapshots/system_init_intent_admin.json`（`system_admin` 面）中，`表单配置`
  （`smart_construction_core.menu_sc_business_config_workbench`）以
  `route_kind=DISCOVERED_PRIMARY_NAV`、`source=delivery_engine.nav`、`required_capability=menu_action_read` 交付；
  `菜单配置`（`menu_ui_menu_config_policy_business_config`）来自 `role_surface.admin_menu_xmlids` 的 `ADMIN_ROUTE`。
- `system_admin` 的 `role_surface.admin_menu_xmlids` 只有 `menu_ui_menu_config_policy_business_config`，
  且 `discover_installed_capabilities=true`、`system_configuration_visible=true`。

**二、裁决：这是设计内的已声明交付，不是未注册交付面，也不是缺陷**

三条独立声明权威共同覆盖该交付：

1. **动作组声明**：`addons/smart_construction_core/views/support/business_config_workbench_views.xml` —
   `action_sc_business_config_workbench.groups_id` 显式包含 `smart_core.group_smart_core_admin`
   （另有 `group_sc_cap_business_config_admin`、`smart_core.group_smart_core_business_config_admin`），
   平台管理员主体本来就对该入口有 ACL 声明。
2. **根作用域投影声明**：`addons/smart_construction_core/core_extension_hook_facts.py` —
   原生配置根为已声明的 `menu_sc_business_config_center`（`smart_core_native_config_root_menu_xmlid`），
   且该叶未列入 `native_config_delivery_excluded_menu_xmlids`；即"配置应用面"的归属是根 + 排除清单，而不是角色锚点清单。
3. **角色面声明**：`core_extension_policy_maps.py` 中 `system_admin.system_configuration_visible=true`，
   由 `smart_core.security.platform_admin.can_manage_system_configuration` 执行。

交付输出本身带有完整来源（`source`、`route_kind`、`entry_target`、`capability_key`、`source_authority`），
说明它来自已声明的 discovery 机制，而不是"无来源的越界交付"。

**三、为什么另两个选项在责任层上是错的**

- **补进 `role_surface.system_admin.admin_menu_xmlids`**：会与已有声明重复，并且会改动 `system_admin` 已发布的导航面，
  进而需要重冻发布面/快照。`admin_menu_xmlids` 在 discover 型面上是**锚点清单**，不是完备枚举；
  引擎的声明面闭合是单向的（声明未交付 = 缺陷），这正是既有设计。责任层不在这里。
- **收紧 `native_config_delivery_excluded_menu_xmlids`**：排除清单是部署级、对所有管理员主体生效的，
  无法只表达 `system_admin` 这一条边界。

**四、结论与唯一待办**

裁决为"设计内行为，无代码改动"，已登记进 run（`round_20261010_declared_delivery_face.open_decision`）。
唯一待办是**所有者确认**：若所有者要求 `表单配置` 必须退出平台管理员面，正确责任层是
**动作/菜单的组声明**（`smart_core.group_smart_core_admin`），而不是角色锚点清单。
## 13.18 冻结准备 + 独立复核：一处门禁漂移与一处无回执主张的处理

**一、冻结准备**

`make ci.delivery.freeze.prepare` PASS，重生成了受内容约束的生成物（契约结构指纹、测试清单、E2E 旅程矩阵、模块依赖图、
复杂度预算、拆分队列、GitHub 远端执行计划、组件接管清单），以 docs/evidence-only 提交落盘。

**二、第一次 Quick 失败（唯一失败点）与其受管修复**

- `make ci.local.quick` → `verify.g1.acceptance.baseline` FAIL：
  `fingerprint drift for config/frontend/acceptance_environments_v1.json: recorded ed8f4e79c12e..., actual 618179c62f5c...`。
- 根因：本分支早前提交改过验收环境配置，但未刷新 G1 基线自指纹（`d106d2dd` 引入）。
- 修复：走受管刷新入口
  `python3 scripts/verify/g1_acceptance_baseline_guard.py --write --baseline-sha 3f424993c9f378aaeedd2f26080545ad37ea3f8e`
  （保留原记录的 G1 切点，仅更新漂移资产的 sha256 与 `collected_at`），随后守卫 PASS。
- 失败后按"收集同层独立失败"要求，把 `ci.local.quick.run` 里 g1 之后的全部目标单独跑完：**全部 PASS**，
  说明该漂移是唯一阻断点。

**三、独立复核（外部只读执行器，非同实现者）**

绑定身份：冻结 HEAD `edc7bcd6`，工作区指纹 digest `8beba69b…c36a42`（8093 条），
baseline `aea2c19b`（`.runtime/delivery-freeze/worktree-fingerprint.json`）。

- **已证实**：P0 声明 ACTION 面闭合（`menu_service.py` 的 declared vs accounted 分区补记显式拒绝，
  未覆盖 ACL/字段权限、无模型特判）；P1 wave-one 叶重挂且停用集未改；验收 summary 字段级主张（89 条、problems 0、
  console 0、76 条声明→渲染绑定 0 不一致）；hierarchical 隔离复跑真 PASS；运行读回身份（5220db8b / 1f46b033…）；
  system_admin 三条声明权威与 `DISCOVERED_PRIMARY_NAV / delivery_engine.nav` 归因；台账 35 个目标均真实存在、输入齐备。
- **阻断性发现（已解决）**：上一轮 `targeted_orm`（`user_data_boundary`，25 tests，0 failed/0 error）**没有回执**，
  且工作区内仅存的三份同标签日志全部为失败且早于修复提交。处理：在冻结候选上**实跑同一受管目标**，
  现得 `0 failed, 0 error(s) of 25 tests`（`sc_dev_demo`），回执
  `.runtime/eff/rec/closeout-20261010/targeted_orm_user_data_boundary.log`。上一轮缺回执的事实已如实登记，不掩盖。
- **记录的限定（不夸大）**：
  1. `20261010-closeout-daily/summary.json` 的 `ok=true` 由 completeness+problems 推导，**内含 1 条 `status=exception`**，
     因此该文件本身不得被读作"89/89 已渲染"；渲染覆盖由隔离复跑 + 证据账本补齐（89 units，88 条来自本次走查 + 1 条来自隔离复跑）。
  2. `negative_closures.json` 无 `served_revision`，属来源/计划输入，不能绑定单一 bundle。
  3. `docs/contract/snapshots/system_init_intent_admin.json` 是冻结 golden（最后内容提交 `c0a6e9e2`），
     记录交付形状，其本身不是"当前候选运行行为"证据。

**四、断言变更披露（非放宽）**

`c31db98f` 同时改了 `addons/smart_construction_core/tests/test_role_surface_project_member.py`：
历史付款事实 / boq 导入的声明型 action 断言，从"必须交付为 `CONTEXTUAL_ROUTE`"改为
"**交付或带 `reason_code` 的显式拒绝，恰好一次**"（与既有 executive / project-member 用例一致）。
交付分支保留原 `route_kind` / `allowed_operation` 断言不变；新增分支只在主体 ACL 不容许所声明操作时可达且必须带显式原因码——
**是"消除静默消失"的收紧，不是承认原先被禁止的交付**。
行为影响：`project_manager` 主体现在收到显式拒绝 `PRODUCT_ENTRY_NOT_AUTHORIZED` 而不是的一条无法执行的入口
（`project.boq.import.wizard` 的 create 只授予 cost_user/cost_manager 能力组，而 project_manager 组只隐含 cost 只读能力），
即前端不再展示该主体无法执行的入口。

**五、状态**

批次验收=进行中 / 主线集成=未做 / 版本发布=日常运行时候选 / 产品交付=未完成。
下一步：在修复后的记录上重新冻结身份 → 跑唯一一次 exact-head `ci.local.quick` → `pr.push.gitee` 并让远端必需检查运行；
合并仍按所有者 CI 通过规则执行。

## 13.19 主线集成收口：PR #634 合并（squash）与产品身份一致性结论（2026-10-10 第 15 轮）

**一、冻结候选与远端门禁**

- 冻结候选 `d1511b51`（唯一一次 exact-head `ci.local.quick` PASS，回执
  `.git/codex/evidence/ci.local.quick/d1511b51aea4e9eb917df410dd8689ee1da1b753.json`）。
- 远端必需检查（绑定 PR head `d1511b51`）：`public_guard`、`merge_policy_gate`、`professional_quality_gate`、
  `frontend_release_gate` **全部 pass**；`make pr.merge.prep PR=634` 复核四项并在该 head 上回报 `merge_policy_gate` commit status。
- 发布前基线身份：PR base == `origin/main` == `f9b03faa`（无基线漂移）；PR head == 冻结候选 == 本地 HEAD。

**二、合并车道与回读**

- 车道选择：**GitHub 是权威远端**，走 `make pr.merge PR=634 EXPECTED_HEAD=d1511b51...`
  （`gh pr merge --squash --match-head-commit`，与 main 上既有 `Merge PR #NNN` 线性历史一致）；
  Gitee 临时集成车道（`publish --purpose integration|ci-only`，明确不把新产品改动合入 main）**未使用**。
- 回读：PR #634 `state=MERGED`，`mergedAt=2026-10-09T19:10:43Z`，merge commit `d690653d`，base main 此前为 `f9b03faa`；
  `git diff --stat d1511b51 d690653d` **为空**（squash 后树完全一致）；`candidate-in-main` 祖先关系不成立属 squash 预期。
  合并不触发产品部署。
- `pr.merge.local_quick_gate` 走 **REUSE** 分支（复用 `d1511b51` 的 exact-head Quick 回执），未重跑套件。

**三、产品身份一致性（本轮复用依据）**

`git diff --stat 5220db8b（日常运行态已服务版本） d1511b51 -- addons/ frontend/ config/ make/ scripts/` **为空**：
合并进主线的内容与日常运行态**已服务并通过用户视角验收的产品内容完全一致**，差异仅在 `docs/`、`.agent/`、证据记录面。
因此本轮**不重跑运行态部署、不重取矩阵证据**（复用依据 = 声明的受影响输入未变 + 产品面零差异），符合"按变更影响复用、不按提交重跑"的规则。

> **勘误（第 17 轮，2026-10-10）**：上文"产品面零差异"只对该轮的目标候选 `d1511b51` 成立，**不适用于其后主线**。
> PR #635（`bb6b6e82`）把 `addons/smart_core/core/form_structure_authority.py` 的契约投影修复带入主线后，
> 运行态 `5220db8b` 与主线 `daecaafc` 之间存在 **1 个生产源差异 + 4 个测试文件差异**，本表述已不再是当前服务态的事实依据。
> 本轮运行态已按受管入口刷新到 `daecaafc`，完整事实、判定与证据见 §13.23。


**四、台账同步方式（按规则，不单独开记账 PR）**

合并后的 run/台账更新提交保留在分支上。按执行规则，纯 `.agent/` + `docs/` 候选会被
`pr.merge.local_quick_gate` 判定为 standalone bookkeeping 并拒绝（CI 对每个冻结提交只产出一份回执，
而记账本身不带来新覆盖），故该记录**随下一项产品候选同行**或按终止退役处理。

**五、保留阻断（单独保留，不泛化）**

环境 DENY（重建/快照车道两个挂载者）仍作为**该车道**的阻断结论登记，绑定实际入口依赖与独立复核依据，不表述为"环境全部通过"。

**六、四态（本轮更新）**

批次验收=完成 / 主线集成=**完成**（PR #634 → `d690653d`）/ 版本发布=日常运行时候选（服务身份 `5220db8b`，产品内容与主线一致）/ 产品交付=**待所有者登录核对判定**。

## 13.20 主线集成收口：PR #635 / #636 / #637（squash）与 nightly 掩盖缺陷闭环（2026-10-10 第 16 轮）

**一、合并车道与回读（均按所有者"CI 通过即合并"规则）**

| PR | 精确 head | 必需检查 | 合并提交 | 备注 |
| --- | --- | --- | --- | --- |
| #635 | — | 全 pass | `bb6b6e82` | nightly 四项红灯修复 |
| #636 | `439cbaa4` | 全 pass | `e2e32ad3` | nightly 第二轮：`smart_construction_scene` 单测导入失败 |
| #637 | `9a000714` | 全 pass | `daecaafc` | 验证体系收口（见 §13.21） |

三次合并均走 `make pr.merge`（`gh pr merge --squash --match-head-commit`），合并前回读
PR head == `EXPECTED_HEAD` == 本地 HEAD，`pr.merge.local_quick_gate` 均走 **REUSE** 分支
（复用对应精确头的 `ci.local.quick` 回执，未重跑套件）。

**二、nightly 掩盖缺陷的端到端证明**

- 修复前：`backend_test_suite.yml` 的按模块步骤在 GitHub `bash -e` 下保留 errexit，
  第一个失败模块即中止整步，后续模块静默跳过，`failed` 累积成死代码——2026-10-09 nightly
  正是以被截断的范围报了绿，掩盖了 `smart_construction_scene` 导入失败。
- 修复后：main `daecaafc` 上重新派发 `38021052567` → **success**，日志出现
  `backend suite executed 14 of 14 planned module run(s); failed=0`（13 个模块库 + 1 个 Python
  单测模块），无 `::error::` 截断注解，无任何非零失败计数。
  （`execution truncated` 字样只出现在 GitHub 回显的脚本源码里，不是运行输出。）

**三、产品身份一致性**

`squash` 后 `daecaafc` 的树与 `9a000714` 的树一致；合并内容对 `addons/`、`frontend/`、`config/`
**零改动**（本轮全部落在 `.github/`、`make/`、`scripts/`、`docs/`、`.agent/`），
故不触发运行态部署，日常运行态服务身份保持不变。

## 13.21 验证体系收口：后端套件不再掩盖失败 + 覆盖登记表 fail-closed（本轮主题，P0/P1/P4）

**一、现象与根因（"验证很多但体系化不够"）**

1. **后端口径造假（P4 CI 工具）**：见 §13.20 二。
2. **证据不成体系（P0/P1 证据机制）**：仓库声明了 155 个 `@tagged` 组（362 条声明），
   其中只有 4 个真正接在受管选择入口上；140 个（274 条声明）从未被任何受管入口引用。
   "手工验过一次"之后不会再跑，且无人可见——这不是"验证很多"，是验证不可复用、不可审计。
3. **死测试**：`scripts/ci/test_backend_test_suite_dispatch_contract.py` 当时零 make/workflow 引用。

**二、修复（各归责任层）**

- `.github/workflows/backend_test_suite.yml`：显式 `set +e`；两个循环各计 `attempted`；
  末尾断言 `attempted == planned_total`，截断即 `failed=1`；打印 `executed N of M`。
- 新增 `scripts/verify/test_coverage_registry_audit.py`：盘点所有 `@tagged` 组与
  `scripts/ci/test_*.py`，未覆盖必须显式 disposition（`gated`/`on-demand`/`unwired` + owner +
  复核期限），**任何新增未接门禁的声明都会让审计失败**（债务只能缩小）。
- 快照 `docs/audit/test_coverage_registry/test_coverage_registry.json`（tracked，审计校验漂移）。
- 单测 `scripts/verify/test_test_coverage_registry_audit.py`（17 例，含多行标签基线、token 边界与负例）。
- 新增 `verify.ci.workflow.contract`（回接死测试），并新增
  `BackendTestSuiteStepIntegrityTest` 断言步骤不能再靠 errexit 掩盖失败。
- 三个新门禁（`verify.guard.registry`、`verify.test.coverage.registry`、`verify.ci.workflow.contract`）
  全部加入 `ci.professional.backend` 与 `ci.professional.backend.shard-verify` 前置，
  由必需检查 `professional_quality_gate` 强制。
- `scripts/verify/registry.yaml` 补 `test_test_coverage_registry_audit.py` 的 `file-consumed`
  处置（`-m unittest` 模块形式只计为文件引用），并刷新 guard_registry 与工程收敛生成物。

**三、实测读数**

- 覆盖登记表：tag 组 155（gated=4 / on-demand=11 / unwired=140），ci 单测脚本 11；
  unwired 全部带 owner 与 2026-12-31 复核期限。
- `verify.guard.registry` PASS（1406 scripts；188/188 unwired dispositioned）；
  `verify.test.coverage.registry` 17 tests OK；`verify.ci.workflow.contract` 6 tests OK；
  `verify.agent.ledger.unit` 15 OK；`ci.local.iteration` PASS；`ci.generated_reports.guard` PASS；
  `ci.delivery.freeze.prepare` PASS。
- 负例（均按预期 FAIL）：注入 `set -euo pipefail`；删除截断断言；篡改覆盖快照。
- 冻结候选 `9a000714` 一次性 exact-head `ci.local.quick` PASS，回执
  `.git/codex/evidence/ci.local.quick/9a000714ee359aca90bccc04cb6bd754f0677d66.json`。

**四、边界（未放宽任何东西）**

未放宽 ACL/字段权限/断言/负例/必需检查；未新增环境、数据库、端口、卷或凭据授权；
未改后端契约、模型、字段或权限语义。登记表只是把既有的"未覆盖"从沉默变为可见债务，
不把任何未接入的组宣称为已通过。

**五、记账方式（按规则，不单独开记账 PR）**

本记录与 `run.json` 更新属纯 `.agent/` + `docs/` 变更，会被 `pr.merge.local_quick_gate`
判定为 standalone bookkeeping 并拒绝，故**随下一项产品候选同行**。

## 13.22 四态（第 16 轮，已被 §13.23 八 取代）

- **批次验收**：完成（验证体系收口三层修复 + 本地全绿 + 负例检出 + exact-head Quick）。
- **主线集成**：**完成**——PR #637 → `daecaafc`（前置 #635 → `bb6b6e82`、#636 → `e2e32ad3`）。
- **版本发布**：未主张（无部署动作；日常运行态服务身份未变）。
- **产品交付**：技术证据就绪，**待所有者登录核对判定**（`http://1.95.85.92:18081/`，`wutao/123456`，库 `sc_demo`）。


## 13.23 运行态对齐主线：squash 合并下主线路不可用 → 受管候选车道刷新 + 投影修复的运行态证实（2026-10-10 第 17 轮）

**一、事实澄清：运行态落后主线一个生产投影修复（修正 §13.19 三 的"产品面零差异"）**

- 刷新前服务态：`sc-root:/opt/projects/repos/sce-product-odoo` 为 detached + clean，`HEAD=5220db8b`，
  `.env.dev` 声明 `SC_SOURCE_REVISION=5220db8b`、`FRONTEND_BUILD_SHA256=1f46b033…1b35`。
- 主线为 `daecaafc`。`git diff --name-only 5220db8b origin/main -- addons/ frontend/ config/` = **5 个文件**，
  `git log` 证明**全部来自 PR #635（`bb6b6e82`）**：
  | 文件 | 变化 | 性质 |
  | --- | --- | --- |
  | `addons/smart_core/core/form_structure_authority.py` | +13/-2 | **生产投影代码** |
  | `addons/smart_core/tests/test_view_orchestrator.py` | +31 | 测试 |
  | `addons/smart_construction_scene/tests/test_action_only_scene_semantic_supply.py` | +12 | 测试 |
  | `frontend/apps/web/scripts/hierarchical_worksheet_load_stage_test.ts` | -2 | 测试脚本 |
  | `frontend/apps/web/scripts/relation_entry_option_limits_test.ts` | -5 | 测试脚本 |
- 该生产差异正是 §13.20 记录的"付款依据"契约投影缺陷修复：`structural_form_declarations()` 多了一个
  `bool(semantic_keys.intersection(row))` 合取，使 identifier-only 行（如 `{"name": …}`）落到结构声明分支，
  报出假 `LEGACY_STRUCTURE_SUPPRESSED_BY_NATIVE_VIEW` 冲突、`compatibilityDependencies` 变为非空；
  289 个已声明契约中唯一受影响 body 是 **id 4 的付款事实 body**。
- 结论：在 `#635` 之前**不能**以"产品面零差异"复用运行态证据；本轮必须先对齐运行态，再谈产品交付收口。

**二、受管刷新：主线路按设计拒绝，改走候选车道（不绕过任何前置）**

- 实测 `git merge-base --is-ancestor 5220db8b daecaafc` **不成立**（#634/#635/#636/#637 均为 squash 合并），
  因此 `daily.runtime.main.bundle_sync` 的前置 `remote old SHA is not an ancestor of the approved SHA` **按设计 BLOCKED**；
  未放宽、未手改远端 ref。
- 在受管 `release/*` 分支（`release/daily-runtime-mainline-daecaafc`，直接绑定主线对象 `daecaafc`）上按既有候选车道执行：
  1. `daily.runtime.candidate.bundle_sync` **PASS** — `old 5220db8b → source daecaafc`、`bundle_base_sha=f9b03faa`、
     `bundle_sha256=aeabe96f…49c6`、`evidence_ref=refs/daily-candidates/release/daily-runtime-mainline-daecaafc`、
     `origin_main_mutated=false`；远端 checkout 后 detached、worktree clean。
  2. `daily.runtime.source_revision.align` **PASS** — `previous_revision 5220db8b → daecaafc`、`env_written=true`、
     `restarted=true`、`rolled_back=false`；回读 `git_sha=daecaafc`。
  3. `daily.runtime.published_face.converge` **PASS** — `sha=daecaafc6da6 products=construction.standard,construction.preview`；
     发布面按新投影重新冻结并复证闸门（投影代码必须先活，快照才不落后一代）。
- 升级判定：`git diff --name-only 5220db8b daecaafc -- '**/__manifest__.py'` 为空（无模型/字段/视图/数据/安全变更）；
  发布面收敛入口按模块树 oid 判定后执行了受管 `mod.upgrade smart_core`（`DAILY_RUNTIME_PUBLISHED_FACE_UPGRADE_MODULES=smart_core`）。
- 代码存活读回（只读）：`sc-root` 上 `git hash-object addons/smart_core/core/form_structure_authority.py`
  = `91a3254b…f600` = `daecaafc:<同路径>` 的 blob，且远端 worktree clean → **修复确已生效于被服务的代码树**。

**三、前端层声明跳过（用输入恒等证明，不用重跑求安心）**

- `git diff --name-only 5220db8b daecaafc -- frontend/apps/web/src frontend/apps/web/index.html
  frontend/apps/web/vite.config.ts frontend/apps/web/tsconfig.json frontend/apps/web/package.json frontend/apps/web/public`
  **为空** → 进入 `frontend/apps/web/dist-dev` 的构建输入字节完全不变；`frontend/` 整目录差异只有两个 `apps/web/scripts/*_test.ts`。
- 故服务态产物指纹 `1f46b033…1b35` 与入口资产 `index-vn0WKFxi.js` 对该修订仍然有效（重建不会改变指纹），
  `daily.runtime.frontend.build` 的**重建被声明跳过**；该入口的离线单测（`verify.daily.runtime.frontend.build`）输入未变，回执 reusable。
- 依据 = "能复用必须先复用" + 已证明的输入恒等；跳过项按规则显式登记，不表述为"通过"。

**四、运行态只读复核（全部 PASS，39 个检查单位）**

- `daily.runtime.record_identity.resolve`（`DAILY_RUNTIME_EXPECTED_SHA=daecaafc`）：PASS；
  `served_revision=daecaafc`、`served_database=sc_demo`、`remote_head=daecaafc`；company a=`21`/b=`22`，
  10 项 target（project / contract / general_contract_carrier / settlement / payment_request /
  payment_request_company_b / payment_execution / journey_request / work_settlement / lifecycle_project）**唯一解析**。
- `verify.daily_dev.acceptance.readonly.probe`（`ACCEPTANCE_TARGET_SHA=daecaafc`、`DB_NAME=sc_demo`、
  base `http://1.95.85.92:18081`、固定开发口令 + ≤10 分钟凭据信封，**未放宽口令 fail-closed 守卫**）：**整体 PASS**
  - `runtime_identity`：served `daecaafc`、db `sc_demo`、frontend `1f46b033…` → PASS。
  - `frontend`：根 200、`assets/index-vn0WKFxi.js` 200。
  - `login`（`wutao`，uid16）：`nav_action_count=89`、`nav_forbidden_label_hits=[]`、`nav_required_path_misses=[]`、
    `nav_required_action_mismatches=[]`、`role_code=business_config_admin`、`system_init_ok=true`。
  - `contract`：**11/11**（布尔全 true）、`errors=[]`；声明账号 `fixture_role_finance` 唯一解析到
    `payment.request` id `36178` / company 21 / menu 550 / action 780。
  - 检查单位 11+11+17 = **39**；`[dev_acceptance_release_probe_schema_guard] PASS`。
- 回执/证据：`.runtime/agent-runs/DAILY-DEV-MAINLINE-PRODUCT-ACCEPTANCE-CLOSEOUT/readonly_probe.log`、
  同目录 `daily_acceptance_readback.json`（受管 begin/record 重录）、
  `artifacts/backend/daily_dev_acceptance_probe.json` 与 `.contract.json`（1,047,240 bytes，sha256 `6a75e201…9ade`）。

**五、受影响产品面的运行态证据（"付款依据"投影，非 handler 诊断替代）**

直接读回服务态封存契约 `artifacts/backend/daily_dev_acceptance_probe.contract.json`
（`ui.contract.v2` / `payment.request` / form / record 36178）：

- `data.formStructureContract.sourceAuthority.governance_source.compatibilityDependencies` = **`[]`**（修复前非空）。
- 全契约文本中 `LEGACY_STRUCTURE_SUPPRESSED_BY_NATIVE_VIEW` 出现 **0 次**。
- 付款事实区块位于 `data.layoutContract.containerTree[1].children[4]`，其 `label`/`string`/`title` 均为 **付款依据**；
  其下 `payment_basis_type` 节点 `readonly=true`、`fieldInfo.invisible=false`、`widget=selection`，
  携带完整 selection 域（`standard_settlement`/`line_settlement`/`material_settlement`/`rental_settlement`/
  `subcontract_settlement`/`contract`/…），**不存在 `visible:false`，也不存在 `auth:"none"`**。

**六、复用面（不重跑已通过项）**

- 前端产物指纹 `1f46b033…1b35` 未变，仍为既有前端业务入口矩阵证据的身份键 → 按"输入未变即复用"不重跑矩阵，
  列表范围 108/108、负例 5/5、运行时错误 0 的既有结论继续有效。
- 服务修订变化只使 `daily_acceptance_readback` 失效（runtime 检查绑定运行态身份），已按受管流程重录；
  复跑 `make agent.run.resume` = **40/40 reusable、outside_scope=[]**。
- 固定开发口令（`wutao/123456`）仅作用于既有日常/隔离 fixture 账号；日常 profile 仍**拒绝已知弱口令**，
  必须提供 ≤10 分钟、字段与 CLI/env 完全一致的凭据信封才可执行只读验收 → 未改变通用登录默认，未放宽任何守卫。

**七、环境 DENY（保留，不泛化）**

- 重建/快照车道的双挂载者 DENY 结论**不变**，仍只作为该车道（重建/快照）的阻断登记；
  `rendering_detail_state` 的排除沿用既有证据与裁决，本轮不重复证明。
- 本轮刷新只走既有受管入口（候选同步 / 源修订声明 / 发布面收敛 / 只读探针），未触碰重建或快照车道，
  因此不构成对该 DENY 的解除，也不表述为"环境全部通过"。

**八、四态（第 17 轮）**

- **批次验收**：完成（验证体系三层修复 + 本轮运行态对齐 + 只读探针 39/39 检查单位 PASS）。
- **主线集成**：完成（PR #635 → `bb6b6e82`、#636 → `e2e32ad3`、#637 → `daecaafc`）。
- **版本发布**：日常运行时候选已对齐主线（服务身份 `daecaafc`，含"付款依据"投影修复）；无正式版本发布主张。
- **产品交付**：技术证据就绪，**待所有者登录核对判定**（`http://1.95.85.92:18081/`，`wutao/123456`，库 `sc_demo`）。

## 13.24 详情收口硬要求闭环：真实关系"点击打开 → 返回原记录 → 标签/动作恢复"重绑当前 served 身份（2026-10-10 第 17 轮续）

**结论先行**：§11.4 与 §12.6.1 要求的详情硬走查（**真实点击**，不得以 handler 诊断替代）
在**当前 served 修订 `daecaafc`**、**受管解析出的 fixture 记录**上已实测 **PASS**，且此前用户报告的
"关联跳转返回 403"在该记录上**不可复现**（3 次关系跳转，`denied_requests=0`）。

**一、为什么这一条此前仍属欠账（不是重复取证）**

- §11.4/§12.6.1 明确的硬要求是"点击打开 → 返回原记录 → 标签/动作恢复"的**真实交互**走查；
  §13.13/§13.16 运行的 `verify.nav.pro01r.route_authority.browser` 断言的是**路由/拒绝权威**
  （`USER_MANAGEMENT_REACHABLE`、`OLD_ACTION_EXECUTION_AUTHORIZED_DIRECT_REACHABLE`、
  `ORDINARY_USER_ADMIN_DENIAL`、`CROSS_COMPANY_CONTEXT_DENIAL`、`HTTP_500=0`），
  它是 `page.goto` 的直达性/拒绝性判定，**不覆盖**"点击关系 → 返回 → 标签/动作恢复"。
- 最近一次关系往返证据绑定 served `24e05cd5`（2026-10-07，`.runtime/final-acceptance/relation-roundtrip-24e05cd5/`），
  本轮把运行态刷新到 `daecaafc`（含 PR #635 的 `form_structure_authority.py` 投影修复）后，
  该证据的服务修订输入已变，按"输入变即失效"必须重绑，不能直接引用。

**二、入口复用（未扩探针框架）**

复用**既有注册资产** `T-ASSET-942`（`scripts/verify/record_relation_roundtrip_acceptance.js`），
不新增探针框架、不改断言口径。该车道是**声明驱动**的：捕获页面自身消费的 `ui.contract.v2`，
只对契约声明可读/可开的关系字段控件做真实点击，校验前端自身发出的 `return_*` 契约，
再回退并断言路径/标题/状态栏/标签/记录动作 `before == after`，全程任一 401/403 或 console 错误即判失败。
视口 `1440x1000`。

记录身份取**受管解析产物** `artifacts/backend/acceptance_record_identity.json`
（`payment.request` / record `36178` / action `780` / menu `550` / company `21`），
主体用该公司的受管契约探测主体 `fixture_role_finance`；**不硬编码记录 id**，不新绑其他记录。

**三、结果（PASS）**

- `declared_entry_count = 18`（契约声明的关系统条目）。
- 页面上 **3 个可见的已声明关系控件全部成功打开**，`denied_requests = 0`、`console_errors = 0`：
  - `company_id` → `/r/res.company/21`（`res.company`）
  - `contract_id` → `/r/construction.contract/13610`（`construction.contract`）
  - `settlement_id` → `/r/sc.settlement.order/3630`（`sc.settlement.order`）
- 往返恢复（`roundtrip.field=company_id`）：`path_restored` / `title_restored` / `statusbar_restored` /
  `tabs_restored` / `actions_restored` **全为 true**，`error_free = true`，`failures = []`。
- 证据：`.runtime/final-acceptance/relation-roundtrip-daecaafc-fixture/20261010T043832/summary.json`
  （6,723 bytes，sha256 `35f7e406…bedc`）。

**四、一次被否定的调用方式（记为绑定事实，非产品缺陷，未放宽断言）**

首次尝试把**同一记录**绑到 `wutao`（其会话默认 company 1）主体，被正确地以
`PROJECT_SCOPE_DENIED` 拒绝（前端落到 `/access-denied?reason=PROJECT_SCOPE_DENIED`，1 次 403 落在 `/api/v1/intent`）。
原因：交付加固 fixture 记录位于 company `21`/`22`，受管契约探测也以 `fixture_role_finance`@company 21 读取同一记录。
即这是**主体/公司绑定事实**，不是缺陷；未放宽 ACL/字段权限/断言，也未改绑记录。

**五、仍未覆盖的边界（不夸大）**

- 本车道覆盖 `1440` 视口；**`390` 移动视口与明暗主题的详情核对不在本车道范围**，
  仍由既有 `verify.frontend.rendering_detail_state.*` 族与既有裁决承载，本轮不重复证明。
- 本车道为受管运行态 **bounded evidence**（注册资产的受管执行），不是新增的台账检查项；
  按既有先例（`daily_dev_user_acceptance_completion_20261006.md` §3.4）以验收产物 + 本文承载。

**六、四态（不夸大）**

批次验收=完成（详情硬走查已在当前 served 身份重绑 PASS）/ 主线集成=完成 / 版本发布=日常运行时候选 /
产品交付=**待所有者登录核对判定**。

## 13.25 本轮收口与新任务就绪契约（2026-10-10 第 17 轮收尾）

**一、本轮收口结果**

- 台账：`make agent.run.resume` = `resolved`，**40/40 声明检查 reusable、0 stale**；唯一曾 stale 的
  `agent_ledger_consistency_unit` 已按受管 begin→run→record 重录（15 tests OK，`goals=93 runs=71`）。
- 产品面：详情硬走查（真实"点击打开 → 返回原记录 → 标签/动作恢复"）已在当前 served `daecaafc`
  重绑 PASS（§13.24）；"付款依据"投影与只读探针 39/39 沿用本轮既有证据（§13.23）。
- 会话卫生：无残留刷新进程、无浏览器残留、无 ssh 端口转发；运行态仍 `daecaafc` / `sc_demo` / `1f46b033…`。

**二、工作区与分支事实（新任务入场依据）**

- 唯一 worktree `/home/lidefend/workspace/sce-backend-odoo`，分支
  `audit/daily-dev-mainline-product-acceptance-closeout-20261009` @ `bff64595`。
- `origin/main`（`daecaafc`）是**本分支祖先**（`git log HEAD..origin/main` 为空），
  `git diff HEAD origin/main` **只触及两份记账文件**（本 run.json + 本迭代文档）。
  即：**本分支 = 主线 + 仅账簿**，下一产品候选可直接在此分支构建，**无需先做分支同步**。
- 两份脏文件**必须随下一产品候选同行**（单独的 `.agent`/`docs` 候选会被判 bookkeeping-only 拒绝）。

**三、新任务登记要求（不得静默继承本 run）**

1. 在 `.agent/goals/` 登记**一个** goal，并建 `.agent/runs/<goal-id>/run.json`；
2. 首个写入动作前，把 `.agent/active-runs.json` 指到本分支；
3. 若新任务属于**另一个可独立验收的产品结果**，先关闭本 run（`completed`/`superseded`，
   并在同一步把 goal 置为终态），否则台账守卫会因"终态 run 残留非终态 goal"报漂移；
   只有新任务属于同一验收结果时才应扩展本 run。

**四、就绪环境与可复用面**

- 运行态：`http://1.95.85.92:18081`，`source_revision=daecaafc`、`database=sc_demo`、
  `frontend_build_sha256=1f46b033…`；固定开发口令 `wutao/123456`（日常只读探针仍需 ≤10 分钟、
  字段与 CLI/env 完全一致的凭据信封）；交付加固 fixture 记录在 company `21`/`22`，
  受管契约探测主体为 `fixture_role_finance`。
- 可复用：前端产物指纹未变 → 业务入口矩阵身份键不变（列表 108/108、负例 5/5 继续有效）；
  详情关系往返已绑当前 served 身份（§13.24）。

**五、有意保留的残留（不清理，避免越权）**

- 本地分支 `release/daily-runtime-mainline-daecaafc`（指向 `daecaafc`，无独有内容）**有意保留**：
  受管清理入口 `scripts/ops/branch_cleanup_safe.sh` 明确拒绝 `release/*`（受保护前缀），
  手工删除属越权操作。
- 重建/快照车道 DENY 仍为**车道级**结论，不泛化；`rendering_detail_state` 排除沿用既有裁决。
- 覆盖登记债：140 个未接线 `@tagged` 组（274 处声明），已登记属主与 2026-12-31 复核期。

**六、四态（收尾）**

批次验收=完成 / 主线集成=完成 / 版本发布=日常运行时候选（服务身份 `daecaafc`）/ 产品交付=**待所有者登录核对判定**。

## 13.26 章节导航与提示块投影复核（2026-10-10 第 18 轮，所有者缺陷报告）

**一、问题陈述（所有者）**

所有者登录日常开发服务器后报告：**「项目表单的章节明显有问题，把提示信息进入章节了」**，并追问
**「违背契约没有发现?」**。本节给出运行态复核结论，不新建台账，并入本 run。

**二、复核身份与工具（受管证据）**

- 运行态：`http://1.95.85.92:18081`，`source_revision=daecaafc6da6c61d92312a464b84468e7d85c486`、
  `database=sc_demo`、`frontend_build_sha256=1f46b033…`（未重建前端）。
- 路由：`/f/project.project/581?menu_id=379&action_id=506`（action 506 / menu 379 / record 581）。
- 契约实取：`.runtime/diag/project-form-section/contract.json`；DOM 探针：
  `dom_probe9.mjs`（导航条目来源）、`dom_probe11.mjs`（提示块几何/视觉）、
  `dom_probe12.mjs`（390 视口）、`dom_probe13.mjs`（声明 class 消费普查）。
  产物：`hint-region.png`、`mobile-390.png`。全部为未跟踪诊断产物，不纳入提交。

**三、结论一：章节导航是契约驱动的（推翻"前端猜出章节"的假设）**

导航恰好 4 条，**全部有契约声明来源**：

| 条目 | key | sourceType | 来源声明 |
| --- | --- | --- | --- |
| 基本信息 | `node:sc_project_information_basic:business-section` | node | `data-sc-anchor="project-basic"` 的 primary group |
| 计划与责任 | `node:sc_project_information_plan:business-section` | node | `data-sc-anchor="project-plan-responsibility"` |
| 责任矩阵 | `node:sc_project_information_responsibility:business-section` | node | `data-sc-anchor="project-responsibility-matrix"` |
| 协作记录 | `surface:activity` | surface | `formStructureContract.surfaces[0]`（title 协作记录 / role activity / contentKind collaboration-panel） |

- 1440 与 390 视口结果一致；390 无 `[data-mobile-section-selector]`。
- **提示块不产生导航条目，也没有任何条目指向它**；`data-sc-navigation-role="subordinate"` 的
  三个 group（项目说明/协作资料/系统追溯）按声明不进主导航。
- 因此"未命名容器被推断成章节条目"的旧假设**不成立**，不再作为修复依据。
- 提示块节点本身也是契约声明：`type=container`、`attributes.class="alert alert-info"`、
  `role=status`，并带**规范化顶层** `modifiers.invisible={kind:field_compare, field:lifecycle_state,
  operator:'!=', value:'draft'}`。可见性由契约 facts + 修饰符 AST 决定，`attributes.invisible`
  只是冗余 trace，不是权威。

**四、结论二：真实违背契约的两点（此前未被任何守卫发现）**

**V1（可见症状根因）— 契约声明的容器布局/展示 fact 没有被渲染器消费。**

- DOM class 普查（`main.sc-native-contract-tree` 全树）：`sc-project-overview`、`d-flex`、
  `justify-content-between`、`align-items-start`、`small`、`text-muted`、`h3`、`alert`、
  `alert-info` **各出现 0 次**。
- `NativeFormTreeRenderer.containerClass()` 只返回 `native-container` / `native-container--<type>`
  与若干 flag，**从不合并 `nodeClassList(node)`**（声明 class 只在 `field`-section 分支第 362 行被合并）。
- 后果：sheet 的 11 个子节点被拍平成 **48 个块级 `<section>`**，其中 **39 个 `data-group-title=""`**；
  概览区的行内布局崩塌成逐词换行（`已有 / 1 / 份合同 / 成本 / 已录入 / 1 / 条`，数值被推到最右），
  草稿提示块渲染成紧贴"基本信息"标题上方的**裸 section 级块**——这正是所有者所说
  「提示信息进入章节」的可见来源。
- 更关键的是：气泡外观仍由**前端按硬编码类名匹配**产出（`isNativeFeedbackContainer` /
  `nativeTextPresentation` 命中 `'alert alert-info'`），即展示语义是前端重新推导的，
  不是从声明的契约 fact 消费的——与"前端除渲染与交互外一切来自契约"的底线不符。

**V2 — 被文档禁止的硬编码区域标签仍在，且守卫看不到。**

- `docs/architecture/form_structure_surface_contract_boundary_v1.md` §Ownership 明确：
  渲染器"must not hardcode a region label, region identity or visibility predicate"；
  P0 `smart_core` "must not name a product capability key"，surface 标题归 P1。
- 实际仍有两处硬编码 `协作记录`：
  `frontend/apps/web/src/pages/contractForm/nativeSectionNavigation.ts` 的
  `legacySurfaceNavigationItems`（label `协作记录` + `sourceIdentity: 'collaboration-panel'`），
  与 `addons/smart_core/handlers/ui_contract_v2.py:93-98` 的
  `FORM_STRUCTURE_DEFAULT_ACTIVITY_SURFACE`。
- 而 `scripts/verify/form_view_native_structure_boundary_guard.py` 的反硬编码断言
  **只 grep `NativeFormTreeRenderer.vue` 一个文件**，对上述两处**结构性不可见**。

**五、为什么此前没被发现（守卫缺口，事实陈述）**

`form_view_native_structure_boundary_guard.py` 的 `_frontend_boundary_checks` 只断言：
章节身份（可见 group + `data-sc-anchor` + 可读标题）、标题隐藏、遍历一致性。
**没有任何断言检查"契约声明的容器布局/展示 fact 是否被消费"**，因此整块声明面被静默丢弃也不会失败。
同类事实：`formStructureContract.sourceSectionTitles` 在本表单混入 **11 个按钮/动作标签**
（项目设置/去补齐资料/审批通过/审批驳回/启动项目/提交立项/查看阶段要求/查看合同/查看成本/查看财务/查看任务）
与 6 个真实章节标题，原因是 `section_titles_from_layout` 把每个非 `field` 节点的 title 都收进来（含 `button`）；
5 个同族 P1 表单有测试断言该字段为空，**本表单没有对应测试**（该字段被投影矩阵标为 `NON_VISUAL`，
当前不驱动渲染，因此记为契约卫生问题而非可见缺陷）。

**六、责任层与修复口径（遵 AGENTS.md 边界）**

- V1：P0 `smart_core` 投影（`layoutContract` 把原生 class 当布局权威导出，未声明渲染器中立的布局）
  + P0 前端通用容器渲染。**不加付款/项目模型特判，不放宽 ACL 或字段权限，不加 `critical` 强制覆盖。**
- V2：P0 `smart_core` 默认 surface 标题 + P0 前端 legacy 导航回退；标题应按文档归 P1 策略。
- 修复方案待所有者裁决（A 推荐 / B）：
  **A**：投影不再把原生 class 当布局权威，改用既有的 `formStructureContract` slots/zones 声明渲染器中立的
  区域布局，渲染器只消费已声明布局，并配"声明面被丢弃即失败"的负例优先守卫；
  **B**：保留原生容器树，让渲染器忠实消费声明 class。
  两者都必须随负例优先守卫一起提交。

**七、未能复现的一点（如实记录，不夸大）**

在受管运行态（record 581，1440 与 390 视口）**没有观察到提示块以章节条目形式出现在导航中**。
若所有者屏幕上确有携带提示文本的导航条目，需要该条目的**精确标签 + URL + 视口**以定位对应面。

**八、四态（不夸大）**

批次验收=完成 / 主线集成=完成 / 版本发布=日常运行时候选（服务身份 `daecaafc`）/
产品交付=**待所有者登录核对判定，且本轮新增 V1/V2 两个未修产品缺陷**。

## 13.27 表单声明面投影修复（V1）+ 区域标签声明收口（V2）+ 守卫机制补齐（2026-10-10 第 18 轮，所有者裁决 A）

**身份**：工作区 HEAD `bff64595` + 显式脏范围（本轮修复未提交，故为 iteration 身份，不得称冻结）。
服务端日常运行态**本轮未变**：仍是主线 `daecaafc` + 上一代前端产物 `1f46b033`，
因此本节任何结论都不绑定修复后的运行态。

**一、V1 根因（已确证，非猜测）**

原生表单 arch 用 CSS class 声明容器展示（`sc-project-overview` / `d-flex` / `justify-content-between` /
`mb-3` / `col-md-6` / `card` / `alert alert-info` …）。投影把这些 class 原样带进
`layoutContract` 的 `attributes`，但**渲染器不消费任何声明展示 token**：`containerClass()` 从不合并它们，
产品样式表也没有实现该词表（DOM 普查 0/9）。声明面被静默丢弃且无任何报错——这正是区域塌成整宽块堆的原因。

**二、修复（各自责任层，未放宽任何断言）**

| 责任层 | 改动 | 说明 |
| --- | --- | --- |
| P0 `smart_core` 投影 | `declared_presentation_tokens()` | 每个声明 class 归入渲染器中立 `styleToken` 并发布到归一化节点；`sc-*` 产品 token、显式布局词表、`o_*/oe_*` 原生结构标记、`btn*` 控件标记分别做出决策；**无法归类的 class 直接 `ValueError` 失败闭合**；`field/button/widget` 豁免（其展示由字段/`actionContract` 面声明） |
| P0 通用渲染器 | `NativeFormTreeRenderer` | 节点类型新增 `styleToken`；`containerClass()`（含容器分支、field-section 分支、静态文本分支）合并 `declaredPresentationTokens(node)`；新增"声明展示词表"样式块实现全部已接受 token；`nativeTextPresentation` 同样消费声明 token |
| P0 surface 声明 | 删除硬编码区域标题 | `nativeSectionNavigation.legacySurfaceNavigationItems()` 删除、`ContractFormDriverHost.vue` legacy 分支与 `'协作记录'` 回退删除、`ObjectTaskPage.vue` legacy 条目与回退删除、`ui_contract_v2.FORM_STRUCTURE_DEFAULT_ACTIVITY_SURFACE` 默认值删除（产品不声明即不出现）。区域可见性改为**仅由声明决定**，运行态数据不再是可见性权威 |

**三、守卫机制补齐（本轮授权范围内的 M1/M2/M3）**

- 新增 `scripts/verify/form_container_presentation_consumption_guard.py`（`make verify.form_container_presentation.guard`，
  已并入 `verify.form_structure.contract` / `verify.form_structure.contract_runtime.audit`）。
  **功能级、负例优先**：证明投影会派生 `styleToken`、对不可归类 class 失败闭合、忽略原生/豁免节点；
  证明渲染器合并声明面且词表内每个 token 都有实现；渲染器两项检查用**变异源码自检**，证明守卫真的会失败。
- 写守卫时立刻抓到真实缺口：词表接受 `g-2`，但渲染器只实现 `.row.g-2`，单独声明的 `g-2` 是空操作 → 已改为通用 `.g-2`。
- M2 闭合：`form_view_native_structure_boundary_guard` 的反硬编码断言从"只 grep 渲染器"扩展到
  `nativeSectionNavigation.ts` / `ContractFormDriverHost.vue` / `ObjectTaskPage.vue`，硬编码区域标签无处可藏。
- M1 部分闭合：`contract_v2_render_authority_matrix` 的 `unclassifiedCount` 改为按产出行派生（出现未归类行即抛错），
  不再写死 0；矩阵 JSON 字节不变，无重生成抖动。
- 运行态交付面校验：`form_structure_contract_runtime_audit` 新增 `presentation_facet_issues()`，
  对**实际交付契约**的每个 `containerTree` 节点重新归类，出现 `presentation_unclassified` / `presentation_dropped`
  即计为边界违规——补上"只比 registry、不比交付契约"的缺口。
- M3（`containerTree` JSON-schema）经复核**不新增**：交付树已由装配器（数组 + owner 绑定）与严格前端解码器
  （容器必填字段、重复 container/widget 身份）校验，再加一层并行 schema 属重复守卫；真正的洞在"消费"，已由新守卫覆盖。

**四、验证结果（第 18 轮，本地）**

- L1：`make ci.local.iteration` PASS（`change_state=dirty`、`coverage=L1_only`、`receipt=none`）。
- L2（受影响非零）：`form_structure_contract_projection.unit` PASS `fields=76 unclassified=0`；
  `form_structure_surface_contract.unit` PASS；`native_section_navigation.unit` PASS
  `authority=7 next_action=3 content_identity=11 active_tracking=11 structure_consumption=7`；
  `contract_v2_render_authority.unit` PASS `fields=327 unclassified=0`；
  `form_container_presentation.guard` PASS `vocabulary=30`；
  `form_view_native_structure_boundary_guard` PASS；`frontend_form_canvas_wide_grid_guard` PASS（含 5 项单测）；
  `typecheck.strict` PASS；`verify.frontend.build` PASS。
- 注册表类：`guard_registry_audit` PASS（1407 脚本，新守卫已被 make 目标引用）；`test_coverage_registry_audit` PASS。
- 影响面：`addons/**/*.xml` 全部 form arch 共 58 个不同 class 全部可归类（**0 个未归类**），
  失败闭合不会打断任何仓库原生视图的契约生成；新样式块用到的全部设计变量均经确认真实存在。

**五、边界（不夸大）**

修复**未提交、未部署**。服务端仍是 `daecaafc` + 旧前端，所有者屏幕仍会看到塌陷。
下一步：提交 → 受管候选车道刷新运行态（bundle sync → source revision align → frontend build → published face converge）
→ 运行态回执 + 交付契约审计（`presentation_unclassified`/`presentation_dropped` 归零）+ 声明词表消费普查
→ 交所有者登录核对（`wutao/123456` / `sc_demo` / `http://1.95.85.92:18081/`）。

**六、四态（第 18 轮）**

批次验收=本轮修复本地通过、**运行态未收口**；主线集成=完成（`daecaafc`）；
版本发布=日常运行时候选 `daecaafc`（未含本轮修复）；产品交付=**待所有者登录核对**。

---

## §13.28 协作区接线守卫改绑「契约声明」权威（第 18 轮补，2026-10-10）

**一、触发**

第 18 轮把协作区可见性改为**只由契约声明驱动**（`hasCollaboration = props.suppressCollaboration ? false : Boolean(collaborationSurface.value)`，
`collaborationSurface = declaredCollaborationSurface(props.surfaces)`）之后，`frontend_scene_component_bridge_guard` 仍把
`resolveCollaborationVisibility` 当作唯一权威（标志体必须逐字等于旧的委派块、宿主必须导入该符号），于是断言与**所有者裁决**
直接冲突而 FAIL。这是守卫口径落后于架构裁决，不是产品缺陷。

**二、改法（改绑 + 退役，不新增框架）**

- 单一权威改绑 `declaredCollaborationSurface`：标志体必须逐字等于「抑制门 + 声明读取」；
  新增一条断言，把中间量 `collaborationSurface` 的 `computed` 体也钉在 `() => declaredCollaborationSurface(props.surfaces)`，
  堵住「标志体不变、把声明读取换成本地常量」的旁路（旧守卫的同类缺口是 `hasCollaborationNode := () => false`）。
- VM 侧新增 `collaboration_surface_authority_failures`：以**整段 body**（含"没有声明就返回 null"）为规范式，
  因为"拒绝未声明的契约"本身就是规则的一部分。
- 退役无消费者的旧规则：`contractRuntimeVm.ts` 删除 `hasCollaborationNode` / `resolveCollaborationVisibility`
  （声明驱动落地后**零生产消费者**）；可执行证明 `contract_form_collaboration_authority_test.ts` 重写为
  **声明读取真值表**（`undefined`/`null`/空表/非表/错误 contentKind/首个命中优先）并保留 node + browser 双域重放；
  守卫内 15 个「节点权威／运行态规则」负例删除，替换为 9 个针对新权威的负例（本地常量、从属区读取、
  任意 contentKind、丢失未声明拒绝、环境探针门控等）。`_COLLABORATION_AUTHORITY_TEST_SHA256` 同步更新。

**三、验证（第 18 轮补，本地）**

- `python3 scripts/verify/frontend_scene_component_bridge_guard.py` PASS `checks=129 collaboration_self_check=259`
- `make verify.frontend.contract_form_collaboration_authority.unit` PASS `cases=58`
- 定向 L2 批次（15 目标）PASS：`form_container_presentation.guard`（vocabulary=30）、
  `form_view.native_structure.boundary_guard`、`view.orchestration_boundary_guard`、`form_view.scope.boundary_guard`、
  `scene_component_bridge.guard`、`scene_component_bridge.unit`(cases=38)、
  `form_structure_surface_contract.unit`、`native_section_navigation.unit`(authority=7…structure_consumption=7)、
  `contract_v2_render_authority.unit`(fields=327 unclassified=0)、`contract_v2_runtime_policy.unit`(cases=6 fields=23)、
  `canonical_form_presenter.unit`(cases=177)、`native_collaboration_presentation.unit`、
  `native_form_structure_responsibility.unit`(cases=12)、`form_structure_contract_projection.unit`(fields=76 unclassified=0)、
  `form_canvas_layout.guard`（wide grid 5 单测 + 守卫）
- `make verify.frontend.typecheck.strict` PASS（RC=0）
- **真实文件变异注入**（证明守卫绑的是产品而非夹具）：把宿主标志体换成 `Boolean(props.showCollaborationPanel)`
  → 守卫 FAIL（标志体断言）；把 `collaborationSurface` 的 `computed` 换成本地字面量
  → 守卫 FAIL（声明读取断言）。两次均已还原，还原后守卫 PASS、文件与受审版本逐字节一致。

**四、既有阻断（与本轮无关，单独保留）**

`make verify.form_structure.contract` 当前**无法运行**：其成员 `verify.user_form.preference.boundary_guard`
要求 `addons/smart_construction_custom/models/user_preferences.py`，而该路径在本分支 **HEAD 中也不存在**
（`git cat-file -e HEAD:<path>` 失败，`addons/smart_construction_custom*` 目录不存在）。
这是注册表/守卫与其依赖层脱节，归属该守卫的所有者；本轮只把它记为**聚合目标不可用的既有阻断**，
不改其依赖、不放宽断言、也不把本轮新守卫的通过说成"聚合门禁通过"。

**五、边界（不夸大）**

本轮改动**未提交、未部署**；服务端仍是 `daecaafc` + 旧前端产物，所有者屏幕仍会看到塌陷的概览区与提示块。
下一步：提交 → 受管候选车道刷新运行态 → 运行态回执 + 交付契约审计（`presentation_unclassified`/`presentation_dropped` 归零）
→ 交所有者登录核对（`wutao/123456` / `sc_demo` / `http://1.95.85.92:18081/`）。

---

## 第 19 轮：声明式取值域收敛为唯一权威（契约官方模板口径）

提交：`514c4c11`（本分支，未 push）。上一轮为 `1066b422`。

**一、问题定性**

上一轮修的是「声明式修饰符必须按契约官方模板在同一取值域解析」的**一个消费者**。
本轮按所有者要求做**系统性**检查，确认该缺陷类别在系统里还有第二处实现：

- 契约投影路径 `resolveContractV2ModifierValues`：快照（`mainData`，空则 `primaryDataSource`）∪ 实时值，
  **实时值仅在「表单确实持有该键且取值已定义」时胜出**；
- 原生布局路径 `resolveNativeModifierFieldValue`：`hasOwnProperty(formData, name) ? formData[name] : mainData[name]`，
  **持有键即胜出，不判空**。

两条路径对「表单持有键但取值未定义」给出不同答案，同一声明在渲染侧与执行侧可能得出不同结论 ——
这正是「声明条件被静默反转、按钮可见性出错」的类别根因。此外 `store.ts` 的注释声称二者一致，
而第二处实现并不满足该断言，属于"文档声明了不存在的同源"。

**二、修复（唯一权威，不新增特判）**

- `app/modifierEngine.ts` 新增 `resolveDeclaredModifierFieldValue(snapshot, live, field)` 作为**取值域唯一规则**：
  实时值仅在表单持有该键且取值有定义时胜出，否则由契约快照回答。
- `app/contracts/v2/store.ts`：`resolveContractV2ModifierValues` 改为消费该规则；同时**移除自身的第二次判空**
  （只保留「快照未声明该键时不要把 undefined 实体化」这一存在性问题），使结果由规则单点决定。
- `pages/contractForm/nativeLayoutUtils.ts`：**删除**本地实现，改为再导出引擎权威；
  `pages/contractForm/useRecordFormLayout.ts` 调用点改用同一函数。
- 无业务模型特判，未触碰 ACL、字段权限或合法隐藏规则。

**三、锁定与负例先行**

- `scripts/verify/modifiers_runtime_guard.py`（已在 `verify.frontend.quick.gate` 内）由"标记型"升级为**结构型**：
  要求引擎规则标记、**禁止**原生布局再次出现本地实现、要求再导出、要求消费点走权威函数。
- `canonical_form_presenter_test.ts` 新增锁定用例（`count=7`）。
- **负例（先证基线正常，再证注入被检出）**：
  1. 把引擎规则退回"持有键即胜出"→ 新断言失败，报错为
     `an owned-but-undefined live entry cannot shadow the contract snapshot a declaration depends on`（实际 undefined / 预期 2）；
  2. 在 `nativeLayoutUtils` 重新植入本地实现 → 门禁失败，报错为
     `engine missing marker: live[name] !== undefined` 与
     `nativeLayoutUtils defines its own modifier value-resolution rule instead of consuming resolveDeclaredModifierFieldValue`。
  两次注入均已还原并复跑绿。

**四、验证**

- 定向：`modifiers_runtime.guard` PASS；`canonical_form_presenter.unit` PASS（177 + count=7）；
  `contract_header_action.unit` PASS（含 real builder chain）；`native_form_action_presentation.unit` PASS；
  `native_form_structure_responsibility.unit` PASS cases=12；`form_structure_contract_projection.unit` PASS fields=76 unclassified=0；
  `standard_form_composition.unit` PASS 121 cases；`typecheck.strict` PASS；`ci.local.iteration` PASS `change_state=clean coverage=L1_only`。
- 运行态审计（`verify.form_structure.contract_runtime.audit` 运行时主体，在 `sc-root` 受管容器
  `sc-backend-odoo-dev-odoo-1` / `sc_demo` 上执行，报告写 `/tmp` 以保持被服务树干净）：
  本轮归属的四个口径**全部为 0** —— `presentation_unclassified=0`、`presentation_dropped=0`、
  `declared_action_verdict_missing=0`、`declared_action_verdict_incomplete=0`、`contract_error=0`。
- 受管车道（提交后按序）：`candidate.bundle_sync` PASS（`bundle_sha256=c325ca16…`，`old_sha=1066b422`）→
  `source_revision.align` PASS（服务态 `source_revision=514c4c11`）→ `frontend.build` PASS
  （重建，指纹 `bc5a0cac…`，入口 `index-BpKZqOGC.js`）。
- 声明驱动表单探针在**新 bundle** 上重跑 1440/390 × 明/暗四态：`verdict=PASS failures=[]`，
  `tree=1 driverError=0 pageErrors=[]`；声明可见布局按钮 6/6 各 1、声明隐藏 5/5 各 0、声明章节标题 6/6 各 1、
  声明类名普查无 0、提示块作为声明 alert 呈现。
- **published face 判定（用证据而非假设）**：`daily.runtime.published_face.converge` 本轮**不重跑**。
  最后一次收敛凭据绑定 `expected_sha=5c828da2`（`guard_status=PASS`，90/90 精确匹配，
  `snapshot_version=daily-navigation-*-5c828da2f8d0`），而 `git diff --name-only 5c828da2..514c4c11`
  只涉及前端源码、前端测试与一个 verify 守卫 —— 无 `addons/`、无菜单/契约数据 ——
  故 `1066b422` 与 `514c4c11` 对锁定契约与已发布产品面无改动。

**五、未归因基线（不当作通过，也不当作失败）**

同一次运行态审计的**广口径读数**首次记录：163/163 模型 `contract_needs_attention`、
`boundary_ok 5 / boundary_violation 158`、`missing_group_semantics=163`、`missing_contract_notebook=82`、
`missing_contract_page=82`、`formStructureContract.slots is required`=60、`projects field outside structure`=2024 处。
该审计**设计上恒返回 0**，且此代际无更早同审计记录，因此这是**首读基线**，不是回归结论，
也**不能**作为"环境全部通过"或"产品面已达标"的依据；其归属层（投影责任 / 审计期望 / 真实产品债）
需单独立项判定。报告：`.runtime/final-acceptance/daily-deployed/form_structure_contract_runtime_audit_1066b422.json`。

**六、既有阻断（与本轮无关，单独保留）**

`make verify.form_structure.contract` / `verify.form_structure.contract_runtime.audit` 的**聚合目标**仍不可用：
成员 `verify.user_form.preference.boundary_guard` 要求 `addons/smart_construction_custom/models/user_preferences.py`，
该路径在**本分支与 `origin/main` 均不存在**（`git cat-file -e origin/main:<path>` 失败）。
属注册表/守卫与其依赖层脱节，归属该守卫所有者；本轮只按目标逐条报告，未改其依赖、未放宽断言。

**七、边界**

工程侧已在 `514c4c11` 闭合并已服务（`source_revision=514c4c11`，`frontend_build_sha256=bc5a0cac…`）；
本轮**未 push**、未合并、未标记整体目标完成。剩余唯一开放项为**所有者登录核对**
（`wutao/123456`、`sc_demo`、`http://1.95.85.92:18081/`，
`/f/project.project/581?menu_id=379&action_id=506`）。

## 第 20 轮：运行态审计「未归因基线」的归属层定性 + 守卫路径口径债务登记

提交：仅台账/文档（本分支，未 push）。上一产品提交仍为 `514c4c11`；本轮**不改代码、不放宽断言、不重跑矩阵**。
取证方式：受管远端 `sc-root:/opt/projects/repos/sce-product-odoo`（`514c4c11`，工作区干净）、
项目 `sc-backend-odoo-dev`、库 `sc_demo`，**只读** odoo shell，对全部 163 个模型重建契约并取样。

**一、结论摘要（三分类，互不混淆）**

| 读数 | 归属层 | 性质 |
| --- | --- | --- |
| `slots is required`=60 | **P0 `smart_core`**（投影 vs 运行态校验自相矛盾） | 真实契约自洽缺口 |
| `layout projects field outside structure`=2024 处 / 158 模型 | **P0 `smart_core` 投影字段域分裂** | 真实契约自洽缺口 |
| `missing_group_semantics`=163 | **P4 验证工具**（`scripts/verify/…audit.py` 判定谓词缺陷） | 工具口径债，非产品债 |
| `missing_contract_notebook/page`=82 | **待单独判定**（审计期望 vs 每模型布局） | 未定性，不引用 |
| `missing_collaboration_runtime/attachment/timeline`=3 | 待单独判定 | 未定性，不引用 |

本轮本批**自有的两个面**（声明式容器呈现、声明式原生动作裁决）在两口径下均为 0，
与 `514c4c11` 的运行态契约审计一致；上述读数**都不是本批引入的回归**。

**二、B1 `slots is required`=60 —— P0 同层自相矛盾（已定论）**

- 精确对应：163 个模型中，**恰好 60 个** 满足 `layoutPolicy=container_tree_authority` ∧
  `formStructureAuthority=native_authority` ∧ `slots=[]`；其余 84 个为 `native_authority`（普通分支，slots>0）、
  19 个为 `overview_then_task_slots`（`entry_semantic_surface`，slots>0）。**0 例错配**。
- 生产者：`addons/smart_core/handlers/ui_contract_v2.py:2687` 的 `native_authority` 短路分支，
  **按其自身声明**（`layoutPolicy: container_tree_authority`、注释「Shared native form owns structure」）
  有意返回 `"slots": []`、`"fieldRoles": {}`。
- 校验者：`addons/smart_core/core/unified_page_contract_v2_runtime.py:444-446`
  **无条件**要求 `slots` 非空，**不读 `layoutPolicy`**。
- 因而这是**同一层（P0）两个组件对同一契约的相互否定**，不是 P1/P2 数据问题，也不是审计工具问题。
- 两个方向（均 P0，均无业务特判，需所有者裁决其一）：
  (a) 校验侧尊重已声明的 `layoutPolicy`（当结构声明「容器树/原生权威」时不要求 slots）；
  (b) 投影侧在该分支也发布最小 slot 集。**不得用放宽断言或前端兜底来掩盖。**

**三、B2 `field outside structure` —— P0 投影字段域分裂（已定论）**

- `boundary_issues` 的 2024 处 = 审计独立列（`layout_outside_structure`，583 处 / 98 个有 slot 的模型）
  **加上** 60 个无 slot 模型的全量布局字段（每字段都被判越界）。两者同源，只是无-slot 模型把整个布局都算作越界。
- 机制：**两套互不相同的字段域**被同一契约同时发布 ——
  结构面 slot 字段域来自业务办理 profile（`form_structure_common_fields` / `detail_fields` / `amount_fields` / `date_fields`），
  布局面字段域来自被投影的原生表单 arch（叠加 P1 策略章节）。
- 运行态证据（越界字段词频）：`source_created_by`/`source_created_at`（原生追溯字段）、`active`、
  `reject_reason`、`sequence`、`status`、`manager_id`、`company_id`、`currency_id`、`project_id`、`note`、`description`
  —— 均为**原生 arch / 基础 / 审批字段**，不属于 P1 trace 章节独有内容；因此**P1 不是责任层**。
- 责任层：**P0 `smart_core` 投影**。运行态不变式「结构必须覆盖其所治理的布局」要求投影
  **从同一被投影布局派生 slot 字段域**（或在不自洽时 fail-closed），而不是并行读第二份 profile 列表。
  与所有者「除渲染与交互外，前端不得自行判断；契约必须自洽」的架构要求同源。

**四、B3 `missing_group_semantics`=163 —— P4 审计工具判定谓词缺陷（已定论，非产品债）**

- 确定性反例（可直接复现）：`is_unlabeled_group({"containerType":"group","containerId":"group_basic_info","title":"基本信息"})`
  返回 **True**。根因：谓词内 `generic = {"", node_type(node)}` 字面量**含空串**，而任意节点的标签集合
  `{title,label,string,semanticTitle}` 对缺失键恒含 `""`，故 `bool(labels & generic)` **恒真**；
  唯有携带非技术型 `semanticTitle` 的节点才能逃逸。→ 一个**明显已命名**的分组被判为未命名。
- 运行态规模（996 个 group 节点 / 163 模型）：该谓词对 **163/163** 模型判定「语义分组为 0」，
  其中 **141/163** 模型实际含已命名分组（例：`construction.contract` 6 个分组中 3 个为
  「金额概览 / 审批信息 / 录入信息」，仍被全部计为未命名）。
- 修正谓词后仍会命中 **158/163**（22 个模型的原生布局只产生**无标签结构包裹分组**），仅 5 个模型转为干净
  ——因为 `group_count` 统计的是**全部结构分组节点**，而非声明语义分组。
  故该指标在修正后仍需对「结构包裹分组是否计入」做口径裁决，**当前形态不承载产品信号**。
- 后果：头条读数「163/163 `contract_needs_attention`」由此指标主导（63 个模型**唯一** gap 即此项），
  **不得**被引用为产品发现。按政策**不擅自放宽断言**，登记为工具口径债并附反例与修正建议。

**五、B4/B5 未定性项（登记，不引用）**

`missing_contract_notebook=82`/`missing_contract_page=82`（43 个 slots-required + 32 个 outside + 4 个 boundary_ok + 3）
与 `missing_collaboration_runtime/attachment_contract/timeline=3` 各 3 例，属「审计期望 vs 每模型布局」，
需各自归属层判定后方可引用。

**六、事实 A：守卫路径口径债务（登记，不改门禁）**

`make verify.form_structure.contract` 的成员 `verify.user_form.preference.boundary_guard` 硬编码
`ROOT/addons/smart_construction_custom/models/user_preferences.py` 并直接 `read_text`，而
**`addons/` 下无该模块、`git log --all -- addons/smart_construction_custom` 为空**（从未在本仓库存在）；
该模块是**仓库边界外的客户定制 addon**，运行态挂载并已安装（受管守卫
`scripts/verify/daily_dev_customer_addons_runtime_guard.py` 即按运行态校验其存在）。
本地实测：`FileNotFoundError`。因此聚合目标在本仓库内**不可能通过**。
本轮只按目标逐条报告，**未改其依赖、未放宽断言**；归属该守卫所有者。

**七、环境 DENY（单独保留，不泛化）**

本结论仅作为**重建/快照车道**的阻断依据，绑定实际入口依赖与独立复核；不得据此宣称「环境全部通过」。
`rendering_detail_state` 的排除沿用既有证据与裁决，不重复证明。

**八、证据与边界**

- 审计报告：`.runtime/final-acceptance/daily-deployed/form_structure_contract_runtime_audit_1066b422.json`
- 只读归属扫描（本轮新增，供复核）：
  `.runtime/agent-runs/DAILY-DEV-MAINLINE-PRODUCT-ACCEPTANCE-CLOSEOUT/form_structure_runtime_audit_baseline_attribution/`
  （`attribution_summary.json`、`contract_scan_163.json`、`group_nodes_scan_163.json`、`probe_sources/`）
- 边界：工程侧仍在 `514c4c11` 闭合且已服务；本轮**未 push**、未合并、未标记整体目标完成。
  唯一开放的产品交付项仍为**所有者登录核对**（`wutao/123456`、`sc_demo`、`http://1.95.85.92:18081/`，
  `/f/project.project/581?menu_id=379&action_id=506`）。B1/B2 的修复**不在本轮**，需所有者对方向 (a)/(b) 与立项裁决后再动。

## 第 21 轮：更正 B3 定性 —— `semanticTitle` 通道「有消费端、无生产端」+ B4/B5 定性

提交：仅台账/文档（本分支，未 push）。**本轮修正第 20 轮的一处不完整结论**，并补齐 B4/B5。
取证：静态代码事实 + git 历史 + 既有运行态审计报告与只读扫描（不重跑矩阵、不改代码）。

**一、更正：第 20 轮把 B3 定性为「纯 P4 工具缺陷」是**不完整**的**

第 20 轮只证明了审计谓词本身有 bug（该结论仍然成立），但漏掉了让它**恒为真**的真正上游原因。
本轮查清：`missing_group_semantics`=163 由**两个独立缺陷叠加**产生，其中一个是 **P0 契约生产端缺口**。

**二、B3a（P0，真实契约缺口）：`semanticTitle` 有消费端、无生产端**

- 生产端：`addons/smart_core/core/unified_page_contract_v2_assembler.py:2113`
  `_apply_semantic_container_annotation()` 会写入 `node["semanticTitle"]` 并打上
  `sourceAuthority.runtime_carrier = "business_form_semantic_label_standardizer"`。
- 但其唯一调用者 `_standardize_form_container_semantics()`（同文件 `:2161`）**在生产代码中没有任何调用点**：
  `grep -rn "_standardize_form_container_semantics" addons/` 只命中定义本身；
  仅两个 verify 守卫直接调用它（`scripts/verify/form_view_native_structure_boundary_guard.py:127`、
  `scripts/verify/form_structure_contract_standardizer_guard.py:184/223/255/290`）。
- 历史：调用点在 WIP 提交 `2ec2e2df`（"在途工作，非完成态"）中被**删除**
  （`-    _standardize_form_container_semantics(container_tree, model=model, view_type=view_type, source=source)`），
  同时引入 `_apply_form_structure_roles_to_tree`（`:2551`）。但后者只写 `formStructureRole`，
  **从不写 `semanticTitle`** —— 它是补充机制，不是等价替换。
- 消费端（前端确实在读它，因此这不是无害死代码）：
  - `frontend/apps/web/src/pages/contractForm/nativeBusinessSection.ts:96`：章节标题权威序为
    锚点身份 → 原生 `title/string/label` → `semanticTitle`；文件注释明确写
    "the governed form-structure `semanticTitle` written by the backend semantic standardizer"，
    并声明"渲染器无权发明标题；无契约署名标题则不渲染标题"。
  - `frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue:892`；
    契约 schema 也声明该键 `frontend/apps/web/src/app/contracts/v2/schema.ts:737`。
  → **前端在等契约署名，后端永不署名**：无原生标题的分组因此渲染为**无标题**，
    而标准化器本应为它们生成语义标题。
- 后果链：标准化器未接线 → 出厂契约中 `semanticTitle` 恒缺失 →
  审计 `semantic_group_count` / `projected_semantic_group_models` **结构性恒为 0** →
  `missing_group_semantics` 饱和于 163/163。只读扫描证实：163 模型、996 个分组节点，
  `semanticTitle` 全为 null（含 `construction.contract` 的「金额概览/审批信息/录入信息」等已命名分组）。

**三、B3b（P4 工具）：审计谓词 `""` 缺陷（第 20 轮已证，保留）**

`scripts/verify/form_structure_contract_runtime_audit.py:299` 的 `is_unlabeled_group()` 中
`generic = {"", node_type(node)}` 含空串，而节点的标签集合对缺失键恒含 `""`，故 `bool(labels & generic)` 恒真。
确定性反例仍成立。**即使 B3a 修复，本 bug 也会继续误报只带 `title` 的分组**，故仍需修。

**四、B3c（P4 工具）：审计指标引用了不存在的载体名**

`scripts/verify/form_structure_contract_runtime_audit.py:419` 统计 `runtime_carrier == "business_form_default_tab_standardizer"`
的节点，但该字符串**在全仓库（除审计脚本外）不存在**（`grep -rn default_tab_standardizer` 仅命中审计脚本）；
真实的分页签标准化器 `_standardize_business_form_default_tabs` **不写任何 `runtime_carrier`**。
故 `projected_notebook_models` 结构性恒为 0。

**五、B3d（P4 守卫盲点）：守卫无法发现其对象未被接线**

`verify.form_structure_contract_standardizer_guard` 通过，是因为它在**合成 fixture 上直接调用**该函数验证其行为，
**没有任何"该函数是否被生产代码接线"的断言**。这正是所有者反复指出的类别：
"守卫都没有发现"。同类盲点也存在于 `form_view_native_structure_boundary_guard`。

**六、B4 定性：`missing_contract_notebook/page`=82 —— 审计期望 vs 每模型原生结构（非产品债）**

82 个命中模型的 `notebook_count` 与 `page_count` **全部为 0**，而另外 81 个模型**有** notebook；
分页签标准化器仅在有原生 notebook 时补页签（守卫断言 `project.task should not receive generic tabs when its
runtime contract has no native notebook`）。故这是"是否要求每个业务表单都必须有契约 notebook"的**口径问题**，
不是一致性的产品缺陷。需口径裁决后方可引用。

**七、B5 定性：三项协作契约缺失=3 —— 同名非 chatter 表面（非产品债）**

3 个模型为 `sc.company.project.refund.workspace`、`sc.current.account.workspace`、`sc.team.loan.deduction.workspace`，
`native_chatter=false`、`attachments_enabled=false`、`timeline_enabled=false` —— 均为无 chatter 的 **workspace 表面**。
审计期望所有业务表单都有协作契约，与这 3 个表面的形态不符。同样属口径问题，需裁决。

**八、结论归并（P0 三项 / P4 三项 / 口径两项 / 守卫一项）**

| 项 | 层 | 性质 | 待办 |
| --- | --- | --- | --- |
| B1 `slots is required`=60 | P0 `smart_core` | 投影与校验自相矛盾 | 所有者裁决 (a) 校验尊重 `layoutPolicy` / (b) 投影发布最小 slot |
| B2 `field outside structure` | P0 `smart_core` | 结构字段域与布局字段域分裂 | 立项目：由被投影布局派生 slot 字段域 |
| **B3a `semanticTitle` 无生产端** | **P0 `smart_core`** | **契约署名通道缺生产端（前端在消费）** | 所有者裁决：重新接线标准化器 / 改由结构契约 slot 标题署名绑定 |
| B3b 审计谓词 `""` | P4 工具 | 判定缺陷 | 修谓词 + 回归用例 |
| B3c 载体名不存在 | P4 工具 | 指标恒 0 | 修正载体名或删除死指标 |
| B3d 守卫盲点 | P4 守卫 | 无法发现未接线 | 增加"生产接线"断言 |
| B4 notebook/page=82 | 口径 | 审计期望 vs 原生结构 | 口径裁决 |
| B5 协作=3 | 口径 | 审计期望 vs 非 chatter 表面 | 口径裁决 |
| 事实 A 守卫路径 | P4 守卫 | 依赖仓库边界外模块 | 既有登记 |

**九、边界**

工程侧仍在 `514c4c11` 闭合且已服务；本轮**未改任何产品代码**（B1/B2/B3a 均属 P0 契约行为变更，
需所有者对方向裁决），**未 push**、未合并、未标记整体目标完成。
唯一开放的产品交付项仍为**所有者登录核对**（`wutao/123456`、`sc_demo`、`http://1.95.85.92:18081/`，
`/f/project.project/581?menu_id=379&action_id=506`）。

---

## 第 22 轮（2026-10-10）：契约署名章节标题通道补回生产端（B3a 修复 + B3b/c/d 工具收口）

**一、本轮定性（承接第 21 轮，B3a 方向已由证据确定，非取舍）**

第 21 轮把 B3a 列为"需所有者裁决方向"。本轮先取决定性证据再动手：

- `git show 2ec2e2df`（该提交自述"contract-spec-v0.1 在途工作，**非完成态**"）删除的行**恰好只有一行**：
  `_standardize_form_container_semantics(container_tree, model=model, view_type=view_type, source=source)`；
  同时新增替代机制 `_apply_form_structure_roles_to_tree`。替代者只写 `formStructureRole`（身份），
  **从不写 `semanticTitle`（标题）**，因此不是等价替换。
- 消费侧齐备：`nativeBusinessSection.ts:96`、`NativeFormTreeRenderer.vue:892`、`schema.ts:737`、
  `contractFormPresenter.ts:444`；两个既有 P0 守卫（`form_view_native_structure_boundary_guard.py:127`、
  `view_orchestration_boundary_guard.py:182`）也声明该标准器"只写 semanticTitle/semanticAnchor 元数据、
  不得写可见 title/label/string"。
- 结论：这不是方向取舍，而是**在生产代码中丢失的一行契约接线**。前端早已删除自己的猜测、
  改为消费契约署名，因此缺生产端＝出厂契约恒不署名章节标题。方向确定为"补回生产端"。

**二、修复**

P0 `addons/smart_core/core/unified_page_contract_v2_assembler.py`
1. 恢复 `_standardize_form_container_semantics` 生产调用（置于 `_standardize_business_form_default_tabs` 之后）。
2. 修 `_is_generic_container_label` 的缺陷：`generic` 含 `""`，而 `labels` 只要缺任一 `title/label/string`
   就含 `""`，集合求交**恒真** → 已署名标题（如「基本信息」）被判为 generic，被结构猜测覆盖。
   改为"标题非空且不等于任何身份值"。

P4 `scripts/verify`（验证工具，不改产品）
1. `form_structure_contract_runtime_audit.is_unlabeled_group` 同类 `""` 缺陷修正。
2. 该审计 notebook 指标原先过滤 `business_form_default_tab_standardizer`——**全仓库不存在该字符串**，
   结构性恒 0。改为声明式 `NOTEBOOK_PROJECTION_CARRIERS` + `resolve_projection_carriers()` 生产者存在性校验，
   发明/改名载体直接报错（载体的声明值现为"空集"，因为分页签标准器本身是**有意的 no-op**）。
3. `form_structure_contract_standardizer_guard` 增补 `production_call_sites()` 断言：守卫只测合成 fixture
   对死代码照过的盲点被堵住。

**三、负例基线（先证未注入正常，再证注入可检出）**

| 用例 | HEAD（未修） | 本轮（已修） |
| --- | --- | --- |
| group 仅带署名标题「基本信息」 | 未署名 | 已署名 |
| group 有 label、缺 title 兄弟 | 未署名 | 已署名 |
| 裸技术 group（无任何标题） | 未署名 | 未署名（不变，正确） |
| 生产接线断言：`_standardize_form_container_semantics` 调用点 | **0** | **1** |
| 生产接线断言：`_standardize_business_form_default_tabs` | 1 | 1 |
| `resolve_projection_carriers` 对不存在的载体 | — | 抛错（原为静默恒 0） |

**四、本地 L1/L2 非零证据（全部 EXIT=0）**

- `make verify.form_structure.contract.guard`（12 tests + standardizer guard）
- `make verify.form_view.native_structure.boundary_guard`
- `make verify.view.orchestration_boundary_guard`
- `make verify.form_container_presentation.guard`
- `make verify.product_view_structure.contract.unit`（25 tests）
- `make verify.frontend.form_structure_contract_projection.unit`（fields=76 unclassified=0）
- `make verify.frontend.native_form_structure_responsibility.unit`（cases=12）
- `make verify.frontend.form_structure_surface_contract.unit`

**五、受管运行态刷新与前后对比（同一 163 模型口径）**

车道：`daily.runtime.candidate.bundle_sync`（PASS，`origin_main_mutated=false`）→
`daily.runtime.source_revision.align`（PASS，重启后 `served.source_revision=330fb36d`）→
`daily.runtime.published_face.converge`（PASS，`module_upgrade_returncode=0`，`upgrade_mode=run`，90/90 菜单精确匹配）。

| 指标 | 修复前 `514c4c11` | 修复后 `330fb36d` |
| --- | --- | --- |
| `projected_semantic_group_models` | **0** | **163** |
| `semantic_group_count` / `group_count` | 0 / 996 | **996 / 996** |
| `unlabeled_group_count>0` 的模型数 | 163 | **0** |
| `contract_standardized` | 0 | **81** |
| `contract_needs_attention` | 163 | **82** |
| `missing_group_semantics` | 163/163 | **0** |
| `boundary_violation` / `boundary_ok` | 158 / 5 | 158 / 5（不变） |
| `slots is required`（B1） | 60 | 60（不变） |
| `field outside structure`（B2） | 2024 | 2024（不变） |
| `attachment` / `timeline` | 160 / 160 | 160 / 160（不变） |

剩余 82 的缺口直方图 = `missing_contract_notebook/page` 82 + `missing_collaboration/attachment/timeline` 3，
即第 20/21 轮已定性的 **B4（82 个无 notebook/page 的作用域模型）与 B5（3 个非 chatter 工作台表面）**，
均为口径问题、非产品债。**B1/B2 前后逐字节不变**，证明本轮修复被限制在章节标题通道，未越界。

报告：`.runtime/final-acceptance/daily-deployed/form_structure_contract_runtime_audit_330fb36d.json`
（前：`..._1066b422.json`）。

**六、受影响表面浏览器核对（1440）**

`/f/project.project/581?menu_id=379&action_id=506`：`treeCount=1`、`driverErrorCount=0`、`pageErrors=[]`、
声明可见按钮 6 个各 =1、声明隐藏按钮 5 个各 =0、6 个声明章节标题全部出现、提示块存在、**verdict PASS**。
（该页原生标题路径本就生效，本轮不改变其呈现；本轮补的是"原本无署名标题的分组"的契约署名。）

**七、边界**

- 本轮为**产品代码变更**（P0 `smart_core`），已按既有受管入口重建/刷新运行态并复验；**未 push**、
  未合并、未标记整体目标完成。
- 仍待所有者裁决的 P0 仅剩两项：**B1**（校验尊重 `layoutPolicy` / 投影最小 slot）、
  **B2**（由被投影布局派生 slot 字段域）。本轮不预先占用其结论。
- 唯一开放的产品交付项仍为**所有者登录核对**（`wutao/123456`、`sc_demo`、`http://1.95.85.92:18081/`）。
---

## 23. 第 23 轮（2026-10-10）：B1/B2 同一根因收口 —— 运行时校验器按已声明 `layoutPolicy` 尊重成员权威

**一、裁决与定性**

所有者裁决 **B（「校验尊重已声明的 layoutPolicy」）**。本轮把第 21 轮登记的 B1/B2 作为**同一根因**处理：
`addons/smart_core/core/unified_page_contract_v2_runtime.py::find_form_structure_contract_issues`
在两条断言上**不承认生产者已声明的结构成员权威**。

判定依据（三源一致，非取舍）：

1. **架构声明**：`docs/architecture/native_first_form_structure_authority_v1.md`（2026-09-16 修订）——
   「`layoutContract.containerTree` 承载唯一有效树，`formStructureContract` 不另造正文树」。
2. **已声明消费者**：`frontend/apps/web/src/app/contracts/v2/schema.ts::decodeFormStructureContract`——
   对 `layoutPolicy === 'container_tree_authority'` **明确禁止** `slots` / `columns` / `fieldRoles`
   （`'container tree authority forbids independent structural slots, columns and field membership'`），
   且只做 `slots → layout` **单向**投影校验（`references field not projected by layout`），无反向断言。
3. **生产者方向**：`unified_page_contract_v2_assembler.py::_project_form_structure_to_layout`
   ——「Bind the semantic structure to fields owned by the final native tree」，即把 slot 的 `fieldRefs`
   **裁剪到最终原生树已有字段** ⇒ 生产者保证 `slots ⊆ tree`，从不保证 `tree ⊆ slots`。

**B1 因此不是「(a) 还是 (b)」的取舍**：`ui_contract_v2.py` 的 native_authority 短路径按其声明输出
`layoutPolicy=container_tree_authority` + `slots:[]` + `fieldRoles:{}`，P0 测试
（`test_form_structure_contract_uses_native_mode_without_entry_authority`、
`test_native_authority_can_publish_task_presentation_without_configured_sections`）逐字断言该形状；
若改走「发布最小 slot 集」，已声明消费者会**拒收**该契约。(b) 在声明上不可行，(a) 被强制。

**B2 的归属纠正**：`layout projects field outside structure` 不是「生产者覆盖缺口」，而是
**P0 校验器越界断言**（无生产者缺陷、无产品行为变化）。运行态 163 模型只读分类（本轮新增探针
`probe_sources/fs_coverage_probe.py`）给出判决性数据：

| 分类口径 | 结果 |
| --- | --- |
| `refs_not_in_layout`（slot 引用字段缺布局，即声明方向） | **0 / 163 模型**（生产者 100% 守约） |
| 越界字段 ∩ 治理字段域（真实覆盖缺口候选） | **6 / 163**（其余全部非治理） |
| 越界字段样例（未受治理） | `source_created_by`(62)、`source_created_at`(56)、`active`(44)、`attachment_ids`(24)、`currency_id`(24)、`sequence`(9) |
| 按 policy 分布 | `container_tree_authority` 1498、`native_authority` 547、`overview_then_task_slots` 156 |

即：越界字段全部是**原生技术/投影/残留字段**，任何策略下都合法地由唯一有效树承载。

**二、修复（P0 `addons/smart_core/core/unified_page_contract_v2_runtime.py`）**

1. 新增 `FORM_STRUCTURE_TREE_MEMBERSHIP_POLICIES = {"container_tree_authority"}` 与
   `tree_membership_authority` 判定，作为「成员权威」的单一解析点。
2. `formStructureContract.slots is required` 只在**非树权威**策略下断言（B1：60 → 0）。
3. 新增**镜像断言**（与已声明消费者同源，属加强）：树权威结构不得并发发布
   `slots` / `columns` / `fieldRoles`，否则正文所有权被拆成两份 → 契约 fail closed。
4. 反向断言收敛为「**受治理字段必须被声明结构归属**」：仅当策略非树权威、且字段属于
   `sourceAuthority.governance_source.fieldNames` 时才判越界；原生技术/残留字段由唯一有效树承载
   （B2：2024 → 0）。**未放宽任何受声明支撑的断言**：`slot → layout` 投影、治理字段域、
   内部字段、重复引用、来源权威等检查逐字不变。

**三、定向单测（负例先证基线再证注入）**

`addons/smart_core/tests/test_unified_page_contract_v2_runtime.py` 19 → **23 tests**（全 EXIT=0）：

| 用例 | 断言 |
| --- | --- |
| `test_container_tree_authority_structure_publishes_no_slots` | 基线：树权威 + 空 slots/fieldRoles ⇒ `issues == []` |
| `test_container_tree_authority_structure_forbids_published_slots` | 注入：树权威并发 slots ⇒ 被检出（新增断言） |
| `test_form_structure_contract_rejects_governed_layout_fields_outside_structure` | 注入：受治理字段未被 slot 归属 ⇒ 被检出（原断言按声明改写：声明 `overview_then_task_slots` 并把 `company_id` 纳入治理字段域） |
| `test_slot_structure_tolerates_ungoverned_native_tree_fields` | 负例：非治理原生字段在树中 ⇒ 不误报 |

第 3 行是本轮唯一改动的既有断言：原用例的 fixture **未声明 `layoutPolicy`**（隐含旧「结构契约即正文权威」模型，
2026-07-20 基线期），与 2026-09-16 原生优先决策冲突。改写后**强度不降**（仍是「被声明的结构域内字段必须被归属」），
且未删除任何检查项。

**四、本地非零 L1/L2 证据（全部 EXIT=0）**

- `make verify.unified_page_contract.v2.runtime`（23 tests + 119 tests + guard score=6）
- `make verify.form_structure.contract.guard`（12 tests + standardizer guard）
- `make verify.business_config.formal_list.unit`（128 + 9 + 52 + 5 tests）
- `make verify.form_view.native_structure.boundary_guard` / `verify.view.orchestration_boundary_guard` /
  `verify.form_container_presentation.guard`（46 tokens）
- `make verify.product_view_structure.contract.unit`（25 tests）
- `make ci.local.iteration` PASS（`change_state=dirty`，L1 only）

**五、受管运行态刷新与前后对比（同一 163 模型口径）**

车道：`daily.runtime.candidate.bundle_sync`（PASS，`old_sha=330fb36d`→`source_sha=e885d590`，
`origin_main_mutated=false`）→ `daily.runtime.source_revision.align`（PASS，重启后
`served.source_revision=e885d590`、`database=sc_demo`、`frontend_build_sha256=bc5a0cac`）
→ `daily.runtime.published_face.converge`（PASS，`module_upgrade_returncode=0`、`upgrade_mode=run`、
`upgrade_modules=["smart_core"]`、90/90 菜单 × 2 产品、快照 `daily-navigation-*-e885d590b314`）。

| 指标 | 修复前 `330fb36d` | 修复后 `e885d590` |
| --- | --- | --- |
| `boundary_ok` / `boundary_violation` | 5 / **158** | **163 / 0** |
| `slots is required`（B1） | **60** | **0** |
| `layout projects field outside structure`（B2） | **2024** | **0** |
| `projected_semantic_group_models`（B3） | 163 | 163（不回退） |
| `contract_standardized` / `contract_needs_attention` | 81 / 82 | 81 / 82（B4/B5 作用域口径不变） |
| `attachment` / `timeline` | 160 / 160 | 160 / 160 |
| 非边界列逐模型 diff | — | **0** |

报告：`.runtime/final-acceptance/daily-deployed/form_structure_contract_runtime_audit_e885d590.json`
（前：`..._330fb36d.json`）。分类探针原始输出：
`.runtime/agent-runs/.../form_structure_runtime_audit_baseline_attribution/coverage_probe_raw.txt`。

**六、影响面与复用判定**

- 改动仅落在 `find_form_structure_contract_issues`（+ 其新增常量）。该函数**无生产调用点**：
  `grep find_runtime_guard_issues|find_form_structure_contract_issues` 命中仅 tests 与
  `scripts/verify/{unified_page_contract_v2_runtime_guard,form_orchestration_business_usability_audit,form_structure_contract_runtime_audit}.py`。
- 因此**渲染面不可能变化**（生产者与前端均未改），第 22 轮的 1440 浏览器证据
  （`/f/project.project/581?menu_id=379&action_id=506` PASS）继续有效并按规则复用，不重跑矩阵。
- B1/B2 的责任层修正：B1 = P0 `smart_core` 校验器与生产者自相矛盾；B2 = P0 `smart_core`
  **校验器越界断言**（非生产者缺口、非 P1）。不因标签改写提交历史。

**七、边界**

- 本轮为 P0 产品代码变更，已按既有受管入口重建/刷新运行态并复验；**未 push**、未合并、未标记整体目标完成。
- B4（82 个无 notebook/page 作用域模型）与 B5（3 个非 chatter 工作台表面）仍为口径问题，未变。
- 独立于本轮的后续专题（不占用本轮结论）：「治理是否应为原生树字段声明更完整的字段域」——
  当前 `outside ∩ governance = 6/163`，属可观测的治理选择，非契约缺陷。
- 唯一开放的产品交付项仍为**所有者登录核对**（`wutao/123456`、`sc_demo`、`http://1.95.85.92:18081/`）。

---

## 24. 第 24 轮（2026-10-10）：复用索引自身的收口 —— 声明输入补全与回执重建

**一、性质与边界**

本轮**无任何产品代码变更**，全部落在 P4 取证体系（`.agent` run 台账与其回执机制）。产品面保持第 23 轮
结论：日常运行态 serve `e885d590`，163 模型审计 `boundary_ok=163 / boundary_violation=0`。

**二、发现的体系缺陷：假复用（不是"重跑"，而是"错用可复用"）**

交接稿记载"`make agent.run.resume` = resolved，40/40 可复用、0 stale"。本轮**实测推翻**：该判断来自更早的
候选身份，在 `e885d590` 上已不成立，实际为 **reusable 32 / stale 8 / not_run 7**。逐项归因后发现真实缺陷：

**有 5 个 check 的声明输入不完整**——受管 Make recipe 实际会执行的测试工具或配置依赖未被声明。后果是：
该文件一旦变化，回执**仍然被判为可复用**，于是"已过期结论"会被索引认证为当前结论。回执机制本体
（输入哈希、环境身份、原始日志哈希）是健全的，**缺口在这些 check 的声明依赖集**。

| check | 未声明的依赖（目标实际会执行） |
| --- | --- |
| `frontend_typecheck` | `scripts/dev/pnpm_exec.sh` |
| `ci_local_iteration` | `baseline_iteration_execution_policy_guard.py` 及其单测（`ci.local.iteration` 的首个前置） |
| `unified_page_contract_v2_runtime_unit` | `addons/smart_core/tests/test_unified_page_contract_v2_mobile_compact.py`（该目标实际跑的第二套 119 tests） |
| `business_config_formal_list_unit` | `test_load_contract_response_cache.py`、`test_view_orchestrator.py`、`test_formal_list_configuration_baseline.py`、`make/runtime_ops.mk` |
| `project_ledger_entry_carrier_orm` | `make/dev.mk`（该 check 的 recipe 所在文件） |

**三、修复与回执重建（受管流程，不手工造回执）**

按 `make agent.run.begin → 受管目标 → make agent.run.record` 逐条重建，日志落在
`.runtime/eff/rec/closeout-20261010-layout-policy-authority/`：

| check | 计数 | 备注 |
| --- | --- | --- |
| `frontend_typecheck` | 1 | vue-tsc strict，10.5s |
| `ci_local_iteration` | 16 | `verify.baseline.iteration.execution.policy` |
| `contract_structure_lock` | 14 | domains=14 |
| `product_view_structure_contract_unit` | 25 | |
| `frontend_navigation_initialization_race_unit` | 35 | |
| `unified_page_contract_v2_runtime_unit` | 142 | 23 + 119 |
| `form_structure_contract_guard` | 13 | 12 tests + standardizer guard |
| `business_config_formal_list_unit` | 194 | 128+9+52+5 |
| `agent_ledger_consistency_unit` | 15 | goals=93 runs=71 |
| `project_ledger_entry_carrier_orm` | 28 | 本地 `sc_dev_demo` 模块测试：0 failed / 0 error |
| `frontend_canonical_form_presenter_unit` | 177 | 套件自报 cases=177 |
| `frontend_contract_header_action_unit` | 9 | 该套件只打印维度计数、无总数，故取日志中 PASS 断言组数（其子用例合计 76） |
| `frontend_modifiers_runtime.guard` | 1 | 单条 PASS |

**四、两条有意保留的"未回执"，均附依据（不是遗漏）**

1. `form_structure_contract_runtime_audit`（`not_run`）：其权威运行是**远端受管运行态**上的 163 模型审计，
   运行身份即 served `e885d590`，报告已作为该 check 的**声明 readback**
   （`.runtime/final-acceptance/daily-deployed/form_structure_contract_runtime_audit_e885d590.json`，
   原始报告另转存为同目录 `..._e885d590.log`）。在输入未变的情况下重跑是同义重复，故回执在
   **冻结/交付轮**按冻结指纹一次性铸造。
2. `browser_login_return_authority`（`stale`）：唯一变化的声明输入是 `make/runtime_ops.mk`；本轮给出
   确定性影响面分析——`git diff 5220db8b..HEAD -- make/runtime_ops.mk` 为 9 增 4 删，**其中不含 nav
   route-authority 车道的任何 recipe/依赖/断言**，故"使回执输入过期的那次变更"不影响其断言结论，按规则
   做记录式前向携带而非重跑。

**五、复用索引前后对比**

| 指标 | 修复前 | 修复后 |
| --- | --- | --- |
| `reusable` | 32 | **45** |
| `stale` | 8 | 1（nav browser，已记录影响面分析） |
| `not_run` | 7 | 1（远端运行态审计，冻结轮铸造回执） |

**六、边界**

- 未 push、未合并、未标记整体目标完成；**未改任何产品代码**，未放宽任何断言或门禁。
- B4（82 个无 notebook/page 作用域模型）、B5（3 个非 chatter 工作台表面）仍为口径问题；覆盖债
  （140 个 @tagged 分组）仍由登记表机器跟踪。
- 唯一开放的产品交付项仍为**所有者登录核对**（`wutao/123456`、`sc_demo`、`http://1.95.85.92:18081/`）。

### 24-续（2026-10-10 本轮续）：运行态审计回执铸造 + 环境残留核查

**一、把最后一条 `not_run` 关闭（受管流程，非重跑取证）**

`verify.form_structure_contract_runtime.audit` 之前只有远端审计报告、没有回执，索引里始终是 `not_run`
（下轮还会再跑一遍）。本轮按受管流程铸造其回执：`make agent.run.begin` → 受管远端审计
（注册工作树 `e885d590` 上 `ODOO_CONTAINER=sc-backend-odoo-dev-odoo-1 DB_NAME=sc_demo
bash scripts/verify/form_structure_contract_runtime_audit.sh`）→ `make agent.run.record`（163 个受审模型契约，
日志 `.runtime/eff/rec/closeout-20261010-layout-policy-authority/rec_form_structure_contract_runtime_audit.log`）。

**这次重跑的附加价值不是"再证一遍"，而是身份未漂移的独立确认**：新报告与第 23 轮报告**逐字节一致**
（报告 sha256 `32c01d74e8a129e2…` 不变；`boundary_ok 163`、`81/82`、语义分组 163、
`attachment/timeline 160/160`），即 served 运行态在两次审计之间没有发生任何契约面漂移。

**二、环境残留核查（只读）**

| 项 | 结论 |
| --- | --- |
| 本地 SSH 端口转发 / 隧道 | 无（`ps` 无 `ssh -L/-R/-D` 进程） |
| 工作区内残留 odoo / vue-tsc / node verify 进程 | 无 |
| 本机容器 | 仅注册的 `sc-local-dev-*`（4 个，healthy） |
| 工作树 | 单工作树 `f3a89714`（符合"最多两个工作树"约束） |
| 本地分支 | `main`、本审计分支、`release/daily-runtime-mainline-daecaafc`（受管清理入口拒绝 `release/*` 保护前缀，已登记残差） |
| 远端审计临时目录 | 本轮自建 `/tmp/audit_continue` 与第 23 轮 `/tmp/audit_e885d590` 已回收（报告已归档入仓） |

**三、复用索引终态**

| 指标 | 本轮起点 | 终态 |
| --- | --- | --- |
| `reusable` | 32 | **46** |
| `stale` | 8 | **1**（nav browser，已记录影响面分析，非未解释项） |
| `not_run` | 7 | **0** |

**四、边界（不变）**

未 push、未合并、未改产品代码、未放宽任何断言；B4/B5 与覆盖债不变；车道级重建/快照 DENY 不变；
唯一开放产品交付项仍为所有者登录核对（`wutao/123456`、`sc_demo`、`http://1.95.85.92:18081/`）。

### 24-续（2）2026-10-10：B4/B5 原生侧归属取证（口径确证，非投影缺陷）

第 24 轮把 B4（82 个 `missing_contract_notebook/page`）与 B5（3 个
`missing_collaboration_runtime/attachment/timeline`）判为"口径问题、需裁决"。本轮不重跑审计，
只用**只读原生侧对照探针**把口径判断升级为**确证**：判据已经从报告里解出，缺的只是"原生那一侧到底有没有"。

**一、探针与受绑身份**

- 通道：`sc-root` → `docker exec sc-backend-odoo-dev-odoo-1`（`scripts/ops/odoo_shell_exec.sh`），
  注册工作树 `/opt/projects/repos/sce-product-odoo @ e885d590`，库 `sc_demo`，与审计报告同环境。
- 探针对每个模型同时取两侧：契约 `layoutContract.containerTree` 的 notebook/page 计数、`runtimeContract.collaboration`
  的三个 `enabled`；原生 `env[model].get_view(view_type="form")` 的 arch 里 `<notebook>`/`<page>`/`oe_chatter`
  元素计数（lxml 解析，不做字符串近似）。
- 取证目录：`.runtime/agent-runs/DAILY-DEV-MAINLINE-PRODUCT-ACCEPTANCE-CLOSEOUT/form_structure_native_side_attribution/`
  （3 个探针源码 + 3 份原始输出 + `attribution_summary.json`，含源码与原始输出的 sha256）。
- 两处探针自身缺陷当场修正（不改产品）：该版本 `get_view` 返回 **dict**(`arch/id/model/models`) 而非二元组；
  以及 `lxml` 的 `Comment.tag` 是 cython 函数、不能作 `Counter` 键。

**二、B4 结论：口径，非投影缺陷（82 模型）**

| 断言 | 结果 |
| --- | --- |
| 原生 notebook 集合 == 契约 notebook 集合 | **成立**（81 == 81，对称差为空） |
| 原生 page 集合 == 契约 page 集合 | **成立**（81 == 81，对称差为空） |
| 82 个 `contract_needs_attention` == 原生无 `<notebook>/<page>` 的 82 个模型 | **成立** |
| 81 个 `contract_standardized` == 原生有 `<notebook>/<page>` 的 81 个模型 | **成立** |
| 82 个平坦原生表仍带原生 `<group>` 容器 | **成立**（`native_group>=1` 全命中） |

即：`missing_contract_notebook/page` 只在**原生表单本身没有分页签**时触发，契约如实声明 0 个页签。
**没有任何原生页签面被丢失，也没有欠下的投影工作**。第 24 轮"六、B4 定性"从契约侧推断的结论由此获得原生侧直接证据。

**三、B5 结论：口径，非缺陷（3 模型）**

| 模型 | 原生 chatter | `message_ids` / `message_post` / `activity_ids` / `follower` | upload/download hook |
| --- | --- | --- | --- |
| `sc.company.project.refund.workspace` | 无 | 全无 | 无 |
| `sc.current.account.workspace` | 无 | 全无 | 无 |
| `sc.team.loan.deduction.workspace` | 无 | 全无 | 无 |

三者都是**非 mail 模型**（无 `message_ids`/`activity_ids`/`message_post`/`message_follower_ids`），
且无附件上传/下载许可，**原生表单视图也没有 chatter**。契约给出空 `collaboration` 与事实一致，
因此这三个 gap 是覆盖度标签而非缺陷。第 24 轮"七、B5 定性"同样获得原生侧确证。

**四、方向性核查：协作契约是否存在"压制原生面"（0 例）**

顺带对全量 163 模型做了双向核查，因为"契约与原生不一致"只在**压制**方向才是缺陷：

- **压制方向（契约 false / 原生有 chatter）= 0 例**。契约从未压掉原生表单已有的协作面。
- **增量方向（契约 true / 原生 arch 无 chatter）= 20 例**：`construction.contract`、`construction.contract.income`、
  `payment.request`、`project.budget`、`project.milestone`、`sc.approval.policy`、`sc.expense.claim`、
  `sc.financing.loan`、`sc.fund.account.operation`、`sc.general.contract`、`sc.invoice.registration`、
  `sc.output.invoice.adjustment`、`sc.payment.execution`、`sc.receipt.income`、`sc.self.funding.registration`、
  `sc.settlement.adjustment`、`sc.settlement.order`、`sc.treasury.reconciliation`、`sc.workflow.def`、
  `sc.workflow.instance`。20 个**全部是 mail 能力模型**（有 `message_ids`），其原生 form arch **既无 `oe_chatter`
  也无 `<chatter/>`**（逐模型元素级取证）。
- 增量方向的产源是 **P0 通用规则**：`smart_core/handlers/ui_contract_v2.py::_inject_collaboration_contract`
  的 `chatter_enabled = declared OR message_capable OR activity_capable`，**无任何模型特判**。
- 定性：这是**只增不减**的声明面差异——契约在原生表单未画 chatter 的 mail 模型上声明了协作面板。
  **不丢失任何原生面**，不构成审计 gap（审计只发 `missing_*`，不发 extra），因此 82 个
  `contract_needs_attention` 的定性不受影响。是否要收敛为"与原生 arch 对齐"属于**产品面裁决**，
  本轮只登记事实、**不改 P0 行为**（改任一侧都会改变 20 个模型的产品面）。

**五、登记一处口径命名风险（本轮回执内，不扩范围）**

审计报告列 `native_chatter` 实为**契约值**（`scripts/verify/form_structure_contract_runtime_audit.py:474-479,520`
读的是 `runtimeContract.collaboration.chatter.enabled`），字段名容易被读成"原生 vs 契约对照"，而该审计
并不做这种对照；`docs/ops/iterations/...20261009.md:2058` 也引用了这个字段名。本轮**只登记该命名风险**，
不改已入仓报告 schema（改名会连带 churn `docs/audit/native/*` 与被引用的迭代文本），留待所有者裁决。

**六、运行环境残留回收（本轮足迹先归档、后清理，只回收本分支可证实的文件）**

清理前逐份比对 sha256，**只要远端副本在本仓 `.runtime` 已有同哈希归档即判定为冗余**，否则先归档再删：

| 远端 `/tmp` 项 | 判定 | 处置 |
| --- | --- | --- |
| `fs_contract_runtime`、`fs_contract_runtime2`（修复前基线 `boundary_ok 5 / violation 158`） | 本仓未归档 | **先归档**到 `.../form_structure_runtime_audit_baseline_attribution/prefix_baseline_reports/`（json+md）再删 |
| `fs_audit_remote.log`、`fs_audit_remote2.log`、`fs_audit_remote3/4.log` | 运行日志 | 归档为 `pre_fix_audit_1520/1543/1603/1631.log` 再删 |
| `fs_contract_runtime3`、`fs_contract_runtime4`、`sc_fs_contract_audit_1066b422`（json sha `a0088960…`） | 与已归档 `..._1066b422.json` **逐字节一致** | 补档 csv/md 后删 |
| `fs_audit_after`（json sha `da45f98a…`） | 与已归档 `..._330fb36d.json` **逐字节一致** | 补档 csv/md 后删 |
| 容器 `sc-backend-odoo-dev-odoo-1:/tmp/fs_*probe*.py` | 探针源码已归档 | 以 `docker exec -u root` 删除（文件属 root，默认 `odoo` 用户无权删） |

非本分支本轮的同期 `/tmp` 遗留（10-04～10-06 的 `probe*`、`sc_daily_probe*`、6 月的 `scbs55_*` 等）
**不在本轮清理范围**，未触碰。本机仅注册的 `sc-local-dev-*` 容器；另见另一执行器的
`sc-fe-r2-p1-01-*`（属其工作树，未触碰）。无 SSH 端口转发，无残留构建/验证进程。

**七、边界**

- 未改任何产品代码、未放宽任何断言/门禁、未 push/未合并；B4/B5 由"待裁决"升级为"已确证为口径"。
- 覆盖债（140 个 `@tagged` 分组）与车道级重建/快照 DENY 不变；唯一开放产品交付项仍为**所有者登录核对**
  （`wutao/123456`、`sc_demo`、`http://1.95.85.92:18081/`）。

### 24-续（3）2026-10-10：服务面 vs 主线拓扑实测与四态台账更正

第 24 轮（含续 1/续 2）的台账里，四态"版本发布"写的是运行态。收尾核对时发现台账
blockers[2] 仍留有**过期陈述**"the runtime now serves mainline daecaafc"——这对 2026-10-10
晚几轮之前的时点成立，但续轮把运行态推进到了 `e885d590` 之后就不再成立。本轮不改产品、
不做新运行验收，只做**一次拓扑实测 + 四态更正**，避免读者把"主线=服务面"当成同一身份。

**一、实测拓扑（本轮命令级证据）**

| 项 | 值 |
| --- | --- |
| `origin/main` | `daecaafc6da6c61d92312a464b84468e7d85c486`（Merge PR #637） |
| 分支 HEAD | `1096895dca8110fe1ad7fcdc182b86636a06b5aa` |
| 领先 origin/main | **83 提交** |
| 其中触及产品/工具路径 | **39**（`addons/` `frontend/` `config/`：30 文件 +1568/-302；`make/` `scripts/`：13 文件 +995/-308） |
| 纯记账 | 44 |
| 合并就绪 | `git merge-tree --write-tree origin/main HEAD` → **exit 0，零冲突** |
| 远端同名分支 tip | `9a000714`（落后本地 21 提交） |
| 服务面 revision | `e885d590b314d310de20a373c4f4c152996e3daf`，`database=sc_demo`，`frontend_build_sha256=bc5a0cac181d5270…` |
| 服务面 revision 是否为 origin/main 祖先 | **否** |

39 个未入主线的产品/工具提交里，包含**已服务**的 P0 校验器修复 `e885d590`（B1/B2 同一根因）
与契约作者章节标题生产者 `330fb36d`（B3a），以及 `514c4c11`/`1066b422`（声明修饰符值域单一权威）、
`5c828da2`/`77e407cc`（声明布局按钮发布授权执行面）、`dde30179`/`d106d2dd`（角色锁定落地与目录投影）、
`3d90df05`（前端丢弃契约拒绝的登录回跳目标）。早前的 PR #635→`bb6b6e82`、#636→`e2e32ad3`、
#637→`daecaafc` 集成**已完成**，本 run 历史回执绑定的正是那批身份；它**不覆盖**这 39 个后续提交。

**二、四态更正（报告时严格分开）**

| 状态 | 结论 |
| --- | --- |
| 批次验收 | **完成** |
| 主线集成 | PR #635/#636/#637 **完成**（`daecaafc`）；**后 39 个产品/工具提交未入主线**（含已服务 P0 修复） |
| 版本发布 | 日常运行态 serve `e885d590`（`sc_demo`，frontend `bc5a0cac…`） |
| 产品交付 | **待所有者登录核对** |

`blockers[2]` 已按上表改写为实测拓扑（并保留"此前的 daecaafc 陈述在当时为真、现更正"的说明），
`evidence.round_20261010_served_ahead_of_mainline` 记录了 commit 拆分与合并就绪性。

**三、为何本轮不发布**

受管发布入口 `make pr.push`（`scripts/ops/git_safe_push.sh`）与 `make pr.push.gitee`
（`scripts/ops/gitee_temporary_integration.py publish`）均为**操作时确认门控**：gitee 车道要求
`--apply --confirm $(GITEE_INTEGRATION_CONFIRM)` 加 `GITEE_EXPECTED_MAIN`/`EXPECTED_HEAD`，
正式 PR 车道另需 `GITEE_PR_TOKEN_FILE`。`origin`（github.com/lidefend/sce-backend-odoo）是
**PUBLIC** 仓库，发布 83 个提交跨越公开边界，属**所有者操作时确认动作**，不是可单方面执行的迭代步骤。
本轮**刻意未 push**，也未放宽任何守卫/检查/保护来制造该结论。

**四、本轮门禁回执（记账）**

- `make verify.agent.ledger.unit` → **15 项通过**（`goals=93 runs=71 pinned_residuals=2 open_run_allowlist=2`），
  回执 `.runtime/eff/rec/closeout-20261010-b4b5-native-attribution/rec_agent_ledger_consistency_unit.log`。
- `make agent.run.resume` → 复用索引 **reusable 46 / stale 1**（与续 2 持平，无新增漂移）。
- `make ci.local.iteration` → **PASS**（`change_state=dirty scope=unclassified_by_design coverage=L1_only`，
  next = 风险选择的非零 L2 目标）。

**五、边界**

- 未改产品代码、未放宽断言/门禁、未 push/未合并、未新增运行验收。
- 覆盖债（140 个 `@tagged` 分组）、车道级重建/快照 DENY、`native_chatter` 命名风险、仓库外客户模块
  `user_preferences.py` 路径债均**保持登记原样**；20 例增量 chatter 仍待产品裁决。
- 唯一开放产品交付项仍为**所有者登录核对**（`wutao/123456`、`sc_demo`、`http://1.95.85.92:18081/`）。
