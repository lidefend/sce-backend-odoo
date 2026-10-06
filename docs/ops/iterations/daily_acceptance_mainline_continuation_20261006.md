# Daily Acceptance Mainline Continuation（日常运行态主线续接绑定，2026-10-06）

Run: `.agent/runs/DAILY-ACCEPTANCE-MAINLINE-CONTINUATION/run.json`
Branch: `audit/daily-acceptance-mainline-continuation-20261006`
Baseline: `6c8e07f70c1ce0d501f9f5b56911d74f9321a721`（`main`，PR #596 之后）
Runtime repository: `sc-root:/opt/projects/repos/sce-product-odoo`
（`ENV=dev`、`ENV_FILE=.env.dev`、`DB_NAME=sc_demo`、`ODOO_DBFILTER=^sc_demo$`）
Owner acceptance entry: `http://1.95.85.92:18081/`（自定义前端），口令 `wutao/123456`

## 1. 目标与责任层

- **Formal Product Layer**：P4（ops delivery / runtime acceptance）。
- **Layer Target**：`daily development runtime acceptance`（sc-root 日常运行态 + `sc_demo` + 自定义前端）。
- **Module**：`.agent`、`docs/ops/iterations`（本批产品代码 **0 变更**）。
- **Standard vs User-Specific**：运行态对齐与验收证据绑定，属 ops 交付层，不是平台机制、行业默认、客户偏好或低代码运行配置。
- **Why Here**：把权威 `main` 精确 SHA 落在日常运行态，并让受管只读验收探针绑定新的 served SHA，属交付验收层。
- **Why Not Elsewhere**：不改 P0-P3 产品语义，不放宽 ACL/字段权限/断言/负例，不改生产租户，不新增/轮换口令。
- **Blast Radius**：sc-root 日常运行仓与其 served 版本身份、`sc_demo` 只读验收面与既有 `wutao`/`fixture_role_finance` 凭据、一条 run 与一份记录。

## 2. 状态（四层分列）

- **批次验收**：通过。日常运行态已对齐到 `main = 6c8e07f7`，受管只读探针在 served `6c8e07f7` 上
  **整体 PASS**（`runtime_identity` / `frontend` / `login` / `contract` 四段全 PASS，契约 11/11）。
  本批未改动任何产品路径，未放宽任何断言、审计、ACL、字段权限或负例。
- **主线集成**：完成 —— 记录批 PR #597 已合并（merge commit `2836f9da`），合并前的最新增量
  `500d6f91` 上必需检查（`public_guard`、`merge_policy_gate`、`professional_quality_gate`、
  `frontend_release_gate`、`professional_authorization`、`python310_runtime_compatibility`、
  `release_candidate_gate`）全部 PASS。
- **版本发布**：未主张（未部署版本、未做 release snapshot）。
- **产品交付**：未主张 —— 待所有者对 §4.1 的单一产品策略观察项裁决。

## 3. 执行记录

### 3.1 身份与环境（每次运行前重新回读）

- `/api/runtime-version` 回读：`git_sha = source_revision = 6c8e07f70c1ce0d501f9f5b56911d74f9321a721`、
  `database=sc_demo`、`environment=dev`、`product_version=1.0.0-rc.20`、`frontend_build_sha256=""`（身份以 served SHA 绑定）。
- 日常运行仓 `sc-root:/opt/projects/repos/sce-product-odoo`：HEAD `6c8e07f7`、worktree 干净；
  `.env.dev` 的 `DB_NAME=sc_demo`、`SC_SOURCE_REVISION=6c8e07f7…`。
- 口令：`wutao/123456`（所有者指定的固定开发口令），契约段 fixture 账号 `fixture_role_finance/123456`。
  本批**未新增、未轮换**任何口令，也未改变通用登录默认。

### 3.2 运行态提升（受管入口，本批未重跑）

来源：`.runtime/final-acceptance/daily-main-6c8e07f7/{bundle-sync,source-revision-align}.json`

- `make daily.runtime.main.bundle_sync`：old `90484d88…` → source `6c8e07f7…`，`changed=true`、
  `normalized_from_candidate=false`、`bundle_sha256=d731f7d638c4b89a4ae5ba841336f22678235129a2790ea98de36a4527a553e1`。
