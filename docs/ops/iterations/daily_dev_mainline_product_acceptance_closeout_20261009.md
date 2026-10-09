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
