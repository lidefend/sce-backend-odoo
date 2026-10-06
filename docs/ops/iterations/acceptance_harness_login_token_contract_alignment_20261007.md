# 日常验收门禁登录契约对齐（2026-10-07）

Run: `.agent/runs/ACCEPTANCE-HARNESS-LOGIN-CONTRACT-ALIGNMENT/run.json`
Branch: `fix/acceptance-harness-login-token-contract-20261007`
Baseline: `a012ced9b0fdeb891f55b8ddfdceb839496bfaa7`（`main`，PR #598 之后）
Runtime: `http://1.95.85.92:18081`（`ENV=dev`、`DB_NAME=sc_demo`、served `6c8e07f7`）

## 1. 目标与责任层

- **Formal Product Layer**：P4（ops delivery / runtime acceptance）。
- **Layer Target**：`ops_delivery_acceptance_gate`（`scripts/ops/production_acceptance_harness.py`）。
- **Module**：`scripts/ops`、`.agent`、`docs/ops/iterations`。
- **Standard vs User-Specific**：交付验收工具口径，属 P4；不是平台机制、行业默认、客户偏好或低代码运行配置。
- **Why Here**：日常开发服务器"完整发布门禁"由该受管门禁承载。
- **Why Not Elsewhere**：不改 `smart_core` 登录契约封装（生产方与前端消费方已一致），不改前端运行态，不放宽任何断言/负例。
- **Blast Radius**：门禁脚本、其单测、验收包摘要锁；`release.daily_dev.*` 与 `daily_candidate` 打包工具归档。

## 2. 根因

- 生产方 `addons/smart_core/handlers/login.py` 的 login intent 返回 `data.session.token`。
- 前端消费方 `frontend/apps/web/src/stores/session.ts` 读取 `result.session?.token`（与生产方一致）。
- 门禁 `scripts/ops/production_acceptance_harness.py` 读取 `data.token`，取到空串 → 真实 HTTP 登录判失败
  （`status=200 code=UNKNOWN`）。
- 门禁单测 `scripts/ops/test_production_acceptance_harness.py` 的 fake server 直接返回
  `{"ok": true, "data": {"token": ...}}`，把错误形状固化，导致该漂移长期不被检出。

## 3. 处理结果

- **门禁消费路径对齐（P4）**：`scripts/ops/production_acceptance_harness.py` 新增
  `session_token_from_login()`，只从声明路径 `data.session.token` 读取 bearer token；原 `data.token`
  读取被移除，不再以宽松回退掩盖生产方/消费方漂移。
- **单测改为真实形状并补负例**：`scripts/ops/test_production_acceptance_harness.py` 的 fake server
  改为返回 `{"ok": true, "data": {"session": {"token": ...}}}`（与 `login.py` 生产方一致）；
  新增 `test_flat_login_token_without_declared_session_path_is_rejected`，证明"只有扁平 `data.token`"
  的响应会被判失败且不产生任何已认证调用。单测数 4 → 5。
- **验收包摘要锁成对刷新**：`scripts/ops/production_acceptance_harness.py` 属不可变验收包成员，
  故同步更新 `scripts/ops/production_acceptance_package_v1.sha256` 与
  `scripts/ops/production_promotion_config_contract_v1.json:acceptance_package_digest`，
  两处均指向新摘要 `75ad08f9…`。这是该锁设计的成对确认，不是放宽。
- **未改动项**：`addons/smart_core/handlers/login.py`（生产方）与前端 `stores/session.ts`（消费方）未改，
  二者本已一致；未改 ACL、字段权限、断言、负例、环境或口令。

## 4. 验证与证据

- L1/L2 定向（离线）：`make verify.production.acceptance.harness ENV=dev` →
  `Ran 144 tests ... OK`、`[acceptance.package.verify] PASS digest=75ad08f9…`（5 个受管单测模块）。
- L4 运行态（真实 HTTP，日常开发服务器）：`make release.daily_dev.production_acceptance.harness
  ENV=dev DB_NAME=sc_demo ACCEPTANCE_BASE_URL=http://1.95.85.92:18081 ACCEPTANCE_LOGIN=wutao`
  （`ACCEPTANCE_RUN_COUNT=2`）→ `[production_acceptance_harness] PASS package_digest=75ad08f9… runs=2`。
  产物：`artifacts/backend/production_acceptance_harness.json`（`status=PASS`）。

  证据要点（两轮一致）：
  - `login_pass=true`、`system_init_pass=true`、`navigation_pass=true`（111 节点，必需片段 0 缺失、
    禁止片段 0 命中）、`my_work_acceptance_pass=true`。
  - `observed_role_code=business_config_admin`（契约 `expected_role_codes` 一致）。
  - `permission_boundary_pass=true`（匿名 `system.init` 与非法 token 均被 `AUTH_REQUIRED` 拒绝）。
  - `core_read_acceptance_pass=true`（`project.project`/`construction.contract`/`payment.request`）。
  - `repeated_clean_session_pass=true`（两轮令牌互异）；`frontend.root_http_status=200`、
    资源 `/assets/index-CQk-FHJ5.js` 200。

## 5. 收口标准映射

`docs/product/formal_business_operation_closure_plan_v1.md` 的收口标准"本地与日常开发服务器均通过完整发布门禁"
中的**日常开发服务器发布门禁**一项，由本节 L4 证据在本批次内首次被证明为 PASS；
此前该项从未被执行（不存在历史 harness 产物）。

## 6. 状态（四层分列）

- **批次验收**：通过。候选 `a298e9d4` 上 `make verify.production.acceptance.harness`（144 tests OK）与
  `make release.daily_dev.production_acceptance.harness`（日常开发服务器真实 HTTP，`PASS runs=2`）均通过。
- **主线集成**：完成 —— PR #599 已合并（merge commit `74465a03`），合并前精确 HEAD `a298e9d4` 上必需检查
  （`public_guard`、`merge_policy_gate`、`professional_quality_gate`、`frontend_release_gate`、
  `professional_authorization`、`python310_runtime_compatibility`、`release_candidate_gate`）全部 PASS。
- **版本发布**：未主张（未部署版本、未做 release snapshot）。
- **产品交付**：未主张；本批只闭合"日常开发服务器发布门禁"一项。

## 7. 台账说明

- run 回执 `.runtime/agent-runs/ACCEPTANCE-HARNESS-LOGIN-CONTRACT-ALIGNMENT/acceptance_harness_unit.json`
  绑定冻结 HEAD `a298e9d4`。该 run 的 `environment.kind=runtime`，故解析器把这份**离线**回执保守地标为
  `stale`（原因 `runtime evidence requires authoritative environment readback`）——这是既有的保守语义，
  与 `DAILY-DEV-USER-ACCEPTANCE-COMPLETION` 先例一致，不代表证据失效。
- 本批 run/goal 已 `completed`，`.agent/active-runs.json` 回到空终止态（见 `ACCEPTANCE-HARNESS-LOGIN-CONTRACT-ALIGNMENT-RETIREMENT`）。

（执行后回填）