- `make daily.runtime.source_revision.align`：写 `.env.dev`（previous `90484d88…` → `6c8e07f7…`，含备份
  `.env.dev.bak`）并重启 odoo；served 回读 `git_sha=6c8e07f7…`、`database=sc_demo`。
- 前端静态产物：`90484d88 → 6c8e07f7` 无任何前端运行时路径变更，远端 `dist-dev` 复用，未重建。
  运行态观测直接佐证：两版 served 的入口资源同为内容哈希文件 `/assets/index-CQk-FHJ5.js`（HTTP 200）。

### 3.3 受管只读验收探针（served `6c8e07f7`，本批实测）

受管入口 `make verify.daily_dev.acceptance.readonly.probe`，在 daily 主机
（`ENV=dev ENV_FILE=.env.dev`）执行；必需显式提供 `ACCEPTANCE_TARGET_SHA` / `ACCEPTANCE_BASE_URL` /
`DB_NAME` / `ACCEPTANCE_LOGIN` / `ACCEPTANCE_PASSWORD` / `SC_ACCEPTANCE_RUN_ID` /
`SC_ACCEPTANCE_DAILY_CREDENTIAL_CONFIRMATION`（`daily-readonly-credential-confirmation.v1`，TTL ≤ 10 分钟，键集固定）。
未手拼 compose/端口/凭据，未绕过 DENY。

登记序列固定为 **resolve → probe**：

1. `make daily.dev.acceptance_contract.resolve ACCEPTANCE_TARGET_SHA=6c8e07f7… ACCEPTANCE_BASE_URL=http://127.0.0.1:18081`
   —— 先 HTTP 校验 `served == ACCEPTANCE_TARGET_SHA`，再在 `DAILY_DEV_ACCEPTANCE_DB=sc_demo`（`SC_ACCEPTANCE_FIXTURE_SCOPE=daily_dev`）
   上重写 `ACCEPTANCE_RECORD_RESOLUTION=artifacts/backend/acceptance_record_identity.json`：
   `expected_sha=6c8e07f7…`；唯一目标 `smart_construction_acceptance_fixture.fe_delivery_hardening_payment_request_a`
   （`payment.request/36156`、action `780`、menu `550`）；companies `a=21`、`b=22`。
2. `make verify.daily_dev.acceptance.readonly.probe` —— 整体 **PASS**：

| 段 | 结果 | 关键值 |
| --- | --- | --- |
| `runtime_identity` | PASS | `served_sha == expected_sha == 6c8e07f7…`，`served_database=sc_demo`，HTTP 200 |
| `frontend` | PASS | `root_status=200`、`asset_path=/assets/index-CQk-FHJ5.js`、`asset_status=200` |
| `login` | PASS | `wutao` uid 16，`nodes=111`、`actions=89`、`leaves=89`，`role=business_config_admin`，`forbidden=[]`、`required_miss=[]` |
| `contract` | PASS | `fixture_role_finance` uid 210、company `[21,22]`、`resolved_sha=served_sha=6c8e07f7…`、11/11 checks true、`http_status=200`、`integrity_reason=ok` |
| schema guard | PASS | `[dev_acceptance_release_probe_schema_guard] PASS` |

- 契约托管：`response_bytes=1043093`、`response_sha256=2d84607b7e66e8c998a63578833a4686b200f1a998b3bc87084c9aaeaa368358`，
  `approved_semantic_sha256=c286139488caa076b38cfa607e1f336d80ad6ac94426b93132b8249e18fada05`
  （与 `90484d88` 实测值完全一致）。
- 证据：`.runtime/final-acceptance/daily-main-6c8e07f7/`
  （`daily_dev_acceptance_probe.json`、`daily_dev_acceptance_probe.contract.json`、`probe-run.log`、
  `acceptance_record_identity.json`）。

### 3.4 契约段首跑失败与纠正（输入纠正，不是放宽断言）

- **首跑**：`contract` 段 `contract_probe_auth_failed`（`identity_deployed_sha` / `resolution_unique_target` 已 true，
  其余 9 项 `not_run`）。
- **事实**：直接对 `fixture_role_finance` 做 `/web/session/authenticate`，`scdevpass` → `Access Denied`，
  `123456` → `uid=210` 成功。即日常 `sc_demo` 的 fixture 口令是**所有者指定的固定口令 `123456`**，
  而 `make/dev.mk` 的 `SC_ACCEPTANCE_FIXTURE_PASSWORD ?= scdevpass` 是**隔离 profile 的默认值**，
  并非日常运行态的 fixture 口令。
- **纠正**：按正确的 fixture 口令输入重跑（`SC_ACCEPTANCE_FIXTURE_PASSWORD=123456` → `ACCEPTANCE_CONTRACT_PASSWORD`），
  其余输入、断言、审计与负例全部不变 → 整体 PASS。
- **归类**：这是**调用输入纠正**（上一个失败输入的恢复事实已证明），不是重试同一个不变失败，
  也不是对任何审计/断言的放宽。日常 fixture 口令口径与 Make 默认值的差异记为 §4.2 记录项（不在本批改代码）。

### 3.5 前端浏览器车道证据的确定性携带（本批不重跑）

- **输入差异（路径级）**：`git diff --name-status e384b832 6c8e07f7` 共 17 项，全部为
  `.agent/**`（run 台账）、`docs/**`（文档）、`config/frontend/authoritative_navigation.json`（CI/发布导航声明）、
  `frontend/apps/web/scripts/contract_form_dirty_semantics_test.ts`（前端**开发脚本**，不在 `tsconfig include`
  的 `src` 构建范围内）、`scripts/verify/frontend_scene_component_bridge_guard.py`（CI 守卫）。
  **没有任何后端运行路径、前端运行路径、视图、动作、数据或 daily 运行态消费的配置发生变化。**
- `config/frontend/authoritative_navigation.json` 的消费者是守卫/验收脚本
  （`make/runtime_ops.mk` 的 page-identity 车道、`addons/smart_core/tests/test_menu_configuration_audit.py`、
  `frontend/apps/web/scripts/*audit*.mjs`），不是运行时服务或前端 bundle。
- **运行态佐证（不依赖路径推断）**：served `6c8e07f7` 与 `90484d88` 的
  `asset_path` 同为内容哈希文件 `/assets/index-CQk-FHJ5.js`、`login` 导航面同为 `111/89/89`、
  契约 `approved_semantic_sha256` 同为 `c2861394…`、契约响应字节同为 `1043093`。
  即服务中的前端字节与后端语义面**未变**，此前已通过的用户视角四象限 / detail / 关系往返 /
  form-profiles / workbench 证据按确定性影响分析携带，不因 HEAD 变化重跑。
- **列表范围**：按所有者裁决**不重跑矩阵**，沿用既有已接受证据
  `artifacts/frontend-web-fix-20260928/resume-20261001/list.json`（108/108 gated、负例 5/5 且
  `baseline_ok=true`、运行时错误 0）。本批也未新增选择器字符串/`44px`/`60px` 文本类“出现即通过”的断言。

### 3.6 run 检查登记修正

本 run 声明 `checks.daily_readonly_acceptance_probe` 并已登记回执
（`make agent.run.begin` / `agent.run.record`，`status=passed`、`test_count=11`，
日志 `.runtime/final-acceptance/daily-main-6c8e07f7/probe-run.log`）。
原声明的 `daily_list_surface_readonly_browser` 依所有者裁决改为**确定性携带**，不再作为本批执行项，
迁至 `run.carried_forward` 并附依据，而不是保留一个无回执的“待跑”项。

### 3.7 run 生命周期与退役（约束；执行见 §5）

- 本批合并时，本 run 保持 `status=active` 且 `.agent/active-runs.json` 仍绑定本分支。
  这与上一批先例一致：`CI-SCHEDULED-FULL-LANE-RECOVERY-E` 随 PR #595 合并时仍是 active，
  由独立的 PR #596 退役（置 `completed` 并清空 `branches`）。
- **实测约束**：`scripts/ops/agent_run_context.py` 的 `main()` 仅在 run 状态为 `resolved`
  时返回 0。当 run 被置 `completed`（summary 状态变 `closed`）或绑定被清空（`unregistered`）时，
  `make ci.local.iteration` 与 `make agent.run.resume` 都会以退出码 2 失败。
  因此**在本分支上不得提前退役**；退役必须作为后续独立步骤（对应独立 PR）执行。
- 本批未改 `run.status`、未清空绑定：`agent.run.resume` 在本分支保持 `resolved`，
  仅 `checks.daily_readonly_acceptance_probe` 因运行时属性报 `stale`
  （“runtime evidence requires authoritative environment readback”，是工具对该类检查的保守默认，
  不等于失败；其回执已在本批于 served `6c8e07f7` 上登记）。
- 该退役已于记录批合并后作为独立步骤执行，见 §5。

### 3.8 远端必需门禁首跑失败与修复（`professional_quality_gate`）

- **候选**：`9364609241b69e80fea3ac79da8d3b8508ba15e6`（PR #597）。
- **失败**：`professional_quality_gate` 中 `make verify.product.release.version` 报
  `product version duplicated outside VERSION: .agent/runs/DAILY-ACCEPTANCE-MAINLINE-CONTINUATION/run.json`。
  其余必需检查（`public_guard`、`merge_policy_gate`、`frontend_release_gate`、`professional_authorization`、
  `python310_runtime_compatibility`、`release_candidate_gate`）均 PASS。
- **分类**：记录内容违反“产品版本单源真值”门禁，**不是**产品缺陷、断言缺陷或环境缺陷。
- **根因**：`run.json` 的 `evidence.runtime_identity.product_version` 直接写了裸版本串，
  等于在 `VERSION` 之外复制产品版本。守卫扫描所有 tracked + 未忽略文件（`.runtime/`、`artifacts/`
  已被 gitignore 跳过）；文档中 `product_version=1.0.0-rc.20` 的写法与既有已合并记录一致且被守卫的前置断言允许。
- **修复**：删除该裸字面量，改为绑定 `VERSION` 文件本身
  （`product_version_authority=VERSION`、`version_file_sha256=32c7b592…`），保持单源真值。
- **复核**：`make verify.product.release.version` → PASS `duplicates=0`；
  `make ci.generated_reports.guard architecture.complexity_baseline_lock` → PASS；
  `git diff --check` → 干净。
- **未放宽**：未削弱守卫、未新增豁免/白名单、未改动 `VERSION`。

## 4. 仍未关闭

1. **`项目台账` 的 `/f/` ↔ `readonly` profile 观察项**（跨批保留，唯一未决产品策略项）：
   列表声明 `model_write_authority=true` 并据此打开 `/f/project.project/<id>`，但记录契约给出
   `effectiveRenderProfile=readonly`。探针按既有策略记为 `not_applicable`（绝不当成编辑通过）；
   是否为产品策略需所有者确认。本批未改代码。
2. **日常 fixture 口令口径记录项**：`make/dev.mk` 的 `SC_ACCEPTANCE_FIXTURE_PASSWORD ?= scdevpass`
   与日常 `sc_demo` 的 `fixture_role_finance=123456` 不一致。本批只按正确输入调用，
   未改默认值（改默认值属 `make/dev.mk` 的隔离 profile 默认口径，需单独裁决）。
3. **其它跨批保留项（未受本批影响）**：
   - `VIEW_STRUCTURE_BASELINE_CLEAN_LANE`（`deferred_env_gated`，需 `local.clean` 车道与新环境授权）。
   - `SCENE_DELIVERY_POLICY_RUNTIME_TEST_NOT_COLLECTED`（`pending_owner_decision`：
     `addons/smart_core/tests/test_scene_delivery_policy.py` 未在 `__init__.py` 注册）。
   - `LOCAL_DEV_NGINX_MOUNT_STALENESS`（已 resolved 的观察项）。
4. 四层状态见 §2。

## 5. Run 退役（终态）

- 记录批 PR #597 合并后，本 run 与 goal 已置 `completed`，`.agent/active-runs.json` 回到空的终态
  `{"schema_version":1,"branches":{}}`，使索引不再指向已合并的
  `audit/daily-acceptance-mainline-continuation-20261006` 分支。
- 退役沿用先例形态（对应 `CI-SCHEDULED-FULL-LANE-RECOVERY-E-RETIREMENT`）：独立离线 run
  `.agent/runs/DAILY-ACCEPTANCE-MAINLINE-CONTINUATION-RETIREMENT/run.json`（`environment.kind=offline`，
  检查 `run_index_terminal_state → verify.agent.resume.unit`），只做台账收口，不改产品、契约、测试、
  门禁、工作流、运行时或口令。
- 终态下 `make agent.run.resume` 在 `main` 上报告 `unregistered`，与
  `ACTIVE-RUN-INDEX-DANGLING-CLOSEOUT` 先例一致；这不是失败，而是“无活动批次”的预期结果。
- 已合并 `audit/...` 分支的删除属独立的 `branch.retire.historical` 受管车道，不在本批范围。
